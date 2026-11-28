"""Persistence-agnostic storage domain rules for voice cases.

These value objects intentionally do not connect to PostgreSQL or any grievance
submission service. A production adapter must persist transitions and outbox rows
in one database transaction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from hashlib import sha256
from threading import RLock
from typing import Iterable
from uuid import UUID, uuid4


class CaseStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    QUEUED_FOR_SUBMISSION = "QUEUED_FOR_SUBMISSION"
    SUBMITTED = "SUBMITTED"


class TransitionError(ValueError):
    """Raised when a case transition violates the lifecycle contract."""


class IdempotencyConflict(ValueError):
    """An idempotency key was reused for a different logical operation."""


@dataclass(frozen=True, slots=True)
class Case:
    case_id: UUID
    status: CaseStatus = CaseStatus.DRAFT
    version: int = 0
    receipt_reference: str | None = None
    receipt_verified_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    event_id: UUID
    aggregate_id: UUID
    event_type: str
    idempotency_key: str
    created_at: datetime
    payload: tuple[tuple[str, str], ...] = ()
    delivered_at: datetime | None = None


class CaseLifecycle:
    """In-memory reference lifecycle; adapters must make changes transactionally."""

    def __init__(self) -> None:
        self._cases: dict[UUID, Case] = {}
        self._keys: dict[str, tuple[str, UUID]] = {}
        self._outbox: list[OutboxEvent] = []
        self._lock = RLock()

    def create(self, *, idempotency_key: str, fingerprint: str) -> Case:
        if not idempotency_key.strip() or not fingerprint:
            raise ValueError("idempotency_key and fingerprint are required")
        with self._lock:
            prior = self._keys.get(idempotency_key)
            if prior:
                if prior[0] != fingerprint:
                    raise IdempotencyConflict("key already used for a different request")
                return self._cases[prior[1]]
            case = Case(uuid4())
            self._cases[case.case_id] = case
            self._keys[idempotency_key] = (fingerprint, case.case_id)
            return case

    def get(self, case_id: UUID) -> Case:
        with self._lock:
            return self._cases[case_id]

    def confirm(self, case_id: UUID, *, idempotency_key: str) -> Case:
        return self._transition(case_id, CaseStatus.DRAFT, CaseStatus.CONFIRMED,
                                idempotency_key, "case.confirmed")

    def queue_for_submission(self, case_id: UUID, *, idempotency_key: str) -> Case:
        return self._transition(case_id, CaseStatus.CONFIRMED,
                                CaseStatus.QUEUED_FOR_SUBMISSION, idempotency_key,
                                "case.submission_queued")

    def record_verified_receipt(
        self, case_id: UUID, *, receipt_reference: str, verified: bool,
        idempotency_key: str, verified_at: datetime | None = None,
    ) -> Case:
        if not verified or not receipt_reference.strip():
            raise TransitionError("SUBMITTED requires a verified non-empty receipt")
        now = verified_at or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("verified_at must be timezone-aware")
        with self._lock:
            case = self._cases[case_id]
            if case.status is CaseStatus.SUBMITTED:
                event = self._event_for_key(idempotency_key)
                if event and event.aggregate_id == case_id and case.receipt_reference == receipt_reference:
                    return case
                raise TransitionError("case already submitted")
            if case.status is not CaseStatus.QUEUED_FOR_SUBMISSION:
                raise TransitionError("only queued cases can be submitted")
            updated = Case(case_id, CaseStatus.SUBMITTED, case.version + 1,
                           receipt_reference, now)
            self._cases[case_id] = updated
            self._append_outbox(case_id, "case.submitted", idempotency_key,
                                (("receipt_reference", receipt_reference),))
            return updated

    def outbox(self) -> tuple[OutboxEvent, ...]:
        with self._lock:
            return tuple(self._outbox)

    def _transition(self, case_id: UUID, expected: CaseStatus, target: CaseStatus,
                    key: str, event_type: str) -> Case:
        if not key.strip():
            raise ValueError("idempotency_key is required")
        with self._lock:
            prior = self._event_for_key(key)
            if prior:
                if prior.aggregate_id != case_id or prior.event_type != event_type:
                    raise IdempotencyConflict("key already used for another operation")
                return self._cases[case_id]
            case = self._cases[case_id]
            if case.status is not expected:
                raise TransitionError(f"expected {expected.value}, found {case.status.value}")
            updated = Case(case_id, target, case.version + 1)
            self._cases[case_id] = updated
            self._append_outbox(case_id, event_type, key)
            return updated

    def _event_for_key(self, key: str) -> OutboxEvent | None:
        return next((event for event in self._outbox if event.idempotency_key == key), None)

    def _append_outbox(self, case_id: UUID, event_type: str, key: str,
                       payload: tuple[tuple[str, str], ...] = ()) -> None:
        prior = self._event_for_key(key)
        if prior:
            if prior.aggregate_id != case_id or prior.event_type != event_type:
                raise IdempotencyConflict("outbox key collision")
            return
        self._outbox.append(OutboxEvent(uuid4(), case_id, event_type, key,
                                        datetime.now(timezone.utc), payload))


class OutboxStore:
    """Small idempotent in-memory outbox abstraction for adapter-independent tests."""
    def __init__(self) -> None:
        self._events: dict[str, OutboxEvent] = {}
        self._lock = RLock()

    def enqueue(self, *, aggregate_id: UUID, event_type: str, idempotency_key: str,
                payload: Iterable[tuple[str, str]] = ()) -> OutboxEvent:
        if not idempotency_key.strip() or not event_type.strip():
            raise ValueError("event_type and idempotency_key are required")
        normalized = tuple(sorted(payload))
        fingerprint = sha256(repr((aggregate_id, event_type, normalized)).encode()).hexdigest()
        with self._lock:
            existing = self._events.get(idempotency_key)
            if existing:
                old = sha256(repr((existing.aggregate_id, existing.event_type,
                                   existing.payload)).encode()).hexdigest()
                if old != fingerprint:
                    raise IdempotencyConflict("outbox key reused with different content")
                return existing
            event = OutboxEvent(uuid4(), aggregate_id, event_type, idempotency_key,
                                datetime.now(timezone.utc), normalized)
            self._events[idempotency_key] = event
            return event

    def pending(self) -> tuple[OutboxEvent, ...]:
        with self._lock:
            return tuple(event for event in self._events.values() if event.delivered_at is None)

    def mark_delivered(self, idempotency_key: str, *, at: datetime | None = None) -> OutboxEvent:
        stamp = at or datetime.now(timezone.utc)
        if stamp.tzinfo is None:
            raise ValueError("delivery timestamp must be timezone-aware")
        with self._lock:
            event = self._events[idempotency_key]
            if event.delivered_at is None:
                event = OutboxEvent(event.event_id, event.aggregate_id, event.event_type,
                                    event.idempotency_key, event.created_at, event.payload, stamp)
                self._events[idempotency_key] = event
            return event


@dataclass(frozen=True, slots=True)
class MemoryScope:
    kind: str
    owner_id: str
    ttl: timedelta | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"session", "user", "case"}:
            raise ValueError("scope kind must be session, user, or case")
        if not self.owner_id.strip():
            raise ValueError("scope owner_id is required")
        if self.ttl is not None and self.ttl <= timedelta(0):
            raise ValueError("ttl must be positive")


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    memory_id: UUID
    scope: MemoryScope
    key: str
    value: str
    created_at: datetime
    expires_at: datetime | None
    deleted_at: datetime | None = None

    def is_active(self, *, now: datetime | None = None) -> bool:
        instant = now or datetime.now(timezone.utc)
        return self.deleted_at is None and (self.expires_at is None or self.expires_at > instant)


@dataclass(frozen=True, slots=True)
class DuplicateCandidate:
    case_id: UUID
    distance_m: float
    time_delta_seconds: float


def resolve_location(point: tuple[float, float], wards: Iterable[tuple[str, tuple[float, float, float, float]]],
                     landmarks: Iterable[tuple[str, str, tuple[float, float]]],
                     *, landmark_radius_m: float = 500.0) -> dict[str, object]:
    """Resolve lon/lat against bounding-box ward fixtures and nearby landmarks.

    This deterministic helper is for testing. Production resolution uses PostGIS.
    Returns candidate identifiers only; a ward match may remain ambiguous.
    """
    lon, lat = point
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError("coordinates outside WGS84 range")
    matches = tuple(sorted(name for name, (xmin, ymin, xmax, ymax) in wards
                           if xmin <= lon <= xmax and ymin <= lat <= ymax))
    nearby = tuple(sorted((name, _haversine_m(point, coords))
                          for name, _kind, coords in landmarks
                          if _haversine_m(point, coords) <= landmark_radius_m))
    return {"ward_candidates": matches, "ward": matches[0] if len(matches) == 1 else None,
            "landmarks": nearby}


def advisory_duplicate_candidates(
    target: tuple[float, datetime], candidates: Iterable[tuple[UUID, tuple[float, datetime]]],
    *, radius_m: float = 100.0, window: timedelta = timedelta(days=7),
) -> tuple[DuplicateCandidate, ...]:
    """Rank spatial/time-near cases as advisory candidates; never merges cases."""
    point, created = target
    if created.tzinfo is None:
        raise ValueError("target timestamp must be timezone-aware")
    result = []
    for case_id, (other_point, other_time) in candidates:
        if other_time.tzinfo is None:
            raise ValueError("candidate timestamp must be timezone-aware")
        distance = _haversine_m(point, other_point)
        delta = abs((created - other_time).total_seconds())
        if distance <= radius_m and delta <= window.total_seconds():
            result.append(DuplicateCandidate(case_id, distance, delta))
    return tuple(sorted(result, key=lambda item: (item.distance_m, item.time_delta_seconds, str(item.case_id))))


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    from math import asin, cos, radians, sin, sqrt
    lon1, lat1 = map(radians, a)
    lon2, lat2 = map(radians, b)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6_371_000 * 2 * asin(sqrt(h))
