"""End-to-end Arize Phoenix evaluation suite for NammaKural.

Evaluates all golden cases across 6 dimensions:
  1. fsm_accuracy      — Expected FSM state reached
  2. ward_accuracy     — Expected Ward resolved (and no fabricated Ward on unseen places)
  3. service_accuracy  — Expected civic service/agency selected
  4. tamil_tts_purity  — Zero Latin leakage in Tamil `tts_text`
  5. pii_firewall      — Zero raw Aadhaar / phone / email in outputs
  6. latency_sla       — P50 / P90 / P95 & % under 500 ms

Streams OpenInference spans to Phoenix (`http://localhost:6006/v1/traces`) and
registers/updates the `nammakural-e2e-golden` dataset in Phoenix when running.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.eval_gate import replay_case
from backend.agent_workflow import run_workflow_turn
from backend.telemetry import emit_otlp_span, get_otlp_endpoint

_RAW_PII_RE = re.compile(r"(?:\b[6-9]\d{9}\b|\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b|[\w.\-]+@[\w.\-]+\.\w+)")


def _pct(vals: list[float], q: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    return round(s[math.ceil(len(s) * q) - 1], 1)


def _get_nested(obj: dict[str, Any], dotted: str) -> Any:
    cur: Any = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _sync_phoenix_dataset(rows: list[dict[str, Any]]) -> str:
    """Upload evaluation dataset to local Arize Phoenix if reachable."""
    try:
        from phoenix.client import Client

        client = Client(base_url=os.getenv("PHOENIX_BASE_URL", "http://localhost:6006"))
        ds_name = "nammakural-e2e-golden"
        try:
            ds = client.datasets.get_dataset(dataset=ds_name)
            return f"dataset:{ds_name}(existing)"
        except Exception:
            client.datasets.create_dataset(
                name=ds_name,
                inputs=[{"id": r["id"], "utterance": r["utterance"], "lang": r["lang"]} for r in rows],
                outputs=[{"fsm_state": r["fsm_state"], "ward": r["ward"], "service_id": r["service_id"]} for r in rows],
                metadata=[{"score": r["score"], "latency_ms": r["latency_ms"]} for r in rows],
            )
            return f"dataset:{ds_name}(created)"
    except Exception as exc:
        return f"dataset:skipped({type(exc).__name__})"


def run_phoenix_eval(golden_path: Path) -> int:
    cases = [json.loads(ln) for ln in golden_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    metrics = {"fsm": 0, "ward": 0, "service": 0, "tts_purity": 0, "pii_safe": 0, "under_500ms": 0}
    latencies: list[float] = []
    dataset_rows: list[dict[str, Any]] = []
    full_pass = 0

    for idx, case in enumerate(cases, start=1):
        name = case.get("id") or f"case-{idx}"
        turns = case.get("turns") or []
        sid = f"phoenix-e2e-{idx}-{int(time.time())}" if case.get("use_session") else None
        res: dict[str, Any] = {}
        expected: dict[str, Any] = {}
        last_utterance = ""
        last_lang = "tanglish"
        t0 = time.monotonic()

        for t in turns:
            inp = t.get("input") or t
            expected = t.get("expect") or expected
            last_utterance = inp.get("utterance", "")
            last_lang = inp.get("lang", "tanglish")
            res = run_workflow_turn(
                utterance=last_utterance,
                combined_text=inp.get("combined_text", last_utterance),
                state_code=inp.get("state_code", case.get("state_code", "tn")),
                lang=last_lang,
                llm_mode=inp.get("llm_mode", "offline"),
                session_id=sid,
                dpdp_consented=inp.get("dpdp_consented", True),
                otp_verified=inp.get("otp_verified", False),
                assistant_speaking=inp.get("assistant_speaking", False),
            )
        elapsed_ms = round((time.monotonic() - t0) * 1000, 2)
        latencies.append(elapsed_ms)

        fsm_ok = not replay_case(case)
        ward_ok = "analysis.landmark.ward" not in expected or _get_nested(res, "analysis.landmark.ward") == expected["analysis.landmark.ward"]
        svc_ok = "analysis.service_id" not in expected or _get_nested(res, "analysis.service_id") == expected["analysis.service_id"]
        tts_txt = str(res.get("tts_text") or "")
        tts_ok = not re.search(r"[A-Za-z]", tts_txt)
        pii_ok = not _RAW_PII_RE.search(f"{res.get('display_text', '')} {tts_txt}")
        fast_ok = elapsed_ms <= 500.0

        metrics["fsm"] += int(fsm_ok)
        metrics["ward"] += int(ward_ok)
        metrics["service"] += int(svc_ok)
        metrics["tts_purity"] += int(tts_ok)
        metrics["pii_safe"] += int(pii_ok)
        metrics["under_500ms"] += int(fast_ok)

        case_ok = fsm_ok and ward_ok and svc_ok and tts_ok and pii_ok
        if case_ok:
            full_pass += 1

        score = round(sum([fsm_ok, ward_ok, svc_ok, tts_ok, pii_ok]) / 5.0, 2)
        ward_val = str(_get_nested(res, "analysis.landmark.ward") or "")
        svc_val = str(_get_nested(res, "analysis.service_id") or "")
        dataset_rows.append(
            {
                "id": name,
                "utterance": last_utterance,
                "lang": last_lang,
                "fsm_state": res.get("fsm_state", ""),
                "ward": ward_val,
                "service_id": svc_val,
                "score": score,
                "latency_ms": elapsed_ms,
            }
        )

        emit_otlp_span(
            name=f"eval.{name}",
            attributes={
                "openinference.span.kind": "EVALUATOR",
                "eval.case_id": name,
                "eval.score": score,
                "eval.passed": case_ok,
                "eval.fsm_ok": fsm_ok,
                "eval.ward_ok": ward_ok,
                "eval.service_ok": svc_ok,
                "eval.tts_purity_ok": tts_ok,
                "eval.pii_safe": pii_ok,
                "eval.fsm_state": res.get("fsm_state", ""),
                "eval.ward": ward_val,
                "eval.service_id": svc_val,
                "eval.latency_ms": elapsed_ms,
            },
            duration_ms=elapsed_ms,
            status_ok=case_ok,
        )

    total = len(cases)
    ds_status = _sync_phoenix_dataset(dataset_rows)
    ep = get_otlp_endpoint() or "disabled"
    print(
        f"Phoenix E2E Eval: {full_pass}/{total} passed | "
        f"FSM={metrics['fsm']}/{total} Ward={metrics['ward']}/{total} Service={metrics['service']}/{total} "
        f"TTS_Purity={metrics['tts_purity']}/{total} PII_Safe={metrics['pii_safe']}/{total} "
        f"Under500ms={metrics['under_500ms']}/{total} | "
        f"P50={_pct(latencies, 0.5)}ms P95={_pct(latencies, 0.95)}ms | {ds_status} | otlp={ep}"
    )
    return 0 if full_pass == total else 1


if __name__ == "__main__":
    golden = ROOT / "analytics" / "golden_cases.jsonl"
    raise SystemExit(run_phoenix_eval(golden))
