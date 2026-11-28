from backend.voice_v1.orchestration import (
    ActionKind,
    Aggregator,
    DeclarativeSchema,
    DigressionStack,
    IdempotencyLedger,
    Intent,
    IntentDecomposer,
    MutationAuthorization,
    OrchestrationTask,
    PrefetchPolicy,
    ProgressNarrator,
    SlotDefinition,
    SlotPatch,
    SlotStore,
    TaskResult,
    ToolDefinition,
    ToolRegistry,
    ToolSchedule,
    Watchdog,
)
from backend.voice_v1.turn_policy import SessionState, TurnCoordinator
import pytest


def test_mutations_require_explicit_confirmed_authorization_but_reads_do_not():
    events = []
    registry = ToolRegistry()
    registry.register(ToolDefinition("lookup", ActionKind.READ_ONLY, ToolSchedule.BLOCKING,
                                     lambda item: events.append(("read", item)) or item))
    registry.register(ToolDefinition("submit", ActionKind.MUTATION, ToolSchedule.BLOCKING,
                                     lambda item: events.append(("write", item)) or "done"))
    assert registry.execute("lookup", "x") == "x"
    with pytest.raises(PermissionError):
        registry.execute("submit", "x")
    with pytest.raises(PermissionError):
        registry.execute("submit", "x", authorization=MutationAuthorization(True))
    assert registry.execute("submit", "x", authorization=MutationAuthorization(True, "confirm-1")) == "done"
    assert events == [("read", "x"), ("write", "x")]


def test_speculation_requires_stable_intent_and_readonly_tool():
    registry = ToolRegistry()
    registry.register(ToolDefinition("read", ActionKind.READ_ONLY, ToolSchedule.SILENT, lambda: 7))
    registry.register(ToolDefinition("write", ActionKind.MUTATION, ToolSchedule.SILENT, lambda: 8))
    assert not PrefetchPolicy.may_prefetch(registry.get("read"), intent_stable=False)
    assert PrefetchPolicy.may_prefetch(registry.get("read"), intent_stable=True)
    with pytest.raises(PermissionError):
        PrefetchPolicy.prefetch(registry, "read", intent_stable=False)
    assert PrefetchPolicy.prefetch(registry, "read", intent_stable=True) == 7
    assert not PrefetchPolicy.may_prefetch(registry.get("write"))
    with pytest.raises(PermissionError):
        PrefetchPolicy.prefetch(registry, "write")


def test_declarative_schema_intents_and_epoch_checked_external_patches():
    schema = DeclarativeSchema("service_request", (SlotDefinition("location", required=True),
                                                   SlotDefinition("issue")))
    assert IntentDecomposer(schema.by_name).decompose([Intent("report", required_slots=("location",))])
    with pytest.raises(ValueError):
        IntentDecomposer(schema.by_name).decompose([Intent("bad", required_slots=("unknown",))])
    store = SlotStore(schema)
    assert store.apply_external(SlotPatch({"location": "Anna Nagar"}, epoch=0), current_epoch=0)
    store.invalidate(1)
    assert not store.apply_external(SlotPatch({"issue": "lamp"}, epoch=0), current_epoch=1)
    assert store.values == {}
    assert store.apply_external(SlotPatch({"issue": "lamp"}, epoch=1), current_epoch=1)


def test_dedupe_aggregation_watchdog_and_narration_scheduling():
    calls = []
    ledger = IdempotencyLedger()
    operation = lambda: calls.append("ran") or 42
    assert ledger.run("key", operation) == ledger.run("key", operation) == 42
    assert calls == ["ran"]
    assert [r.task_id for r in Aggregator.combine(
        ["a", "b"], [TaskResult("b", 2), TaskResult("a", 1)]
    )] == ["a", "b"]
    task = OrchestrationTask("t", "lookup", ToolSchedule.NON_BLOCKING, 0, 10)
    assert not Watchdog.expired(task, now=9)
    with pytest.raises(TimeoutError):
        Watchdog.check(task, now=10)
    assert ProgressNarrator.message("request", ToolSchedule.SILENT) is None
    assert ProgressNarrator.message("request", ToolSchedule.WHEN_IDLE, idle=False) is None
    assert ProgressNarrator.message("request", ToolSchedule.WHEN_IDLE, idle=True) == "Working on request."
    assert ProgressNarrator.message("request", ToolSchedule.INTERRUPT) == "Working on request."


def test_digression_stack_and_turn_pause_resume_keep_epoch_until_committed():
    stack = DigressionStack()
    stack.pause({"goal": "file report"})
    assert stack.resume() == {"goal": "file report"}
    turn = TurnCoordinator()
    turn.start_generation()
    epoch = turn.start_speaking()
    turn.pause_for_possible_barge_in()
    stack.pause("resume-this-after-digression")
    assert turn.state is SessionState.PAUSED
    assert turn.resolve_incoming_speech(is_backchannel=True) == epoch
    assert turn.state is SessionState.SPEAKING
    assert stack.resume() == "resume-this-after-digression"
    turn.pause_for_possible_barge_in()
    assert turn.resolve_incoming_speech(is_backchannel=False) == epoch + 1
    assert not turn.is_current_epoch(epoch)
