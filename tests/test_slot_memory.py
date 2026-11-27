"""Regional speech and session memory through the production API entry point."""

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend import agent_workflow, main


@pytest.mark.parametrize("mode", ["offline", "unsloth", "auto"])
def test_transliterated_streetlight_survives_location_and_correction(monkeypatch, mode):
    monkeypatch.setattr(main, "save_conversation_turn", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_workflow, "log_event", lambda *args, **kwargs: None)
    prompts = []
    calls = []

    def fake_chat(backend, messages, **options):
        if "tools" not in options:
            prompts.append(messages[0]["content"])
            return {"content": "சரி, விவரத்தை குறிச்சுக்கிட்டேன்."}
        if messages[-1]["role"] == "tool":
            calls.append(json.loads(messages[-1]["content"]))
            return {"content": "What is your street issue?"}
        utterance = messages[-1]["content"]
        field, value = (
            ("landmark", "மெரினா மாலை ஆப்போசிட்ல") if "நாவலூர்" in utterance else
            ("landmark", "அண்ணா ஆர்ச்") if "ஆர்ச்" in utterance else
            ("note", "Two lamps are out") if "Two lamps" in utterance else
            ("issue", "ஸ்ட்ரீட் லைட் வந்து தெளிவா எரியல")
        )
        return {"role": "assistant", "tool_calls": [{"id": "extract", "type": "function",
                "function": {"name": "update_complaint_slot", "arguments": json.dumps({"field": field, "value": value})}}]}

    monkeypatch.setattr(agent_workflow, "chat_backends", lambda mode: iter([{"active_model": "gemma-4-mock"}]))
    monkeypatch.setattr(agent_workflow, "chat_message", fake_chat)
    client = TestClient(main.app)
    session = uuid4().hex

    def turn(text, session_id=session):
        response = client.post("/api/workflow/turn", json={
            "utterance": text, "combined_text": text, "session_id": session_id, "llm_mode": mode,
        })
        assert response.status_code == 200
        return response.json()

    first = turn("இல்ல இல்ல ஸ்ட்ரீட் லைட் வந்து தெளிவா எரியல")
    assert first["analysis"]["has_issue"] is True
    assert first["analysis"]["service_id"] == "streetlight_eb"
    second = turn("நான் வந்து சோழிங்கநல்லூர் தாண்டி நாவலூர்ல இருக்கேன், மெரினா மாலை ஆப்போசிட்ல")
    assert second["fsm_state"] == "DISAMBIGUATE"
    assert second["analysis"]["has_place"] and second["analysis"]["has_issue"]
    assert second["analysis"]["service_id"] == "streetlight_eb"
    assert second["analysis"]["area"] == "Navalur"
    assert "மெரினா மாலை" in second["analysis"]["landmark_text"]
    assert not second["analysis"]["landmark"]["ward"]
    assert "what is your street issue" not in second["reply"].lower()
    assert second["cooldown"] is None
    third = turn("இல்ல, அண்ணா ஆர்ச் பக்கத்துல")
    assert third["fsm_state"] == "HITL_SEAL"
    assert third["analysis"]["landmark"]["ward"] == "Ward 102"
    detail = turn("Two lamps are out")
    assert detail["analysis"]["landmark"]["ward"] == "Ward 102"
    assert not turn("Tower Park", uuid4().hex)["analysis"]["has_issue"]
    if mode != "offline":
        assert detail["slots"]["note"] == "Two lamps are out"
        assert turn("Still dark")["slots"]["note"] == "Two lamps are out"
        assert {call["updated"] for call in calls if "updated" in call} >= {"issue", "landmark", "note"}
        assert '"slots"' in prompts[1] and "streetlight_eb" in prompts[1] and "Navalur" in prompts[1]


def test_session_correction_replaces_issue_and_consent_withdrawal_clears_slots(monkeypatch):
    monkeypatch.setattr(main, "save_conversation_turn", lambda *args, **kwargs: None)
    client = TestClient(main.app)
    session = uuid4().hex

    def turn(text):
        return client.post("/api/workflow/turn", json={"utterance": text, "combined_text": text,
                           "session_id": session, "llm_mode": "offline"}).json()

    assert turn("Tower Park streetlight eriyala")["fsm_state"] == "HITL_SEAL"
    repair = turn("இல்ல, வாட்டர் பைப் உடைஞ்சிருக்கு")
    assert repair["analysis"]["service_id"] == "water_pipe"
    assert repair["analysis"]["landmark"]["ward"] == "Ward 103"
    client.post("/api/dpdp/consent", json={"session_id": session, "consented": False})
    assert turn("Tower Park")["blocked_reason"] == "dpdp_consent_withdrawn"
    client.post("/api/dpdp/consent", json={"session_id": session, "consented": True})
    assert not turn("Tower Park")["analysis"]["has_issue"]


def test_gps_must_match_fixture_before_unlocking_review():
    from backend.agent_workflow import run_workflow_turn

    phrase = "streetlight eriyala"
    outside = run_workflow_turn(phrase, phrase, gps_lat=12.84, gps_lon=80.23)
    assert outside["fsm_state"] == "DISAMBIGUATE"
    assert not outside["analysis"]["landmark"]["ward"]
    supported = run_workflow_turn(phrase, phrase, gps_lat=13.085, gps_lon=80.21)
    assert supported["fsm_state"] == "HITL_SEAL"
    assert supported["analysis"]["landmark"]["ward"] == "Ward 103"
    remote = "Navalur junction pakkam streetlight eriyala"
    remote = run_workflow_turn(remote, remote, gps_lat=13.085, gps_lon=80.21)
    assert remote["fsm_state"] == "DISAMBIGUATE"
    assert remote["analysis"]["area"] == "Navalur"
