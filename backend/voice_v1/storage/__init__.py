"""Pure domain primitives for voice-case persistence; no database client is wired."""

from .domain import (
    Case,
    CaseLifecycle,
    CaseStatus,
    DuplicateCandidate,
    IdempotencyConflict,
    MemoryEntry,
    MemoryScope,
    OutboxEvent,
    OutboxStore,
    TransitionError,
    advisory_duplicate_candidates,
    resolve_location,
)

__all__ = [
    "Case", "CaseLifecycle", "CaseStatus", "DuplicateCandidate",
    "IdempotencyConflict", "MemoryEntry", "MemoryScope", "OutboxEvent",
    "OutboxStore", "TransitionError", "advisory_duplicate_candidates",
    "resolve_location",
]
