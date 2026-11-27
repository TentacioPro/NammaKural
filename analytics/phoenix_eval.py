"""Run NammaKural golden evals and stream OTLP traces + eval metrics to Arize Phoenix.

Usage:
  1. Start local Arize Phoenix: `docker run -p 6006:6006 arizephoenix/phoenix:latest` (or `phoenix serve`)
  2. Run: `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:6006/v1/traces python analytics/phoenix_eval.py`
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.agent_workflow import run_workflow_turn
from backend.telemetry import emit_otlp_span, get_otlp_endpoint


def run_phoenix_eval(golden_path: Path) -> int:
    cases = [json.loads(ln) for ln in golden_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    passed = 0
    latencies: list[float] = []

    for idx, case in enumerate(cases, start=1):
        name = case.get("id") or f"case-{idx}"
        turns = case.get("turns") or []
        expected = case.get("expect") or {}
        sid = f"phoenix-eval-{idx}-{int(time.time())}"
        res = {}
        t0 = time.monotonic()
        for t in turns:
            res = run_workflow_turn(
                utterance=t.get("utterance", ""),
                combined_text=t.get("combined_text", t.get("utterance", "")),
                state_code=case.get("state_code", "tn"),
                lang=case.get("lang", "tanglish"),
                llm_mode=case.get("llm_mode", "offline"),
                session_id=sid,
                dpdp_consented=t.get("dpdp_consented", True),
                otp_verified=t.get("otp_verified", False),
            )
        elapsed_ms = round((time.monotonic() - t0) * 1000, 2)
        latencies.append(elapsed_ms)

        ok = True
        if "fsm_state" in expected and res.get("fsm_state") != expected["fsm_state"]:
            ok = False
        if "ward" in expected and res.get("analysis", {}).get("landmark", {}).get("ward") != expected["ward"]:
            ok = False
        if "service_id" in expected and res.get("analysis", {}).get("service_id") != expected["service_id"]:
            ok = False

        if ok:
            passed += 1

        emit_otlp_span(
            name=f"eval.{name}",
            attributes={
                "eval.case_id": name,
                "eval.passed": ok,
                "eval.fsm_state": res.get("fsm_state", ""),
                "eval.ward": res.get("analysis", {}).get("landmark", {}).get("ward", ""),
                "eval.service_id": res.get("analysis", {}).get("service_id", ""),
                "openinference.span.kind": "EVALUATOR",
            },
            duration_ms=elapsed_ms,
            status_ok=ok,
        )

    avg_ms = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    ep = get_otlp_endpoint() or "disabled (set OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:6006/v1/traces)"
    print(f"Phoenix Eval: {passed}/{len(cases)} passed | avg={avg_ms} ms | otlp={ep}")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    golden = ROOT / "analytics" / "golden_cases.jsonl"
    raise SystemExit(run_phoenix_eval(golden))
