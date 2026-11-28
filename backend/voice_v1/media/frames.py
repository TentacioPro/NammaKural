"""Frame checks and resampler boundary; actual decoding/resampling is adapter-owned."""
from __future__ import annotations

from typing import Protocol

from backend.voice_v1.contracts import AudioFrame


class AudioFrameError(ValueError):
    """Malformed frame metadata or payload."""


def validate_frame(frame: AudioFrame, *, max_payload_bytes: int = 1_048_576) -> AudioFrame:
    """Validate basic PCM/container metadata without decoding or mutating the frame."""
    if not isinstance(frame.data, bytes):
        raise AudioFrameError("frame data must be bytes")
    if not 0 < len(frame.data) <= max_payload_bytes:
        raise AudioFrameError("frame payload size is outside allowed bounds")
    if not 1 <= frame.sample_rate_hz <= 192_000:
        raise AudioFrameError("sample_rate_hz must be in [1, 192000]")
    if not 1 <= frame.channels <= 8:
        raise AudioFrameError("channels must be in [1, 8]")
    if frame.sample_format not in {"s16le", "s16be", "f32le", "f32be", "opus"}:
        raise AudioFrameError("unsupported or unspecified sample_format")
    if frame.capture_monotonic_ns < 0 or frame.sequence < 0:
        raise AudioFrameError("capture timestamp and sequence must be non-negative")
    if not frame.codec or len(frame.codec) > 64:
        raise AudioFrameError("codec must be a short non-empty identifier")
    return frame


class Resampler(Protocol):
    """Adapter contract for real decoding/resampling; no implementation is bundled.

    Implementations must perform actual sample conversion, preserve capture timestamp
    and sequence, and set the output rate to the rate actually produced. They must
    never relabel samples (e.g. 8 kHz bytes as 16 kHz) without resampling.
    """
    def resample(self, frame: AudioFrame, *, target_sample_rate_hz: int) -> AudioFrame: ...


def resample_frame(frame: AudioFrame, *, target_sample_rate_hz: int, adapter: Resampler) -> AudioFrame:
    validate_frame(frame)
    if target_sample_rate_hz <= 0:
        raise ValueError("target_sample_rate_hz must be positive")
    result = adapter.resample(frame, target_sample_rate_hz=target_sample_rate_hz)
    validate_frame(result)
    if result.sample_rate_hz != target_sample_rate_hz:
        raise AudioFrameError("resampler output rate does not match requested rate")
    if (result.capture_monotonic_ns, result.sequence) != (frame.capture_monotonic_ns, frame.sequence):
        raise AudioFrameError("resampler must preserve capture timestamp and sequence")
    return result
