from __future__ import annotations

import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from backend.agent_workflow import run_workflow_turn
from backend.voice_v1.observability import FIRST_AUDIO_SECONDS, REQUESTS, TRACER, flush_traces, metrics_app, stage_timer

@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    flush_traces(timeout_millis=5000)


app = FastAPI(
    title="NammaKural Streaming Voice Scaffold",
    version="1.0.0-dev",
    description="Instrumented test harness and provider contracts. Text test endpoint is not end-to-end voice TTFA.",
    lifespan=lifespan,
)
app.mount("/metrics", metrics_app)


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        status = "500"
        try:
            with TRACER.start_as_current_span("http.request") as span:
                span.set_attribute("http.method", request.method)
                span.set_attribute("nk.request_id", request_id)
                response = await call_next(request)
                status = str(response.status_code)
                span.set_attribute("http.status_code", response.status_code)
                route = request.scope.get("route")
                span.set_attribute("http.route", getattr(route, "path", "unmatched"))
            response.headers["X-Request-ID"] = request_id
            response.headers["Server-Timing"] = f"app;dur={(time.perf_counter() - started) * 1000:.1f}"
            return response
        finally:
            # Route is resolved during routing; use its template, never arbitrary URL paths, as a metric label.
            route = request.scope.get("route")
            route_template = getattr(route, "path", "unmatched")
            # Route template avoids leaking user-derived path values into metrics.
            REQUESTS.labels(route_template, status).inc()


app.add_middleware(TraceMiddleware)


class TestTurn(BaseModel):
    utterance: str = Field(min_length=1, max_length=1200)
    session_id: str = Field(default_factory=lambda: f"test-{uuid.uuid4().hex[:12]}", min_length=1, max_length=128)
    state_code: str = "tn"
    lang: str = "tanglish"
    llm_mode: str = "offline"
    dpdp_consented: bool = True


class PlaybackAck(BaseModel):
    turn_id: str = Field(min_length=1, max_length=64)
    event: Literal["playback_started"]
    clock_origin: Literal["browser-performance.now", "native-monotonic"]
    end_of_speech_ms: float = Field(ge=0, le=1e12)
    playback_started_ms: float = Field(ge=0, le=1e12)


class PlaybackAckResponse(BaseModel):
    accepted: bool
    turn_id: str
    client_end_of_speech_to_playback_ms: float
    clock_origin: str
    note: str


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"status": "ok", "service": "nammakural-voice", "version": os.getenv("NK_AGENT_VERSION", "voice-v1-dev")}


@app.get("/readyz")
def readyz() -> dict[str, Any]:
    return {
        "ready": True,
        "mode": os.getenv("NK_VOICE_MODE", "test"),
        "transport": os.getenv("NK_TRANSPORT", "not-configured"),
        "asr": os.getenv("NK_ASR_PROVIDER", "not-configured"),
        "llm": os.getenv("NK_LLM_PROVIDER", "deterministic-workflow"),
        "tts": os.getenv("NK_TTS_PROVIDER", "not-configured"),
        "note": "Readiness of the API does not mean realtime audio providers are configured.",
    }


@app.get("/v1/providers")
def providers() -> dict[str, Any]:
    return {
        "transport": {"selected": os.getenv("NK_TRANSPORT", "not-configured"), "target": "LiveKit WebRTC"},
        "asr": {"selected": os.getenv("NK_ASR_PROVIDER", "not-configured"), "required": "streaming partial/final transcript adapter"},
        "workflow": {"selected": "existing deterministic NammaKural FSM", "llm_mode_default": "offline"},
        "tts": {"selected": os.getenv("NK_TTS_PROVIDER", "not-configured"), "required": "incremental playable audio chunks"},
        "telemetry": {"metrics": "/metrics", "traces": "OTLP when OTEL_EXPORTER_OTLP_ENDPOINT is set"},
        "production_audio_ready": False,
    }


@app.post("/v1/test/turn")
def test_turn(payload: TestTurn, request: Request) -> JSONResponse:
    """Exercise the civic FSM with injected text; excludes mic/VAD/ASR/TTS."""
    turn_id = str(uuid.uuid4())
    started = time.perf_counter()
    with TRACER.start_as_current_span("voice.test_turn") as span:
        span.set_attribute("nk.request_id", request.state.request_id)
        span.set_attribute("nk.turn_id", turn_id)
        span.set_attribute("nk.session_id", payload.session_id)
        span.set_attribute("nk.input_mode", "injected_text")
        span.set_attribute("nk.language", payload.lang)
        with stage_timer("workflow", "existing-nammakural-fsm"):
            result = run_workflow_turn(
                utterance=payload.utterance,
                combined_text=payload.utterance,
                state_code=payload.state_code,
                lang=payload.lang,
                llm_mode=payload.llm_mode,
                session_id=payload.session_id,
                dpdp_consented=payload.dpdp_consented,
            )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        span.set_attribute("nk.workflow_ms", elapsed_ms)
    return JSONResponse({
        "request_id": request.state.request_id,
        "session_id": payload.session_id,
        "turn_id": turn_id,
        "input_mode": "injected_text",
        "voice_ttfa_ms": None,
        "voice_ttfa_note": "Not measured: this test injects text and excludes microphone, endpointing, ASR, TTS, audio transport, and playback.",
        "workflow_ms": elapsed_ms,
        "result": result,
    })


@app.post("/v1/telemetry/playback", response_model=PlaybackAckResponse)
def playback_ack(payload: PlaybackAck, request: Request) -> PlaybackAckResponse | JSONResponse:
    """Accept a client playback event measured entirely on one client monotonic clock."""
    delta_ms = payload.playback_started_ms - payload.end_of_speech_ms
    if delta_ms < 0:
        return JSONResponse(status_code=422, content={"detail": "playback time precedes end-of-speech on the supplied clock"})
    if delta_ms > 60_000:
        return JSONResponse(status_code=422, content={"detail": "playback delay exceeds the 60000 ms sanity limit"})
    FIRST_AUDIO_SECONDS.observe(delta_ms / 1000)
    with TRACER.start_as_current_span("voice.client_playback_ack") as span:
        span.set_attribute("nk.request_id", request.state.request_id)
        span.set_attribute("nk.turn_id", payload.turn_id)
        span.set_attribute("nk.clock_origin", payload.clock_origin)
        span.set_attribute("nk.end_of_speech_to_playback_ms", delta_ms)
    return PlaybackAckResponse(
        accepted=True,
        turn_id=payload.turn_id,
        client_end_of_speech_to_playback_ms=round(delta_ms, 2),
        clock_origin=payload.clock_origin,
        note="Client-reported measurement; verify the event semantics and client clock before treating as an SLO result.",
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "nammakural-voice-scaffold", "docs": "/docs", "health": "/healthz", "metrics": "/metrics"}
