"""Capture-side feature policy. These flags do not perform audio processing."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CaptureFeatures:
    echo_cancellation: bool = False
    noise_suppression: bool = False
    automatic_gain_control: bool = False
    comfort_noise: bool = False

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "CaptureFeatures":
        import os
        values = os.environ if env is None else env
        def enabled(name: str) -> bool:
            value = values.get(name, "0").strip().lower()
            if value not in {"0", "1", "false", "true", "off", "on"}:
                raise ValueError(f"{name} must be an explicit boolean")
            return value in {"1", "true", "on"}
        return cls(
            echo_cancellation=enabled("NK_AUDIO_ECHO_CANCELLATION"),
            noise_suppression=enabled("NK_AUDIO_NOISE_SUPPRESSION"),
            automatic_gain_control=enabled("NK_AUDIO_AGC"),
            comfort_noise=enabled("NK_AUDIO_COMFORT_NOISE"),
        )

    def enabled_processing_flags(self) -> tuple[str, ...]:
        """Report requested flags only; browser/device DSP must be independently verified."""
        return tuple(name for name, active in (
            ("echo_cancellation", self.echo_cancellation),
            ("noise_suppression", self.noise_suppression),
            ("automatic_gain_control", self.automatic_gain_control),
        ) if active)


def comfort_noise_allowed(features: CaptureFeatures) -> bool:
    """Comfort noise is policy-gated and defaults off; this does not generate noise."""
    return features.comfort_noise
