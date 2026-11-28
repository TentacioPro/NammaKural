from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient

from backend import citizen_accounts, logger, main


def test_verified_citizens_get_private_history_and_channel_checklist(monkeypatch, tmp_path):
    monkeypatch.setenv("NK_AUTH_REQUIRED", "1")
    monkeypatch.setattr(citizen_accounts, "HISTORY_DB", tmp_path / "history.sqlite3")
    monkeypatch.setattr(logger, "LOG_FILE", tmp_path / "pipeline.jsonl")
    monkeypatch.setattr(main, "save_conversation_turn", lambda *args, **kwargs: None)
    monkeypatch.setattr(citizen_accounts, "provider_config", lambda: ("https://example.supabase.co", "synthetic"))

    accounts = {}

    async def provider(action, payload):
        if action == "otp":
            return {}
        citizen = accounts.setdefault(payload["phone"], str(uuid4()))
        return {"access_token": "synthetic", "user": {"id": citizen, "phone": payload["phone"][1:]}}

    monkeypatch.setattr(citizen_accounts, "_auth_post", provider)
    anonymous = TestClient(main.app)
    assert anonymous.get("/api/requests").status_code == 401
    assert anonymous.post("/api/workflow/turn", json={"utterance": "A public road is blocked"}).status_code == 401

    def signed_in(index):
        client = TestClient(main.app, client=(f"test-citizen-{index}", 10000))
        phone = "+91" + "6" + "0" * 8 + str(index)
        assert client.post("/api/auth/send", json={"phone": phone}).is_success
        verified = client.post("/api/auth/verify", json={"phone": phone, "code": "1" * 6})
        assert verified.is_success and "httponly" in verified.headers["set-cookie"].lower()
        return client, accounts[phone]

    alice, alice_id = signed_in(1)
    bob, _ = signed_in(2)
    assert alice.get("/api/telemetry/runs").status_code == 403
    monkeypatch.setenv("NK_OPERATOR_IDS", alice_id)
    assert alice.get("/api/telemetry/runs").is_success
    assert bob.post("/api/ops/evaluate").status_code == 403
    assert len(alice.get("/api/civic/channels").json()["channels"]) == 6
    session = str(uuid4())
    record = {"session_id": session, "llm_mode": "offline"}
    start = alice.post("/api/workflow/turn", json={**record, "utterance": "Tower Park road is flooded"}).json()
    assert start["grievance_draft"]["next_field"] == "impact"
    assert "passable" in start["display_text"]
    assert bob.get("/api/workflow/draft", params={"session_id": session}).json()["grievance_draft"] is None
    assert bob.post("/api/requests", json={"session_id": session}).status_code == 404

    result = alice.post("/api/workflow/turn", json={**record, "utterance": "The road is blocked"}).json()
    draft = result["grievance_draft"]
    assert draft["status"] == "needs_confirmation"
    assert draft["impact"] == "The road is blocked"
    form = {"session_id": session, "turn_id": str(uuid4()), "ward": draft["location"]["ward"],
            "service_id": draft["intent"], "urgency_tier": draft["urgency_tier"], "complaint_revision": str(draft["revision"]),
            "spoken_phrase": "Confirm", "modal_ok": True}
    assert alice.post("/api/hitl/seal", json=form).json()["approved"] is False
    monkeypatch.setattr(main, "_read_env_value", lambda name, default="": "synthetic" if name == "SARVAM_API_KEY" else default)
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: BytesIO(b'{"transcript":"Confirm"}'))
    speech = alice.post("/api/stt", files={"audio": ("voice.webm", b"synthetic-audio", "audio/webm")},
                        headers={"X-NK-Call-ID": str(uuid4()), "X-NK-Turn-ID": form["turn_id"]})
    assert speech.json()["provider"] == "sarvam-saaras"
    assert alice.post("/api/hitl/seal", json=form).json()["handoff_authorized"] is True
    assert alice.post("/api/hitl/seal", json=form).json()["approved"] is False
    assert alice.post("/api/requests", json={"session_id": session}).is_success
    assert alice.post("/api/requests", json={"session_id": session}).is_success
    history = alice.get("/api/requests").json()
    assert history["saved"] == 1 and history["reported_filed"] == 0
    draft_id = history["items"][0]["id"]
    assert bob.post(f"/api/requests/{draft_id}/filing-reference", json={"reference": "TEST-ABC"}).status_code == 404
    assert alice.post(f"/api/requests/{draft_id}/filing-reference", json={"reference": "TEST-ABC"}).json()["status"] == "reported_by_citizen"
    assert alice.get("/api/requests").json()["reported_filed"] == 1
    assert bob.get("/api/requests").json()["saved"] == 0
    assert alice.post("/api/auth/signout").is_success
    assert alice.get("/api/requests").status_code == 401
