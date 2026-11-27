"""Report workflow latency, FSM activity, and potential PII in civic JSONL logs."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.state import scrub_pii_and_aadhaar

GROUPED_NUMBER = re.compile(r"(?<!\w)(?:\+91[ -]?)?(?:[6-9]\d{4}[ -]\d{5}|[6-9]\d{2}[ -]\d{3}[ -]\d{4})(?!\w)")
IDENTIFIER = re.compile(r"\b(?:otp|one.time (?:code|password)|consumer (?:id|number))\s*[:=#-]?\s*\d{4,19}\b", re.IGNORECASE)
PII_FIELDS = {
    "phone", "phone_number", "mobile", "mobile_number", "email", "email_address",
    "aadhaar", "aadhaar_number", "otp", "otp_code", "consumer_number", "consumer_id",
    "api_key", "authorization",
}
MASKED_VALUES = {"[REDACTED_NUM]", "[REDACTED_EMAIL]", "[AADHAAR_BLOCKED]", "[REDACTED]", "[MASKED]"}
WORKFLOW_STATE = re.compile(r"^FSM=([A-Z_]+)\b")
FSM_STATES = {"GREET", "TRIAGE", "DISAMBIGUATE", "CONFIRM_CLARITY",
              "COOLDOWN_AND_OTP", "HITL_SEAL", "DISPATCH", "LIFE_SAFETY"}


def read_records(path: Path) -> Iterator[tuple[int, dict]]:
    with path.open(encoding="utf-8-sig") as source:
        for number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError:
                raise ValueError(f"{path.name}:{number}: malformed JSON") from None
            if not isinstance(record, dict):
                raise ValueError(f"{path.name}:{number}: expected a JSON object")
            yield number, record


def has_pii(value, field: str = "") -> bool:
    if isinstance(value, dict):
        return any(has_pii(key) or has_pii(item, key.lower()) for key, item in value.items())
    if isinstance(value, list):
        return any(has_pii(item, field) for item in value)
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        raw = str(value)
        if not raw.strip() or raw in MASKED_VALUES:
            return False
        if field in PII_FIELDS:
            return bool(re.search(r"\d{4}|@|[a-zA-Z0-9]{8}", raw))
        return (
            scrub_pii_and_aadhaar(raw)["clean_text"] != raw
            or bool(GROUPED_NUMBER.search(raw) or IDENTIFIER.search(raw))
        )
    return False


def percentile(samples: list[float], fraction: float) -> str:
    if not samples:
        return "unavailable"
    ordered = sorted(samples)
    return f"{ordered[math.ceil(len(ordered) * fraction) - 1]:.2f} ms"


def summarize(logs: Path, convs: Path) -> int:
    latencies = []
    pipeline_states = Counter()
    conversation_states = Counter()
    leaks = []
    count = 0

    for index, event in read_records(logs):
        count += 1
        if has_pii(event):
            leaks.append((logs.name, index))
        if event.get("stage") != "workflow.turn_complete":
            continue
        data = event.get("data")
        latency = data.get("latency_ms") if isinstance(data, dict) else None
        if type(latency) in (int, float) and math.isfinite(latency) and latency >= 0:
            latencies.append(latency)
        match = WORKFLOW_STATE.match(str(event.get("message", "")))
        if match and match[1] in FSM_STATES:
            pipeline_states[match[1]] += 1

    for index, turn in read_records(convs):
        count += 1
        if has_pii(turn):
            leaks.append((convs.name, index))
        fsm_state = str(turn.get("fsm_state", ""))
        if turn.get("role") == "user" and fsm_state in FSM_STATES:
            conversation_states[fsm_state] += 1

    print(f"Workflow latency ({len(latencies)} samples) | P50 {percentile(latencies, .50)} | P95 {percentile(latencies, .95)}")
    for label, funnel in (("Pipeline", pipeline_states), ("Conversation", conversation_states)):
        formatted = ", ".join(f"{state}={amount}" for state, amount in sorted(funnel.items()))
        print(f"{label} FSM state funnel: {formatted or 'no state records'}")
    print(f"PII firewall: {len(leaks)} PII leaks across {count} records")
    for name, line in leaks:
        print(f"  {name}:{line}")
    return int(bool(leaks))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", required=True, type=Path)
    parser.add_argument("--convs", required=True, type=Path)
    args = parser.parse_args()
    try:
        return summarize(args.logs, args.convs)
    except ValueError as error:
        print(error, file=sys.stderr)
    except OSError as error:
        print(f"Unable to read a log file ({type(error).__name__}).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
