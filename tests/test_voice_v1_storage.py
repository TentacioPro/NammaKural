from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from backend.voice_v1.storage import (
    CaseLifecycle,
    CaseStatus,
    IdempotencyConflict,
    MemoryEntry,
    MemoryScope,
    OutboxStore,
    TransitionError,
    advisory_duplicate_candidates,
    resolve_location,
)


def test_lifecycle_requires_ordered_transitions_and_verified_receipt():
    lifecycle = CaseLifecycle()
    case = lifecycle.create(idempotency_key="create-1", fingerprint="f1")
    assert case.status is CaseStatus.DRAFT
    with pytest.raises(TransitionError):
        lifecycle.queue_for_submission(case.case_id, idempotency_key="queue-early")
    with pytest.raises(TransitionError):
        lifecycle.record_verified_receipt(case.case_id, receipt_reference="", verified=True,
                                          idempotency_key="receipt-empty")
    confirmed = lifecycle.confirm(case.case_id, idempotency_key="confirm-1")
    assert confirmed.status is CaseStatus.CONFIRMED
    queued = lifecycle.queue_for_submission(case.case_id, idempotency_key="queue-1")
    assert queued.status is CaseStatus.QUEUED_FOR_SUBMISSION
    with pytest.raises(TransitionError):
        lifecycle.record_verified_receipt(case.case_id, receipt_reference="R-1", verified=False,
                                          idempotency_key="receipt-unverified")
    stamp = datetime.now(timezone.utc)
    submitted = lifecycle.record_verified_receipt(case.case_id, receipt_reference="R-1",
                                                   verified=True, idempotency_key="receipt-1",
                                                   verified_at=stamp)
    assert submitted.status is CaseStatus.SUBMITTED
    assert submitted.receipt_reference == "R-1"
    assert submitted.receipt_verified_at == stamp
    assert submitted.version == 3
    assert [event.event_type for event in lifecycle.outbox()] == [
        "case.confirmed", "case.submission_queued", "case.submitted"
    ]


def test_create_and_transitions_are_idempotent_but_conflicts_rejected():
    lifecycle = CaseLifecycle()
    first = lifecycle.create(idempotency_key="create", fingerprint="same")
    assert lifecycle.create(idempotency_key="create", fingerprint="same") == first
    with pytest.raises(IdempotencyConflict):
        lifecycle.create(idempotency_key="create", fingerprint="different")
    assert lifecycle.confirm(first.case_id, idempotency_key="confirm") == lifecycle.confirm(
        first.case_id, idempotency_key="confirm"
    )
    with pytest.raises(IdempotencyConflict):
        lifecycle.queue_for_submission(first.case_id, idempotency_key="confirm")
    assert len(lifecycle.outbox()) == 1


def test_outbox_deduplicates_same_operation_and_rejects_key_reuse():
    store = OutboxStore()
    aggregate = uuid4()
    a = store.enqueue(aggregate_id=aggregate, event_type="changed", idempotency_key="k",
                      payload=(("status", "ok"),))
    assert store.enqueue(aggregate_id=aggregate, event_type="changed", idempotency_key="k",
                         payload=(("status", "ok"),)) == a
    with pytest.raises(IdempotencyConflict):
        store.enqueue(aggregate_id=aggregate, event_type="changed", idempotency_key="k",
                      payload=(("status", "different"),))
    assert len(store.pending()) == 1
    delivered = store.mark_delivered("k")
    assert delivered.delivered_at is not None
    assert store.pending() == ()


def test_duplicate_matching_is_advisory_spatial_and_temporal():
    now = datetime.now(timezone.utc)
    near = uuid4()
    far = uuid4()
    result = advisory_duplicate_candidates(
        ((80.2707, 13.0827), now),
        [(near, ((80.2708, 13.0828), now - timedelta(hours=2))),
         (far, ((80.5, 13.3), now))],
        radius_m=100, window=timedelta(days=1),
    )
    assert [item.case_id for item in result] == [near]
    assert result[0].distance_m < 100
    assert result[0].time_delta_seconds == 7200


def test_location_resolution_preserves_ward_ambiguity_and_returns_near_landmark():
    resolved = resolve_location(
        (80.27, 13.08),
        [("ward-a", (80.0, 12.9, 80.5, 13.2)), ("ward-b", (80.2, 13.0, 80.4, 13.1))],
        [("Central stop", "transit", (80.2701, 13.0801))],
    )
    assert resolved["ward_candidates"] == ("ward-a", "ward-b")
    assert resolved["ward"] is None
    assert resolved["landmarks"][0][0] == "Central stop"


def test_memory_scopes_ttl_and_tombstone_semantics():
    now = datetime.now(timezone.utc)
    scope = MemoryScope("session", "opaque-session", ttl=timedelta(hours=1))
    live = MemoryEntry(uuid4(), scope, "language", "ta", now, now + timedelta(hours=1))
    expired = MemoryEntry(uuid4(), scope, "intent", "road", now, now - timedelta(seconds=1))
    deleted = MemoryEntry(uuid4(), scope, "preference", "x", now, None, deleted_at=now)
    assert live.is_active(now=now)
    assert not expired.is_active(now=now)
    assert not deleted.is_active(now=now)
    with pytest.raises(ValueError):
        MemoryScope("global", "owner")
    with pytest.raises(ValueError):
        MemoryScope("user", "owner", ttl=timedelta(0))
