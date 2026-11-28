from uuid import uuid4

from fastapi.testclient import TestClient

from backend import agent_workflow, main
from backend.nlu import analyze_turn


def test_road_flooding_is_distinct_from_a_pipe_leak():
    assert analyze_turn("Navalur roads full-a தண்ணியா நிரம்பி இருக்கு")["service_id"] == "road_flooding"
    assert analyze_turn("Navalur water pipe burst and flooded the road")["service_id"] == "water_pipe"


def test_draft_carries_intent_location_and_route(monkeypatch):
    monkeypatch.setattr(main, "save_conversation_turn", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_workflow, "log_event", lambda *args, **kwargs: None)
    session = str(uuid4())
    client = TestClient(main.app)

    def turn(utterance, **kwargs):
        response = client.post("/api/workflow/turn", json={
            "session_id": session, "llm_mode": "offline", "utterance": utterance, **kwargs,
        })
        assert response.status_code == 200
        return response.json()

    assert turn("water pipe issue")["analysis"]["service_id"] == "water_pipe"
    repaired = turn("இது road-ல இருக்கிற issue தான்.")
    assert repaired["analysis"]["service_id"] == "road_flooding"
    turn("Navalur")
    draft = turn("Alpha City company")["grievance_draft"]
    assert draft["intent"] == "road_flooding"
    assert draft["location"]["area"] == "Navalur"
    assert draft["location"]["landmark"] == "Alpha City company"
    assert not draft["location"]["ward"]
    assert draft["destination"]["id"] == "cm_cell_1100"
    assert draft["status"] == "needs_location"
    rejected = turn("", gps_lat=13.0850, gps_lon=80.2101, gps_accuracy_m=15)
    assert not rejected["grievance_draft"]["location"]["ward"]
    resolved = turn("Actually, Tower Park")
    assert resolved["grievance_draft"]["destination"]["id"] == "gcc_pgrs"
    assert resolved["grievance_draft"]["status"] == "needs_confirmation"
    restored = client.get("/api/workflow/draft", params={"session_id": session})
    assert restored.headers["cache-control"] == "no-store"
    assert restored.json()["grievance_draft"] == resolved["grievance_draft"]
    client.post("/api/dpdp/consent", json={"session_id": session, "consented": False})
    assert client.get("/api/workflow/draft", params={"session_id": session}).json()["grievance_draft"] is None


def test_live_gps_distinguishes_coarse_and_supported_fixes(monkeypatch):
    monkeypatch.setattr(main, "save_conversation_turn", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_workflow, "log_event", lambda *args, **kwargs: None)
    session = str(uuid4())
    client = TestClient(main.app)
    payload = {"session_id": session, "llm_mode": "offline"}
    client.post("/api/workflow/turn", json={**payload, "utterance": "The road is flooded"})
    gps = {**payload, "utterance": "", "gps_lat": 13.0850, "gps_lon": 80.2101}
    coarse = client.post("/api/workflow/turn", json={**gps, "gps_accuracy_m": 800}).json()
    assert coarse["grievance_draft"]["status"] == "needs_location"
    verified = client.post("/api/workflow/turn", json={**gps, "gps_accuracy_m": 20}).json()
    assert verified["grievance_draft"]["location"]["source"] == "gps"
    assert verified["grievance_draft"]["location"]["ward"] == "Ward 103"


def test_generated_claim_of_filing_is_replaced(monkeypatch):
    monkeypatch.setattr(agent_workflow, "chat_backends", lambda mode: iter([{"provider": "sarvam-cloud"}]))
    monkeypatch.setattr(agent_workflow, "_generate_natural_reply", lambda **kwargs: (
        "இதை நான் register பண்றேன்.", "நம்ம team வந்து சரி பண்ணிடுவாங்க.", "mock",
    ))
    monkeypatch.setattr(agent_workflow, "log_event", lambda *args, **kwargs: None)
    text = "Navalur road is flooded"
    result = agent_workflow.run_workflow_turn(text, text, llm_mode="auto")
    assert result["fsm_state"] == "DISAMBIGUATE"
    assert "register" not in result["display_text"]
    assert "team" not in result["tts_text"]
    assert result["grievance_draft"]["submitted"] is False


def test_chennai_water_draft_collects_portal_duration(monkeypatch):
    monkeypatch.setattr(agent_workflow, "log_event", lambda *args, **kwargs: None)
    session = str(uuid4())
    first = agent_workflow.run_workflow_turn(
        "Tower Park water pipe burst", "", session_id=session,
    )
    draft = first["grievance_draft"]
    assert draft["destination"]["id"] == "cmwssb_gms"
    assert draft["status"] == "needs_details"
    assert "many days" in first["reply"]
    result = agent_workflow.run_workflow_turn("3 நாட்களாக", "", session_id=session)
    assert result["grievance_draft"]["duration_days"] == 3
    assert result["grievance_draft"]["status"] == "needs_confirmation"


def test_demo_review_is_bound_to_the_draft_and_does_not_authorize_filing(monkeypatch):
    monkeypatch.setattr(main, "save_conversation_turn", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_workflow, "log_event", lambda *args, **kwargs: None)
    client = TestClient(main.app)
    session = str(uuid4())
    draft = client.post("/api/workflow/turn", json={
        "session_id": session, "llm_mode": "offline", "utterance": "Tower Park road is flooded",
    }).json()["grievance_draft"]
    otp = client.post("/api/otp/send", json={"phone_masked": "demo"}).json()
    client.post("/api/otp/verify", json={"otp_session_id": otp["otp_session_id"], "code": otp["demo_otp_hint"]})
    body = {"session_id": session, "otp_session_id": otp["otp_session_id"], "mode": "voice_double",
            "spoken_phrase": "Confirm", "complaint_revision": str(draft["revision"]), "turn_id": str(uuid4()),
            "ward": draft["location"]["ward"], "service_id": draft["intent"], "urgency_tier": draft["urgency_tier"]}
    assert client.post("/api/hitl/seal", json={**body, "ward": "Ward 102"}).json()["approved"] is False
    assert client.post("/api/hitl/seal", json=body).json()["pending_confirmation"] is True
    assert client.post("/api/hitl/seal", json=body).json()["duplicate_turn"] is True
    review = client.post("/api/hitl/seal", json={**body, "turn_id": str(uuid4())}).json()
    assert review["approved"] is True
    assert review["handoff_authorized"] is False
    assert client.get("/api/workflow/draft", params={"session_id": session}).json()["grievance_draft"]["status"] == "needs_confirmation"
