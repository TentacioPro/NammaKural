"""Pure in-memory orchestration policy; deliberately makes no external calls.

This module is scaffolding only. Adapters, persistence, authorization identity, and
transport integration must be supplied and reviewed separately.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from time import monotonic
from typing import Any, Callable, Iterable, Mapping


class ActionKind(StrEnum):
    READ_ONLY = "read_only"
    MUTATION = "mutation"


class ToolSchedule(StrEnum):
    BLOCKING = "blocking"
    NON_BLOCKING = "non_blocking"
    SILENT = "silent"
    WHEN_IDLE = "when_idle"
    INTERRUPT = "interrupt"


@dataclass(frozen=True, slots=True)
class SlotDefinition:
    name: str
    kind: str = "free_text"
    required: bool = False
    sensitive: bool = False
    description: str = ""


@dataclass(frozen=True, slots=True)
class DeclarativeSchema:
    name: str
    slots: tuple[SlotDefinition, ...]

    def __post_init__(self) -> None:
        names = [slot.name for slot in self.slots]
        if not self.name or len(names) != len(set(names)):
            raise ValueError("schema needs a name and unique slot names")

    @property
    def by_name(self) -> Mapping[str, SlotDefinition]:
        return {slot.name: slot for slot in self.slots}


@dataclass(frozen=True, slots=True)
class Intent:
    name: str
    description: str = ""
    required_slots: tuple[str, ...] = ()


class IntentDecomposer:
    """Validates caller-supplied intent decomposition; does not infer or call an LLM."""
    def __init__(self, known_slots: Iterable[str]):
        self.known_slots = frozenset(known_slots)

    def decompose(self, intents: Iterable[Intent]) -> tuple[Intent, ...]:
        result = tuple(intents)
        if len({i.name for i in result}) != len(result):
            raise ValueError("intent names must be unique")
        for intent in result:
            unknown = set(intent.required_slots) - self.known_slots
            if unknown:
                raise ValueError(f"unknown slots for {intent.name}: {sorted(unknown)}")
        return result


@dataclass(slots=True)
class DigressionStack:
    """LIFO continuation stack to suspend and resume the current conversation goal."""
    _items: list[Any] = field(default_factory=list)

    def pause(self, continuation: Any) -> None:
        self._items.append(continuation)

    def resume(self) -> Any | None:
        return self._items.pop() if self._items else None

    def __len__(self) -> int:
        return len(self._items)


@dataclass(frozen=True, slots=True)
class MutationAuthorization:
    confirmed: bool = False
    confirmation_id: str | None = None


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    action: ActionKind
    schedule: ToolSchedule
    handler: Callable[..., Any]
    idempotent: bool = True
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not self.name or self.timeout_seconds <= 0:
            raise ValueError("tool name and positive timeout are required")


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    def execute(self, name: str, *args: Any, authorization: MutationAuthorization | None = None,
                **kwargs: Any) -> Any:
        tool = self.get(name)
        if tool.action is ActionKind.MUTATION and not (
            authorization and authorization.confirmed and authorization.confirmation_id
        ):
            raise PermissionError("mutation requires explicit confirmed authorization")
        return tool.handler(*args, **kwargs)


class PrefetchPolicy:
    """Speculative work is permitted only for registered read-only tools."""
    @staticmethod
    def may_prefetch(tool: ToolDefinition, *, intent_stable: bool = False) -> bool:
        return tool.action is ActionKind.READ_ONLY and intent_stable

    @staticmethod
    def prefetch(registry: ToolRegistry, name: str, *args: Any,
                 intent_stable: bool = False, **kwargs: Any) -> Any:
        tool = registry.get(name)
        if not PrefetchPolicy.may_prefetch(tool, intent_stable=intent_stable):
            raise PermissionError("prefetch requires a stable intent and a read-only tool")
        return tool.handler(*args, **kwargs)


@dataclass(frozen=True, slots=True)
class TaskResult:
    task_id: str
    value: Any = None
    error: str | None = None
    epoch: int = 0


class Aggregator:
    """Stable, deterministic collection preserving the declared task order."""
    @staticmethod
    def combine(task_ids: Iterable[str], results: Iterable[TaskResult]) -> tuple[TaskResult, ...]:
        wanted = tuple(task_ids)
        result_list = tuple(results)
        indexed = {r.task_id: r for r in result_list}
        if len(indexed) != len(result_list):
            raise ValueError("duplicate task results")
        missing = set(wanted) - indexed.keys()
        if missing:
            raise ValueError(f"missing results: {sorted(missing)}")
        return tuple(indexed[task_id] for task_id in wanted)


@dataclass(frozen=True, slots=True)
class OrchestrationTask:
    task_id: str
    tool_name: str
    schedule: ToolSchedule
    epoch: int
    deadline_monotonic: float


class Watchdog:
    """Deadline checks are explicit and deterministic; it does not spawn timers."""
    @staticmethod
    def expired(task: OrchestrationTask, *, now: float | None = None) -> bool:
        return (monotonic() if now is None else now) >= task.deadline_monotonic

    @staticmethod
    def check(task: OrchestrationTask, *, now: float | None = None) -> None:
        if Watchdog.expired(task, now=now):
            raise TimeoutError(f"task deadline exceeded: {task.task_id}")


class IdempotencyLedger:
    """Process-local cache keyed by caller-supplied idempotency key."""
    def __init__(self) -> None:
        self._results: dict[str, Any] = {}

    def run(self, key: str, operation: Callable[[], Any]) -> Any:
        if not key:
            raise ValueError("idempotency key is required")
        if key not in self._results:
            self._results[key] = operation()
        return self._results[key]


class ProgressNarrator:
    """Emits concise progress only when policy allows, without doing I/O."""
    @staticmethod
    def should_narrate(schedule: ToolSchedule, *, idle: bool = False) -> bool:
        if schedule is ToolSchedule.SILENT:
            return False
        if schedule is ToolSchedule.WHEN_IDLE:
            return idle
        return True

    @staticmethod
    def message(label: str, schedule: ToolSchedule, *, idle: bool = False) -> str | None:
        return f"Working on {label}." if ProgressNarrator.should_narrate(schedule, idle=idle) else None


@dataclass(frozen=True, slots=True)
class SlotPatch:
    values: Mapping[str, Any]
    epoch: int
    source: str = "external"


class SlotStore:
    """Validated slot values with optimistic epoch invalidation for external patches."""
    def __init__(self, schema: DeclarativeSchema, *, epoch: int = 0) -> None:
        self.schema = schema
        self.epoch = epoch
        self.values: dict[str, Any] = {}

    def apply_external(self, patch: SlotPatch, *, current_epoch: int) -> bool:
        if patch.epoch != current_epoch or patch.epoch != self.epoch:
            return False
        unknown = set(patch.values) - self.schema.by_name.keys()
        if unknown:
            raise ValueError(f"unknown slots: {sorted(unknown)}")
        self.values.update(patch.values)
        return True

    def invalidate(self, new_epoch: int) -> None:
        if new_epoch <= self.epoch:
            raise ValueError("epoch must increase")
        self.epoch = new_epoch
        self.values.clear()
