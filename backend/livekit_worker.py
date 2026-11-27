"""LiveKit Agents full-duplex WebRTC voice worker powered by Silero VAD, Sarvam Saaras v4/Bulbul v3 & LangGraph.

Run locally or on a dedicated worker host:
  python -m backend.livekit_worker dev
Requires LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET (and SARVAM_API_KEY) in .env.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import urllib.request
import uuid
import wave
from typing import Any

from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    APIConnectOptions,
    JobContext,
    WorkerOptions,
    cli,
    llm,
    stt,
    tts,
)
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, NOT_GIVEN, NotGivenOr
from livekit.plugins import silero

from backend.agent_workflow import run_workflow_turn
from backend.logger import log_event
from backend.session_store import _load_local_env
from backend.tts_service import synthesize_neural_mp3

_load_local_env()


def _audio_buffer_to_wav(buffer: stt.AudioBuffer) -> bytes:
    frames = buffer if isinstance(buffer, list) else [buffer]
    if not frames:
        return b""
    sample_rate = frames[0].sample_rate
    num_channels = frames[0].num_channels
    pcm = b"".join(bytes(f.data) for f in frames)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


class SarvamSaarasSTT(stt.STT):
    """LiveKit STT adapter calling Sarvam Saaras v4 (codemix) on VAD-segmented utterances."""

    def __init__(self) -> None:
        super().__init__(capabilities=stt.STTCapabilities(streaming=False, interim_results=False))

    async def _recognize_impl(
        self,
        buffer: stt.AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> stt.SpeechEvent:
        wav_bytes = _audio_buffer_to_wav(buffer)
        sarvam_key = os.getenv("SARVAM_API_KEY", "").strip()
        transcript = ""
        if wav_bytes and sarvam_key:
            transcript = await asyncio.to_thread(self._transcribe_sync, wav_bytes, sarvam_key)
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(language=language if isinstance(language, str) else "ta-IN", text=transcript)],
        )

    @staticmethod
    def _transcribe_sync(wav_bytes: bytes, sarvam_key: str) -> str:
        boundary = uuid.uuid4().hex
        fields = {"model": "saaras:v4", "mode": "codemix"}
        body = "".join(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'
            for k, v in fields.items()
        ).encode("utf-8")
        body += (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; filename="speech.wav"\r\n'
            "Content-Type: audio/wav\r\n\r\n"
        ).encode("utf-8") + wav_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
        req = urllib.request.Request(
            "https://api.sarvam.ai/speech-to-text",
            data=body,
            headers={
                "api-subscription-key": sarvam_key,
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))
                txt = str(parsed.get("transcript", "")).strip()
                log_event("livekit.stt_saaras", txt[:80])
                return txt
        except Exception as exc:
            log_event("livekit.stt_error", type(exc).__name__, level="WARN")
            return ""


class _NammaKuralLLMStream(llm.LLMStream):
    def __init__(
        self,
        llm_inst: llm.LLM,
        *,
        chat_ctx: llm.ChatContext,
        tools: list[llm.Tool] | None,
        conn_options: APIConnectOptions,
        session_id: str,
    ) -> None:
        super().__init__(llm_inst, chat_ctx=chat_ctx, tools=tools or [], conn_options=conn_options)
        self._session_id = session_id

    async def _run(self) -> None:
        history: list[dict[str, str]] = []
        latest_user = ""
        for item in self._chat_ctx.items:
            if getattr(item, "type", "") != "message":
                continue
            role = "agent" if item.role == "assistant" else "user"
            txt = item.text_content or ""
            if txt:
                history.append({"role": role, "text": txt})
                if role == "user":
                    latest_user = txt

        if not latest_user:
            return

        res = await asyncio.to_thread(
            run_workflow_turn,
            utterance=latest_user,
            combined_text=latest_user,
            state_code="tn",
            lang="tanglish",
            llm_mode="auto",
            history=history[:-1],
            session_id=self._session_id,
            dpdp_consented=True,
        )
        spoken = res.get("tts_text") or res.get("display_text") or res.get("reply") or ""
        if spoken:
            self._event_ch.send_nowait(
                llm.ChatChunk(
                    id=uuid.uuid4().hex[:12],
                    delta=llm.ChoiceDelta(role="assistant", content=spoken),
                )
            )


class NammaKuralLangGraphLLM(llm.LLM):
    """LiveKit LLM adapter backed by NammaKural's LangGraph StateGraph & Code > LLM guardrails."""

    def __init__(self, session_id: str) -> None:
        super().__init__()
        self._session_id = session_id

    def chat(
        self,
        *,
        chat_ctx: llm.ChatContext,
        tools: list[llm.Tool] | None = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        parallel_tool_calls: Any = NOT_GIVEN,
        tool_choice: Any = NOT_GIVEN,
        extra_kwargs: Any = NOT_GIVEN,
    ) -> llm.LLMStream:
        return _NammaKuralLLMStream(
            self,
            chat_ctx=chat_ctx,
            tools=tools,
            conn_options=conn_options,
            session_id=self._session_id,
        )


class _BulbulChunkedStream(tts.ChunkedStream):
    def __init__(self, tts_inst: tts.TTS, input_text: str, conn_options: APIConnectOptions) -> None:
        super().__init__(tts=tts_inst, input_text=input_text, conn_options=conn_options)

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        res = await synthesize_neural_mp3(self._input_text, preferred_voice="auto", lang="tanglish")
        audio_bytes: bytes = res.get("audio") or b""
        if not audio_bytes:
            return
        media = res.get("media_type", "audio/mpeg")
        if media == "audio/wav":
            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                output_emitter.initialize(
                    request_id=uuid.uuid4().hex[:12],
                    sample_rate=wf.getframerate(),
                    num_channels=wf.getnchannels(),
                    mime_type="audio/pcm",
                )
                output_emitter.push(wf.readframes(wf.getnframes()))
        else:
            output_emitter.initialize(
                request_id=uuid.uuid4().hex[:12],
                sample_rate=24000,
                num_channels=1,
                mime_type="audio/mpeg",
            )
            output_emitter.push(audio_bytes)
        output_emitter.flush()


class NammaKuralBulbulTTS(tts.TTS):
    """LiveKit TTS adapter using Sarvam Bulbul v3 (with edge-tts fallback)."""

    def __init__(self) -> None:
        super().__init__(capabilities=tts.TTSCapabilities(streaming=False), sample_rate=16000, num_channels=1)

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> tts.ChunkedStream:
        return _BulbulChunkedStream(self, text, conn_options)


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()
    session_id = ctx.room.name or f"lk-{uuid.uuid4().hex[:8]}"
    agent = Agent(
        instructions=(
            "You are NammaKural (நம்ம குரல்), a warm Tamil/Tanglish civic voice assistant. "
            "Speak naturally in 1-2 short Tamil/Tanglish sentences."
        )
    )
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=SarvamSaarasSTT(),
        llm=NammaKuralLangGraphLLM(session_id=session_id),
        tts=NammaKuralBulbulTTS(),
        allow_interruptions=True,
        min_endpointing_delay=0.35,
        max_endpointing_delay=1.6,
    )
    await session.start(room=ctx.room, agent=agent)
    await session.say("வணக்கம்! நான் நம்ம குரல். உங்கள் தெருப் பிரச்சனையைச் சொல்லுங்கள்.", allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
