"""Headless PCM16 WAV replay source for deterministic adapter tests.

This reads actual WAV PCM and never relabels/resamples it. Feed emitted frames into
an injected ASR/VAD/session adapter from tests or a dedicated replay runner.
"""
from __future__ import annotations

import argparse
import time
import wave
from collections.abc import Iterator
from pathlib import Path

from backend.voice_v1.contracts import AudioFrame


def iter_wav_frames(
    path: str | Path,
    *,
    frame_ms: int = 20,
    capture_start_monotonic_ns: int | None = None,
) -> Iterator[AudioFrame]:
    if frame_ms <= 0 or frame_ms > 200:
        raise ValueError("frame_ms must be in [1, 200]")
    start_ns = time.monotonic_ns() if capture_start_monotonic_ns is None else capture_start_monotonic_ns
    with wave.open(str(path), "rb") as wav:
        if wav.getcomptype() != "NONE" or wav.getsampwidth() != 2:
            raise ValueError("replay currently accepts uncompressed PCM16 WAV only")
        rate, channels = wav.getframerate(), wav.getnchannels()
        samples_per_frame = max(1, round(rate * frame_ms / 1000))
        sequence = 0
        while data := wav.readframes(samples_per_frame):
            yield AudioFrame(
                data=data,
                sample_rate_hz=rate,
                channels=channels,
                sample_format="s16le",
                codec="pcm_s16le",
                capture_monotonic_ns=start_ns + round(sequence * samples_per_frame * 1e9 / rate),
                sequence=sequence,
            )
            sequence += 1


def inspect_wav(path: str | Path, *, frame_ms: int = 20) -> dict[str, int | str]:
    frames = list(iter_wav_frames(path, frame_ms=frame_ms, capture_start_monotonic_ns=0))
    if not frames:
        raise ValueError("WAV contains no audio frames")
    total_samples = sum(len(frame.data) // (2 * frame.channels) for frame in frames)
    return {
        "sample_rate_hz": frames[0].sample_rate_hz,
        "channels": frames[0].channels,
        "frame_count": len(frames),
        "duration_ms": round(total_samples * 1000 / frames[0].sample_rate_hz),
        "sample_format": frames[0].sample_format,
        "first_sequence": frames[0].sequence,
        "last_sequence": frames[-1].sequence,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect/replay PCM16 WAV fixture metadata")
    parser.add_argument("wav", type=Path)
    parser.add_argument("--frame-ms", type=int, default=20)
    args = parser.parse_args()
    import json
    print(json.dumps(inspect_wav(args.wav, frame_ms=args.frame_ms), indent=2))


if __name__ == "__main__":
    main()
