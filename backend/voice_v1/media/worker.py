"""Worker bootstrap boundary: transport/provider adapters must be supplied explicitly."""
from __future__ import annotations

from dataclasses import dataclass


class ProviderAdaptersMissing(RuntimeError):
    """Raised rather than falsely claiming a media worker is ready."""


@dataclass(frozen=True, slots=True)
class WorkerAdapters:
    livekit_session: object | None = None
    decoder: object | None = None
    resampler: object | None = None
    vad: object | None = None
    asr: object | None = None
    tts: object | None = None

    def readiness(self) -> dict[str, bool]:
        return {name: getattr(self, name) is not None for name in (
            "livekit_session", "decoder", "resampler", "vad", "asr", "tts"
        )}


def require_worker_adapters(adapters: WorkerAdapters) -> None:
    missing = [name for name, configured in adapters.readiness().items() if not configured]
    if missing:
        raise ProviderAdaptersMissing(
            "voice worker not ready; missing adapters: " + ", ".join(missing)
        )


def main() -> None:
    """Placeholder executable intentionally exits until real integrations are injected."""
    require_worker_adapters(WorkerAdapters())


if __name__ == "__main__":
    main()
