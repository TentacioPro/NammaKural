"""Isolated media scaffolding; no codec, DSP, transport, or model is bundled."""

from .frames import AudioFrameError, Resampler, validate_frame

__all__ = ["AudioFrameError", "Resampler", "validate_frame"]
