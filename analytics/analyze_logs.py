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


def _valid_ms(value: object) -> float | None:
    if type(value) in (int, float) and math.isfinite(value) and value >= 0:
        return float(value)
    return None


def _fmt_dist(label: str, samples: list[float]) -> str:
    return (
        f"{label} ({len(samples)} samples) | "
        f"P50 {percentile(samples, .50)} | P90 {percentile(samples, .90)} | P95 {percentile(samples, .95)}"
    )


def summarize(logs: Path, convs: Path) -> int:
    latencies: list[float] = []
    by_model: dict[str, list[float]] = {}
    llm_ttft: list[float] = []
    tts_synth: list[float] = []
    tts_all: list[float] = []
    ttfa_samples: list[float] = []
    stage_counts: Counter[str] = Counter()
    pipeline_states: Counter[str] = Counter()
    conversation_states: Counter[str] = Counter()
    leaks = []
    count = 0
    pending_wf: tuple[float, float] | None = None

    for index, event in read_records(logs):
        count += 1
        if has_pii(event):
            leaks.append((logs.name, index))
        stage = str(event.get("stage", ""))
        stage_counts[stage] += 1
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        ts = _valid_ms(event.get("ts"))
        ms = _valid_ms(data.get("latency_ms"))

        if stage == "workflow.turn_complete":
            if ms is not None:
                latencies.append(ms)
                model = str(data.get("model") or "unknown")
                by_model.setdefault(model, []).append(ms)
                if ts is not None:
                    pending_wf = (ts, ms)
            match = WORKFLOW_STATE.match(str(event.get("message", "")))
            if match and match[1] in FSM_STATES:
                pipeline_states[match[1]] += 1
        elif stage == "llm.fast_turn" and ms is not None:
            llm_ttft.append(ms)
        elif stage == "tts.neural_synth" and ms is not None:
            tts_synth.append(ms)
            tts_all.append(ms)
            if pending_wf and ts is not None and 0 <= ts - pending_wf[0] <= 10.0:
                ttfa_samples.append(pending_wf[1] + ms)
                pending_wf = None
        elif stage == "tts.cache_hit":
            tts_all.append(0.0)
            if pending_wf and ts is not None and 0 <= ts - pending_wf[0] <= 10.0:
                ttfa_samples.append(pending_wf[1])
                pending_wf = None

    for index, turn in read_records(convs):
        count += 1
        if has_pii(turn):
            leaks.append((convs.name, index))
        fsm_state = str(turn.get("fsm_state", ""))
        if turn.get("role") == "user" and fsm_state in FSM_STATES:
            conversation_states[fsm_state] += 1

    print(_fmt_dist("Workflow latency", latencies))
    for model, vals in sorted(by_model.items()):
        print(f"  - {model}: {_fmt_dist('Workflow', vals)}")
    print(_fmt_dist("LLM / TTFT (llm.fast_turn)", llm_ttft))
    print(_fmt_dist("TTS synth (tts.neural_synth)", tts_synth))
    cache_hits = stage_counts["tts.cache_hit"]
    cache_rate = (cache_hits / len(tts_all) * 100) if tts_all else 0.0
    print(f"{_fmt_dist('TTS all incl. cache', tts_all)} | cache_hit={cache_hits}/{len(tts_all)} ({cache_rate:.1f}%)")
    print(_fmt_dist("End-to-End TTFA (Workflow + TTS)", ttfa_samples))
    print(
        "Voice & Guardrail counters: "
        f"stt_final={stage_counts['stt.final']}, sarvam_stt={stage_counts['stt.sarvam_saaras']}, "
        f"noise_filtered={stage_counts['stt.noise_filtered']}, stt_error={stage_counts['stt.error']}, "
        f"barge_in={stage_counts['tts.barge_in']}, aadhaar_blocked={stage_counts['guardrail.aadhaar_blocked']}"
    )
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
