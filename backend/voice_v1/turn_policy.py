from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SlotKind(StrEnum):
    YES_NO = "yes_no"
    SHORT_CHOICE = "short_choice"
    FREE_TEXT = "free_text"
    DIGITS = "digits"
    ADDRESS = "address"


# Starting silence hangovers, to tune with a language-specific replay set.
_ENDPOINT_MS: dict[SlotKind, tuple[int, int]] = {
    SlotKind.YES_NO: (150, 250),
    SlotKind.SHORT_CHOICE: (200, 350),
    SlotKind.FREE_TEXT: (350, 650),
    SlotKind.DIGITS: (800, 1200),
    SlotKind.ADDRESS: (800, 1200),
}


def endpoint_window_ms(slot_kind: SlotKind, *, confidence: float | None = None) -> tuple[int, int]:
    """Return the initial (minimum, maximum) slot-specific silence hangover."""
    low, high = _ENDPOINT_MS[slot_kind]
    if confidence is not None and confidence < 0.55:
        return low, min(1500, high + 200)
    return low, high


@dataclass(slots=True)
class SpeakerCadence:
    """EMA of caller pause lengths; a policy signal, not a VAD or semantic detector."""
    mean_pause_ms: float = 250.0
    alpha: float = 0.2

    def observe_pause(self, pause_ms: float) -> None:
        if pause_ms < 0:
            raise ValueError("pause_ms must be non-negative")
        self.mean_pause_ms = (1 - self.alpha) * self.mean_pause_ms + self.alpha * pause_ms

    def adjust_window(self, slot_kind: SlotKind, *, confidence: float | None = None) -> tuple[int, int]:
        low, high = endpoint_window_ms(slot_kind, confidence=confidence)
        slow_extra = max(0, min(300, round(self.mean_pause_ms - 300)))
        return low, min(1500, high + slow_extra)


class SessionState(StrEnum):
    LISTENING = "LISTENING"
    ENDPOINTING = "ENDPOINTING"
    GENERATING = "GENERATING"
    SPEAKING = "SPEAKING"
    PAUSED = "PAUSED"
    TOOL_PENDING = "TOOL_PENDING"
    HUMAN_HANDOFF = "HUMAN_HANDOFF"
    CLOSED = "CLOSED"


@dataclass(slots=True)
class TurnCoordinator:
    """Deterministic state core; adapters must cancel tasks and flush actual media queues."""
    state: SessionState = SessionState.LISTENING
    epoch: int = 0
    paused_from: SessionState | None = None
    last_event: str = "created"

    def begin_endpointing(self) -> None:
        self._require_not_closed()
        if self.state is not SessionState.LISTENING:
            raise RuntimeError(f"cannot endpoint while session is {self.state.value}")
        self.state = SessionState.ENDPOINTING
        self.last_event = "endpointing_started"

    def start_generation(self) -> int:
        self._require_not_closed()
        if self.state not in (SessionState.LISTENING, SessionState.ENDPOINTING):
            raise RuntimeError(f"cannot generate while session is {self.state.value}")
        self.state = SessionState.GENERATING
        self.last_event = "generation_started"
        return self.epoch

    def start_speaking(self) -> int:
        self._require_not_closed()
        if self.state is not SessionState.GENERATING:
            raise RuntimeError(f"cannot speak while session is {self.state.value}")
        self.state = SessionState.SPEAKING
        self.last_event = "speech_started"
        return self.epoch

    def start_tool(self) -> int:
        self._require_not_closed()
        if self.state in (SessionState.TOOL_PENDING, SessionState.HUMAN_HANDOFF):
            raise RuntimeError(f"cannot start tool while session is {self.state.value}")
        self.state = SessionState.TOOL_PENDING
        self.last_event = "tool_started"
        return self.epoch

    def complete_tool(self, epoch: int) -> bool:
        if not self.is_current_epoch(epoch) or self.state is not SessionState.TOOL_PENDING:
            return False
        self.state = SessionState.GENERATING
        self.last_event = "tool_completed"
        return True

    def begin_handoff(self) -> None:
        self._require_not_closed()
        self.epoch += 1
        self.state = SessionState.HUMAN_HANDOFF
        self.paused_from = None
        self.last_event = "human_handoff_started"

    def end_handoff(self) -> None:
        self._require_not_closed()
        if self.state is not SessionState.HUMAN_HANDOFF:
            raise RuntimeError("no human handoff is active")
        self.epoch += 1
        self.state = SessionState.LISTENING
        self.last_event = "human_handoff_ended"

    def pause_for_possible_barge_in(self) -> int:
        """Pause output while classifying speech; do not cancel until interruption is committed."""
        self._require_not_closed()
        if self.state in (SessionState.SPEAKING, SessionState.GENERATING):
            self.paused_from = self.state
            self.state = SessionState.PAUSED
            self.last_event = "possible_barge_in_paused"
        return self.epoch

    def resolve_incoming_speech(self, *, is_backchannel: bool, explicit_stop: bool = False) -> int:
        """Resume on an acknowledgement; bump epoch only for a committed interruption."""
        self._require_not_closed()
        if self.state in (SessionState.HUMAN_HANDOFF, SessionState.TOOL_PENDING):
            return self.epoch
        if self.state is SessionState.LISTENING and not explicit_stop:
            return self.epoch
        if self.state is SessionState.PAUSED and is_backchannel and not explicit_stop:
            self.state = self.paused_from or SessionState.LISTENING
            self.paused_from = None
            self.last_event = "backchannel_resumed"
            return self.epoch
        self.epoch += 1
        self.state = SessionState.LISTENING
        self.paused_from = None
        self.last_event = "explicit_stop" if explicit_stop else "barge_in_committed"
        return self.epoch

    def is_current_epoch(self, epoch: int) -> bool:
        """Check before accepting delayed model/tool completion after cancellation."""
        return self.state is not SessionState.CLOSED and epoch == self.epoch

    def finish_turn(self) -> None:
        """Return a completed turn to listening without changing its epoch."""
        self._require_not_closed()
        if self.state not in (SessionState.ENDPOINTING, SessionState.GENERATING, SessionState.SPEAKING):
            raise RuntimeError(f"cannot finish turn while session is {self.state.value}")
        self.state = SessionState.LISTENING
        self.paused_from = None
        self.last_event = "turn_finished"

    def close(self) -> None:
        self.epoch += 1
        self.state = SessionState.CLOSED
        self.paused_from = None
        self.last_event = "closed"

    def _require_not_closed(self) -> None:
        if self.state is SessionState.CLOSED:
            raise RuntimeError("session is closed")


def classify_backchannel(text: str, *, context: str, confidence: float | None = None) -> bool:
    """Conservative acknowledgement filter; confirmation contexts never discard agreement."""
    normalized = " ".join(text.casefold().strip().split()).strip(".,!?;:")
    if context in {"consent", "confirmation", "otp", "critical_readback"}:
        return False
    if confidence is not None and confidence < 0.65:
        return False
    return normalized in {
        "mm", "mmm", "hmm", "ஆமா", "ஆமாம்", "சரி", "seri", "sari", "aama", "ama", "okay", "ok"
    }


def is_explicit_stop(text: str) -> bool:
    normalized = " ".join(text.casefold().strip().split()).strip(".,!?;:")
    return normalized in {"stop", "cancel", "niruthunga", "niruththu", "நிறுத்து", "நிறுத்துங்கள்"}


def should_emit_listening_cue(*, continuous_speech_seconds: float, pause_ms: float, already_emitted: bool) -> bool:
    """Policy only; audio playback must remain low-volume, cancellable, and opt-in."""
    return not already_emitted and continuous_speech_seconds >= 5.5 and 120 <= pause_ms <= 500
