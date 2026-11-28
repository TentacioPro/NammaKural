from __future__ import annotations

import os
import time
import asyncio
from contextlib import contextmanager, asynccontextmanager
from typing import AsyncIterator, Iterator, Mapping

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Histogram, make_asgi_app

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "nammakural-voice")

# Labels are deliberately low-cardinality. Never add session IDs, turn IDs, raw paths,
# transcripts, locations, or other user-derived values as Prometheus labels.
REQUESTS = Counter("nk_voice_requests_total", "Voice API requests", ["route", "status"])
STAGE_SECONDS = Histogram(
    "nk_voice_stage_duration_seconds",
    "Voice pipeline stage duration",
    ["stage", "provider", "outcome"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1, 1.5, 2.5, 5, 10),
)
FIRST_AUDIO_SECONDS = Histogram(
    "nk_voice_end_of_speech_to_first_audio_seconds",
    "Client-clock end-of-speech to first playable audio; only real audio acknowledgements count",
    buckets=(0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1, 1.5, 2.5, 5),
)
ERRORS = Counter("nk_voice_pipeline_errors_total", "Voice pipeline errors", ["stage", "error_type"])


def configure_tracing() -> None:
    provider = trace.get_tracer_provider()
    if provider.__class__.__name__ != "ProxyTracerProvider":
        return
    resource = Resource.create({"service.name": SERVICE_NAME, "service.version": os.getenv("NK_AGENT_VERSION", "voice-v1-dev")})
    sdk_provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        sdk_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(sdk_provider)


def flush_traces(timeout_millis: int = 5000) -> bool:
    provider = trace.get_tracer_provider()
    flush = getattr(provider, "force_flush", None)
    return bool(flush(timeout_millis=timeout_millis)) if flush else True


configure_tracing()
TRACER = trace.get_tracer("nammakural.voice.pipeline", "1.0.0")


@contextmanager
def stage_timer(stage: str, provider: str = "local") -> Iterator[None]:
    started = time.perf_counter()
    outcome = "ok"
    try:
        with TRACER.start_as_current_span(f"voice.{stage}") as span:
            span.set_attribute("voice.stage", stage)
            span.set_attribute("voice.provider", provider)
            yield
    except Exception as exc:
        outcome = "error"
        ERRORS.labels(stage, type(exc).__name__).inc()
        raise
    finally:
        STAGE_SECONDS.labels(stage, provider, outcome).observe(time.perf_counter() - started)


@asynccontextmanager
async def async_stage_timer(
    stage: str,
    provider: str = "local",
    *,
    attributes: Mapping[str, str | int | float | bool] | None = None,
) -> AsyncIterator[None]:
    started = time.perf_counter()
    outcome = "ok"
    try:
        with TRACER.start_as_current_span(f"voice.{stage}") as span:
            span.set_attribute("voice.stage", stage)
            span.set_attribute("voice.provider", provider)
            for key, value in (attributes or {}).items():
                span.set_attribute(key, value)
            yield
    except asyncio.CancelledError:
        outcome = "cancelled"
        raise
    except Exception as exc:
        outcome = "error"
        ERRORS.labels(stage, type(exc).__name__).inc()
        raise
    finally:
        STAGE_SECONDS.labels(stage, provider, outcome).observe(time.perf_counter() - started)


metrics_app = make_asgi_app()
