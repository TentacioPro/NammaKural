"""VAD adapter boundary and deterministic adaptive endpoint tracker."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.voice_v1.media.frames import validate_frame
from backend.voice_v1.turn_policy import SlotKind, endpoint_window_ms
from backend.voice_v1.contracts import AudioFrame


class VADAdapter(Protocol):
    """A real Silero adapter can implement this; model/runtime is deliberately absent."""
    def is_speech(self, frame: AudioFrame) -> bool: ...


class SileroVADAdapter(Protocol):
    """Named contract only: caller must provide a real Silero-backed implementation."""
    def is_speech(self, frame: AudioFrame) -> bool: ...


class SemanticTurnDetector(Protocol):
    """Learned or evaluated detector; no model is bundled in this scaffold."""
    def is_turn_complete(self, transcript: str, *, active_slot: str) -> bool: ...


def finalize_turn_candidate(
    *, acoustic_endpoint: bool, transcript: str, active_slot: str,
    detector: SemanticTurnDetector,
) -> bool:
    """An acoustic silence candidate alone is insufficient for semantic completion."""
    if not acoustic_endpoint or not transcript.strip():
        return False
    return detector.is_turn_complete(transcript, active_slot=active_slot)


@dataclass(slots=True)
class AdaptiveEndpoint:
    slot_kind: SlotKind
    confidence: float | None = None
    silence_ms: int = 0
    speech_seen: bool = False

    def update(self, frame: AudioFrame, *, is_speech: bool) -> bool:
        """Return endpointed once configured minimum silence is reached after speech.

        Caller controls frame cadence and must pass truthful VAD results; this helper
        does not inspect samples or infer speech. A silence run beyond max also ends.
        """
        validate_frame(frame)
        if frame.sample_format not in {"s16le", "s16be"}:
            raise ValueError("adaptive timing requires decoded signed 16-bit PCM frames")
        bytes_per_sample = 2 * frame.channels
        if len(frame.data) % bytes_per_sample:
            raise ValueError("PCM payload is not aligned to whole sample frames")
        if is_speech:
            self.speech_seen = True
            self.silence_ms = 0
            return False
        if not self.speech_seen:
            return False
        # PCM cadence estimate only where a 16-bit mono/stereo PCM payload is known.
        duration_ms = max(1, round((len(frame.data) // bytes_per_sample) * 1000 / frame.sample_rate_hz))
        self.silence_ms += duration_ms
        minimum, maximum = endpoint_window_ms(self.slot_kind, confidence=self.confidence)
        return self.silence_ms >= minimum or self.silence_ms >= maximum

    def reset(self) -> None:
        self.silence_ms = 0
        self.speech_seen = False
