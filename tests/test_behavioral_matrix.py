"""Regression checks for golden conversations and deterministic filing safeguards."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from analytics.analyze_logs import summarize
from analytics.eval_gate import load_cases, replay_case
from backend import state
from backend.main import app

GOLDEN_CASES = load_cases(Path(__file__).resolve().parents[1] / "analytics" / "golden_cases.jsonl")


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=lambda case: case["id"])
def test_golden_case(case, monkeypatch):
    monkeypatch.setattr("backend.agent_workflow.log_event", lambda *args, **kwargs: None)
    assert replay_case(case) == []


def test_cooldown_applies_to_filing_and_exempts_immediate_hazards():
    ward, service = "Ward 178", "sewage_pothole"
    assert not state.check_cooldown(ward, service, "STANDARD")["override_allowed"]
    assert state.check_cooldown(ward, service, "CRITICAL_SAFETY")["override_allowed"]
    assert state.check_cooldown(ward, service, "LIFE_SAFETY")["override_allowed"]
    result = state.verify_hitl_seal("modal_plus_voice", "உறுதி", True, True,
                                    ward, service, "STANDARD")
    assert not result["approved"]


def test_spoken_turn_is_bound_to_current_complaint_and_verified_otp(monkeypatch):
    monkeypatch.setattr(state, "_REQUEST_HISTORY", [])
    monkeypatch.setattr(state, "_OTP_SESSIONS", {})
    with TestClient(app) as client:
        issued = client.post("/api/otp/send", json={}).json()
        session = issued["otp_session_id"]

        def seal(phrase, ward="Ward 103", **options):
            payload = {"otp_session_id": session, "mode": "voice_double", "ward": ward,
                       "service_id": "streetlight_eb", "spoken_phrase": phrase, **options}
            return client.post("/api/hitl/seal", json=payload).json()

        assert not seal("Confirm", otp_verified=True)["approved"]
        client.post("/api/otp/verify", json={"otp_session_id": session, "code": issued["demo_otp_hint"]})
        assert not seal("Confirm, Confirm", distinct_turns=2)["approved"]
        assert seal("Confirm")["pending_confirmation"]
        assert seal("Confirm", "Ward 102", complaint_revision="old-draft")["pending_confirmation"]
        assert seal("Confirm", "Ward 102", complaint_revision="amended-draft")["pending_confirmation"]
        assert seal("உறுதி", "Ward 102", complaint_revision="amended-draft")["approved"]
        assert not seal("Confirm", "Ward 102", mode="modal_plus_voice", modal_ok=True)["approved"]
        assert not seal("", mode="modal_plus_voice", modal_ok=True)["approved"]
        assert not seal("உறுதி", mode="modal_plus_voice")["approved"]
        assert seal("உறுதி", mode="modal_plus_voice", modal_ok=True)["approved"]


def test_cloud_failure_falls_through_to_local_then_offline(monkeypatch):
    from backend import llm_bridge
    from backend.agent_workflow import run_workflow_turn

    backends = [
        {"provider": "cloud-api", "active_model": "cloud-demo"},
        {"provider": "ollama", "active_model": "gemma-4"},
    ]
    monkeypatch.setattr(llm_bridge, "cloud_llm", lambda: backends[0])
    monkeypatch.setattr(llm_bridge, "probe_local_llm", lambda: {**backends[1], "available": True})
    monkeypatch.setattr(llm_bridge, "_read_env_value", lambda name, default="": default)
    monkeypatch.setattr("backend.agent_workflow.log_event", lambda *args, **kwargs: None)
    attempted = []

    def request(backend, messages, **options):
        provider = backend["provider"]
        attempted.append(provider)
        if provider == "cloud-api":
            raise TimeoutError
        return {"content": "What near your street needs fixing?"}

    monkeypatch.setattr("backend.agent_workflow.chat_message", request)
    phrase = "konjam help pannunga"
    assert run_workflow_turn(phrase, phrase, llm_mode="auto")["model"] == "gemma-4"
    assert attempted == ["cloud-api", "ollama"]
    monkeypatch.setattr(llm_bridge, "probe_local_llm", lambda: {"available": False})
    assert run_workflow_turn(phrase, phrase, llm_mode="auto")["model"] == "deterministic-tanglish-v1"


def test_log_analytics_counts_records_without_echoing_identifiers(tmp_path, capsys):
    logs = tmp_path / "events.jsonl"
    convs = tmp_path / "turns.jsonl"
    logs.write_text("".join(json.dumps({
        "stage": "workflow.turn_complete",
        "message": "FSM=HITL_SEAL ward=Ward 103",
        "data": {"latency_ms": n},
    }) + "\n" for n in range(1, 21)), encoding="utf-8")
    safe_turn = {"role": "user", "fsm_state": "HITL_SEAL", "text": "[REDACTED_EMAIL]"}
    convs.write_text(json.dumps(safe_turn) + "\n", encoding="utf-8")
    assert summarize(logs, convs) == 0
    clean_output = capsys.readouterr().out
    assert "P50 10.00 ms" in clean_output
    assert "P95 19.00 ms" in clean_output
    assert "PII firewall: 0 PII leaks" in clean_output

    synthetic_email = "synthetic" + "@" + "example.invalid"
    with convs.open("a", encoding="utf-8") as output:
        output.write(json.dumps({"meta": {"email": synthetic_email}}) + "\n")
    assert summarize(logs, convs) == 1
    leak_output = capsys.readouterr().out
    assert "turns.jsonl:2" in leak_output
    assert synthetic_email not in leak_output

def test_cpu_image_routes_tamil_nadu_without_external_pack_files(monkeypatch):
    from backend.agent_workflow import run_workflow_turn
    from backend.state_packs import REGISTRY

    monkeypatch.setattr(REGISTRY, "_packs", {})
    monkeypatch.setattr("backend.agent_workflow.log_event", lambda *args, **kwargs: None)
    streetlight = "Anna Nagar Tower Park streetlight eriyala"
    result = run_workflow_turn(streetlight, streetlight)
    assert result["model"] == "deterministic-tanglish-v1"
    assert result["analysis"]["landmark"]["ward"] == "Ward 103"
    assert result["fsm_state"] == "HITL_SEAL"


def test_edge_tts_uses_tamil_voice_and_positive_rate(monkeypatch):
    import asyncio

    import edge_tts

    from backend.tts_service import synthesize_neural_mp3

    request = {}

    class Communicate:
        def __init__(self, text, voice, *, rate):
            request.update(text=text, voice=voice, rate=rate)

        async def stream(self):
            yield {"type": "audio", "data": b"synthetic-audio"}

    monkeypatch.setattr(edge_tts, "Communicate", Communicate)
    monkeypatch.setattr("backend.tts_service.log_event", lambda *args, **kwargs: None)
    phrase = "வார்டு 103 சரிபார்க்கப்பட்டது."
    result = asyncio.run(synthesize_neural_mp3(phrase, "en-IN-PrabhatNeural"))
    assert result["ok"]
    assert request == {"text": phrase, "voice": "ta-IN-ValluvarNeural", "rate": "+6%"}
