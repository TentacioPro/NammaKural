"""Tests for Round 2 Sarvam/Vercel/Redis/GCC Pre-Submit voice architecture modules."""

from fastapi.testclient import TestClient

from backend.main import app
from backend.nlu import validate_phone_digits
from backend.portal_bridge import build_gcc_preview_packet
from backend.sarvam_realtime import get_dynamic_keyterms
from backend.session_store import SessionStore, sign_session_token, verify_session_token

client = TestClient(app)


def test_session_store_ttl_and_hmac_tokens() -> None:
    store = SessionStore()
    store.set_json("test:key", {"ward": "Ward 103", "complaint_version": 2}, ttl_sec=60)
    loaded = store.get_json("test:key")
    assert loaded == {"ward": "Ward 103", "complaint_version": 2}
    assert store.consume_once("turn:123", ttl_sec=60) is True
    assert store.consume_once("turn:123", ttl_sec=60) is False

    token = sign_session_token({"session_id": "sess-42", "state_code": "tn"})
    assert verify_session_token(token) == {"session_id": "sess-42", "state_code": "tn"}
    assert verify_session_token(token + "tampered") is None


def test_validate_phone_digits_partial_and_complete() -> None:
    partial = validate_phone_digits("98401 234")
    assert partial["complete"] is False
    assert partial["digits_count"] == 8

    valid = validate_phone_digits("+91 98401 23456")
    assert valid["complete"] is True
    assert valid["valid"] is True
    assert valid["masked"] == "+91 98XXXXXX56"


def test_dynamic_keyterms_locality_and_stage() -> None:
    terms = get_dynamic_keyterms("tn", "Anna Nagar")
    assert len(terms) > 0
    assert "streetlight" in terms
    assert "urudhi" in terms


def test_gcc_preview_packet_never_submits_to_gov() -> None:
    incomplete = build_gcc_preview_packet(
        service_id="streetlight_eb",
        landmark={"name": "Navalur Marina Mall opposite", "ward": "", "zone": ""},
        summary_text="Navalur Marina Mall opposite-la streetlight eriyala",
        urgency_tier="STANDARD",
        complaint_version=1,
        otp_verified=False,
        hitl_approved=False,
    )
    assert incomplete["outbound_gov_requests"] is False
    assert incomplete["preview_id"].startswith("NK-PREVIEW-")
    assert incomplete["ready_for_portal"] is False
    assert "ward_verification" in incomplete["missing_fields"]
    assert "mobile_otp" in incomplete["missing_fields"]
    assert "dual_confirm_hitl" in incomplete["missing_fields"]

    ready = build_gcc_preview_packet(
        service_id="streetlight_eb",
        landmark={"name": "Anna Arch pakkam", "ward": "Ward 102", "zone": "Zone VIII - Anna Nagar"},
        summary_text="Anna Nagar Anna Arch pakkam streetlight not working",
        urgency_tier="HIGH",
        complaint_version=3,
        otp_verified=True,
        hitl_approved=True,
    )
    assert ready["outbound_gov_requests"] is False
    assert ready["ready_for_portal"] is True
    assert ready["missing_fields"] == []
    assert ready["complaint_version"] == 3


def test_portal_preview_debug_and_telemetry_endpoints() -> None:
    health = client.get("/api/health").json()
    assert health["status"] == "ok"
    assert "store_backend" in health
    assert "vercel_region" in health

    preview = client.post(
        "/api/portal/preview",
        json={
            "service_id": "streetlight_eb",
            "landmark": {"name": "Anna Arch pakkam", "ward": "Ward 102", "zone": "Zone VIII"},
            "summary_text": "Streetlight out near Anna Arch",
            "urgency_tier": "STANDARD",
            "complaint_version": 2,
            "otp_verified": True,
            "hitl_approved": True,
        },
    )
    assert preview.status_code == 200
    assert preview.json()["outbound_gov_requests"] is False
    assert preview.json()["ready_for_portal"] is True

    dbg = client.get("/api/debug/session?session_id=browser&state_code=tn")
    assert dbg.status_code == 200
    assert dbg.json()["session_id"] == "browser"
    assert isinstance(dbg.json()["dynamic_keyterms"], list)

    tel = client.get("/api/telemetry/summary")
    assert tel.status_code == 200
    assert "ttfa" in tel.json()
