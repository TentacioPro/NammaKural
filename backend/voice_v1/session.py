"""Provider-neutral async session loop for the voice_v1 backend.

This composes adapters; it does not implement transport, codecs, ASR, an LLM,
TTS, or agency tools. A committed interruption cancels the active pipeline task
and advances the coordinator epoch so late provider results are discarded.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Literal

from backend.voice_v1.contracts import AudioChunk, AudioFrame, Reply, StreamingASR, StreamingTTS, Transcript, Workflow
from backend.voice_v1.observability import async_stage_timer
from backend.voice_v1.speech.pipeline import build_speech_output
from backend.voice_v1.turn_policy import SessionState, TurnCoordinator


EventKind = Literal["transcript_partial", "transcript_final", "reply", "audio", "interrupted", "error"]


@dataclass(frozen=True, slots=True)
class SessionEvent:
    kind: EventKind
    session_id: str
    turn_id: str
    epoch: int
    transcript: Transcript | None = None
    reply: Reply | None = None
    audio: AudioChunk | None = None
    error_code: str | None = None


@dataclass(slots=True)
class _ActiveTurn:
    turn_id: str
    epoch: int
    task: asyncio.Task[None]
    events: asyncio.Queue[SessionEvent | None]


class VoiceSessionOrchestrator:
    """Connect configured streaming adapters with cancellation-safe turn policy.

    One active turn per session is supported. Session instances are process-local;
    callers must provide transport, durable state and authentication separately.
    """

    def __init__(self, *, asr: StreamingASR, workflow: Workflow, tts: StreamingTTS):
        self.asr = asr
        self.workflow = workflow
        self.tts = tts
        self._coordinators: dict[str, TurnCoordinator] = {}
        self._active: dict[str, _ActiveTurn] = {}

    def coordinator(self, session_id: str) -> TurnCoordinator:
        if not session_id:
            raise ValueError("session_id is required")
        return self._coordinators.setdefault(session_id, TurnCoordinator())

    async def stream_turn(
        self,
        *,
        session_id: str,
        turn_id: str,
        frames: AsyncIterator[AudioFrame],
        language: str = "ta-IN",
        keyterms: tuple[str, ...] = (),
    ) -> AsyncIterator[SessionEvent]:
        """Yield partial/final transcript, reply, and playable audio events in order."""
        if not turn_id:
            raise ValueError("turn_id is required")
        if session_id in self._active:
            raise RuntimeError("session already has an active turn")
        coordinator = self.coordinator(session_id)
        coordinator.begin_endpointing()
        epoch = coordinator.epoch
        events: asyncio.Queue[SessionEvent | None] = asyncio.Queue()
        task = asyncio.create_task(
            self._produce(session_id, turn_id, epoch, language, keyterms, frames, events),
            name=f"voice-turn:{session_id}:{turn_id}:{epoch}",
        )
        active = _ActiveTurn(turn_id, epoch, task, events)
        self._active[session_id] = active
        try:
            while True:
                event = await events.get()
                if event is None:
                    break
                yield event
        finally:
            # Disconnecting the consumer must not leave model/provider work running.
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            if self._active.get(session_id) is active:
                self._active.pop(session_id, None)

    async def possible_barge_in(self, session_id: str) -> int:
        """Temporarily pause output while a transport/classifier judges speech."""
        return self.coordinator(session_id).pause_for_possible_barge_in()

    async def resolve_incoming_speech(
        self,
        session_id: str,
        *,
        is_backchannel: bool,
        explicit_stop: bool = False,
    ) -> int:
        """Resume for backchannels; cancel in-flight work only on committed interruption."""
        coordinator = self.coordinator(session_id)
        previous_epoch = coordinator.epoch
        epoch = coordinator.resolve_incoming_speech(
            is_backchannel=is_backchannel,
            explicit_stop=explicit_stop,
        )
        active = self._active.get(session_id)
        if epoch != previous_epoch and active is not None:
            await active.events.put(SessionEvent(
                kind="interrupted",
                session_id=session_id,
                turn_id=active.turn_id,
                epoch=epoch,
            ))
            active.task.cancel()
        return epoch

    async def _produce(
        self,
        session_id: str,
        turn_id: str,
        epoch: int,
        language: str,
        keyterms: tuple[str, ...],
        frames: AsyncIterator[AudioFrame],
        events: asyncio.Queue[SessionEvent | None],
    ) -> None:
        coordinator = self.coordinator(session_id)
        trace_attributes = {
            "nk.session_id": session_id,
            "nk.turn_id": turn_id,
            "nk.turn_epoch": epoch,
        }
        try:
            async for transcript in self._transcripts(
                frames, language=language, keyterms=keyterms, attributes=trace_attributes
            ):
                if not coordinator.is_current_epoch(epoch):
                    return
                if not transcript.is_final:
                    await events.put(SessionEvent(
                        "transcript_partial", session_id, turn_id, epoch, transcript=transcript
                    ))
                    continue
                await events.put(SessionEvent(
                    "transcript_final", session_id, turn_id, epoch, transcript=transcript
                ))
                coordinator.start_generation()
                async with async_stage_timer(
                    "workflow",
                    type(self.workflow).__name__,
                    attributes=trace_attributes,
                ):
                    reply = await self.workflow.respond(
                        transcript.text,
                        session_id=session_id,
                        turn_id=turn_id,
                    )
                if not coordinator.is_current_epoch(epoch):
                    return
                speech = build_speech_output(
                    reply.display_text,
                    final_text=reply.tts_text,
                    locale=language,
                    provider=reply.provider,
                    critical_readback=reply.speaking_rate < 1.0,
                )
                rendered_reply = Reply(
                    display_text=speech.display_text,
                    tts_text=speech.tts_text,
                    state=reply.state,
                    provider=reply.provider,
                    voice=reply.voice,
                    speaking_rate=speech.speaking_rate,
                )
                await events.put(SessionEvent(
                    "reply", session_id, turn_id, epoch, reply=rendered_reply
                ))
                coordinator.start_speaking()
                async for chunk in self._audio_chunks(
                    rendered_reply,
                    language=speech.voice_locale,
                    attributes=trace_attributes,
                ):
                    if not coordinator.is_current_epoch(epoch):
                        return
                    await events.put(SessionEvent(
                        "audio", session_id, turn_id, epoch, audio=chunk
                    ))
                return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # Avoid leaking provider exception text, which may contain user data.
            if coordinator.is_current_epoch(epoch):
                await events.put(SessionEvent(
                    "error", session_id, turn_id, epoch, error_code=type(exc).__name__
                ))
        finally:
            if coordinator.is_current_epoch(epoch) and coordinator.state not in (
                SessionState.TOOL_PENDING,
                SessionState.HUMAN_HANDOFF,
                SessionState.CLOSED,
            ):
                coordinator.finish_turn()
            await events.put(None)

    async def _transcripts(
        self,
        frames: AsyncIterator[AudioFrame],
        *,
        language: str,
        keyterms: tuple[str, ...],
        attributes: dict[str, str | int | float | bool],
    ) -> AsyncIterator[Transcript]:
        async with async_stage_timer(
            "asr", type(self.asr).__name__, attributes=attributes
        ):
            async for transcript in self.asr.transcribe(
                frames, language=language, keyterms=keyterms
            ):
                yield transcript

    async def _audio_chunks(
        self,
        reply: Reply,
        *,
        language: str,
        attributes: dict[str, str | int | float | bool],
    ) -> AsyncIterator[AudioChunk]:
        async with async_stage_timer(
            "tts", type(self.tts).__name__, attributes=attributes
        ):
            async for chunk in self.tts.synthesize(
                reply.tts_text,
                language=language,
                voice=reply.voice,
                speaking_rate=reply.speaking_rate,
            ):
                yield chunk
