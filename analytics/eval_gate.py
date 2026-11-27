"""Replay synthetic civic conversations against the deterministic workflow."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.agent_workflow import run_workflow_turn, split_tts_clauses

TAMIL_SPEECH = re.compile(r"[\u0B80-\u0BFF0-9\s.!?,]+")
TAMIL_LETTER = re.compile(r"[\u0B85-\u0BB9]")
_MISSING = object()


def load_cases(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as source:
        cases = [json.loads(line) for line in source if line.strip()]
    ids = [case["id"] for case in cases]
    if len(cases) < 25 or len(set(ids)) != len(ids):
        raise ValueError("Expected at least 25 distinctly named cases.")
    if any(not case["turns"] or any(not turn["expect"] for turn in case["turns"]) for case in cases):
        raise ValueError("Each case needs at least one turn and each turn needs assertions.")
    return cases


def read_path(result: dict, path: str):
    value = result
    for key in path.split("."):
        if not isinstance(value, dict):
            return _MISSING
        value = value.get(key, _MISSING)
    return value


def replay_case(case: dict) -> list[str]:
    errors = []
    context = []
    session = uuid4().hex if case.get("use_session") else None
    for turn_index, turn in enumerate(case["turns"], start=1):
        args = turn["input"].copy()
        context.append(args["utterance"])
        args.setdefault("combined_text", args["utterance"] if session else " ".join(context))
        args["session_id"] = session
        args["llm_mode"] = "offline"
        actual = run_workflow_turn(**args)
        for path, expected in turn["expect"].items():
            if read_path(actual, path) != expected:
                errors.append(f"turn {turn_index}: expected value differs at {path}")
        speech = actual.get("tts_text")
        if (
            not isinstance(speech, str)
            or actual.get("display_text") != actual.get("reply")
            or bool(speech) != bool(actual.get("reply"))
            or (speech and not (TAMIL_SPEECH.fullmatch(speech) and TAMIL_LETTER.search(speech)))
            or actual.get("clauses") != split_tts_clauses(speech)
        ):
            errors.append(f"turn {turn_index}: invalid display or Tamil speech fields")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, required=True)
    args = parser.parse_args()
    try:
        cases = load_cases(args.golden)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Unable to read golden cases ({type(error).__name__}).", file=sys.stderr)
        return 1

    passed = 0
    # Synthetic evals should not append to production latency and funnel data.
    with patch("backend.agent_workflow.log_event"):
        for case in cases:
            errors = replay_case(case)
            print(f"{'FAIL' if errors else 'PASS'} {case['id']}")
            for error in errors:
                print(f"  {error}")
            passed += not errors
    print(f"{passed}/{len(cases)} passed ({passed / len(cases):.0%})")
    return int(passed != len(cases))


if __name__ == "__main__":
    raise SystemExit(main())
