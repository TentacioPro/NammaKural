from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Protocol


@dataclass(slots=True)
class AudioFrame:
    """A decoded frame plus enough provenance to interpret its samples correctly."""
    data: bytes
    sample_rate_hz: int
    channels: int
    sample_format: str
    codec: str
    capture_monotonic_ns: int
    sequence: int


@dataclass(slots=True)
class Transcript:
    text: str
    is_final: bool
    confidence: float | None = None
    language: str = "ta-IN"
    first_audio_monotonic_ns: int | None = None
    speech_end_monotonic_ns: int | None = None
    emitted_monotonic_ns: int | None = None


@dataclass(slots=True)
class Reply:
    display_text: str
    tts_text: str
    state: str = "clarifying"
    provider: str = "deterministic"
    voice: str = "ta-IN"
    speaking_rate: float = 1.0


@dataclass(slots=True)
class AudioChunk:
    data: bytes
    mime_type: str
    sample_rate_hz: int
    channels: int
    sequence: int
    generated_monotonic_ns: int


class StreamingASR(Protocol):
    """Consume timestamped media frames and yield partial/final transcripts."""
    async def transcribe(
        self, frames: AsyncIterator[AudioFrame], *, language: str, keyterms: tuple[str, ...] = ()
    ) -> AsyncIterator[Transcript]: ...


class Workflow(Protocol):
    async def respond(self, transcript: str, *, session_id: str, turn_id: str) -> Reply: ...


class StreamingTTS(Protocol):
    """Yield playable chunks as soon as the provider produces them."""
    async def synthesize(
        self, text: str, *, language: str, voice: str, speaking_rate: float
    ) -> AsyncIterator[AudioChunk]: ...
