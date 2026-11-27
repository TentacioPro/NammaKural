"""Golden Voice Agent behavioral, Pan-Bharat state-pack, PII/Aadhaar firewall, and guardrail eval suite."""

from __future__ import annotations

import io
import json

from fastapi.testclient import TestClient

from backend import llm_bridge
from backend.agent_workflow import execute_tool, post_guardrail_reply, run_workflow_turn
from backend.main import app
from backend.state import is_valid_verhoeff_aadhaar, scrub_pii_and_aadhaar
from backend.state_packs import REGISTRY

client = TestClient(app)


def test_pluggable_bharat_state_packs_load_and_resolve() -> None:
    packs = REGISTRY.list_summaries()
    codes = {p["state_code"] for p in packs}
    assert {"tn", "ka", "in_central"}.issubset(codes)

    ka_res = run_workflow_turn(
        utterance="Indiranagar 100 feet BESCOM streetlight current illa",
        combined_text="Indiranagar 100 feet BESCOM streetlight current illa",
        state_code="ka",
        llm_mode="offline",
    )
    assert ka_res["state_code"] == "ka"
    assert ka_res["fsm_state"] == "HITL_SEAL"
    assert ka_res["analysis"]["landmark"]["ward"] == "Ward 80"


def test_aadhaar_verhoeff_and_pre_llm_pii_firewall() -> None:
    # Verhoeff validation: 23456789012 -> check exact checksum vs flipped digit
    valid_sample = next(f"23456789012{d}" for d in range(10) if is_valid_verhoeff_aadhaar(f"23456789012{d}"))
    assert is_valid_verhoeff_aadhaar(valid_sample) is True
    flipped = valid_sample[:-1] + str((int(valid_sample[-1]) + 1) % 10)
    assert is_valid_verhoeff_aadhaar(flipped) is False
    assert is_valid_verhoeff_aadhaar("012345678901") is False

    scrub = scrub_pii_and_aadhaar("My aadhaar is 9988 7766 5544 and phone +91 9840012345")
    assert scrub["aadhaar_blocked"] is True
    assert "9988" not in scrub["clean_text"]
    assert "9840012345" not in scrub["clean_text"]
    assert "[AADHAAR_BLOCKED]" in scrub["clean_text"]

    # Workflow blocks Aadhaar immediately BEFORE reaching LLM
    wf = run_workflow_turn(
        utterance="Anna Nagar Aadhaar 4567 8901 2345 verify pannunga",
        combined_text="Anna Nagar Aadhaar 4567 8901 2345 verify pannunga",
        state_code="tn",
        llm_mode="offline",
    )
    assert wf["aadhaar_blocked"] is True
    assert "Mobile OTP" in wf["reply"]


def test_multi_turn_landmark_repair_and_guardrail_refusal() -> None:
    # Turn 1: Ambiguous Velachery pauses in DISAMBIGUATE
    t1 = run_workflow_turn(
        utterance="Velachery streetlight eriyala",
        combined_text="Velachery streetlight eriyala",
        state_code="tn",
    )
    assert t1["fsm_state"] == "DISAMBIGUATE"

    # Turn 2: Citizen repairs landmark ("illa Anna Arch IIIrd Ave")
    t2 = run_workflow_turn(
        utterance="illa Anna Arch IIIrd Ave",
        combined_text="Velachery streetlight eriyala illa Anna Arch IIIrd Ave",
        state_code="tn",
    )
    assert t2["analysis"]["landmark"]["ward"] == "Ward 102"
    assert any(step["tool"] == "update_complaint_slot" for step in t2["tool_trace"])

    # Code > LLM guardrail refuses dispatch when DPDP consent withdrawn or OTP missing
    withdrawn = run_workflow_turn(
        utterance="Anna Nagar streetlight eriyala",
        combined_text="Anna Nagar streetlight eriyala",
        dpdp_consented=False,
    )
    assert withdrawn["blocked_reason"] == "dpdp_consent_withdrawn"

    sealed_without_otp = execute_tool(
        "seal_complaint",
        {"mode": "voice_double", "spoken_phrase": "confirm confirm", "otp_verified": False, "ward": "Ward 102", "service_id": "streetlight_eb"},
        {"otp_verified": False, "dpdp_consented": True},
    )
    assert sealed_without_otp["approved"] is False

    # Post-LLM hallucinated Ward scrubber
    grounded = post_guardrail_reply("**Filed** for Ward 999 near Anna Arch.", {"Ward 102"})
    assert "Ward 999" not in grounded
    assert "your verified Ward" in grounded
    assert "*" not in grounded


def test_llm_tool_calling_loop_and_webrtc_coturn_endpoints(monkeypatch) -> None:
    class _FakeResp(io.BytesIO):
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    call_count = {"n": 0}

    def fake_urlopen(req, timeout=8.0):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _FakeResp(json.dumps({
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [{
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "lookup_landmark_and_ward",
                                "arguments": json.dumps({"query": "Anna Nagar Tower Park streetlight", "state_code": "tn"}),
                            },
                        }],
                    }
                }]
            }).encode("utf-8"))
        return _FakeResp(json.dumps({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Resolved Ward 103 Tower Park. Verify OTP and say Confirm twice.",
                }
            }]
        }).encode("utf-8"))

    monkeypatch.setattr("backend.agent_workflow.probe_local_llm", lambda: {"available": True, "provider": "unsloth-studio", "active_model": "gemma-4-E2B-it-Q4_K_M", "models": ["gemma-4-E2B-it-Q4_K_M"]})
    monkeypatch.setattr("backend.agent_workflow._read_env_value", lambda name, default="": "demo-key" if name == "UNSLOTH_API_KEY" else "http://127.0.0.1:8888")
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    wf = client.post(
        "/api/workflow/turn",
        json={"utterance": "Anna Nagar Tower Park streetlight", "combined_text": "Anna Nagar Tower Park streetlight", "llm_mode": "unsloth"},
    ).json()
    assert wf["fsm_state"] == "HITL_SEAL"
    assert wf["tool_trace"][0]["tool"] == "lookup_landmark_and_ward"
    assert "Ward 103" in wf["reply"]

    rtc_cfg = client.get("/api/rtc/config").json()
    assert len(rtc_cfg["iceServers"]) >= 2
    assert any("turn:" in u for s in rtc_cfg["iceServers"] for u in ([s["urls"]] if isinstance(s["urls"], str) else s["urls"]))

    offer = client.post("/api/rtc/offer", json={"sdp": "v=0...", "type": "offer"}).json()
    assert offer["status"] == "signaling_ready"

    packs = client.get("/api/state-packs").json()
    assert packs["count"] >= 3

    cl = client.post("/api/client-log", json={"stage": "stt.final", "message": "Phone 9876543210 test", "level": "INFO"}).json()
    assert cl["logged"] is True
    assert "[REDACTED_NUM]" in cl["entry"]["message"]
    logs_res = client.get("/api/logs?limit=20").json()
    assert logs_res["count"] >= 1
