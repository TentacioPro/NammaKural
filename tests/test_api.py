"""Automated pytest suite verifying zero-key startup, NLU, VAD, Cooldown, OTP, Dual-Confirm HITL, and PII redaction."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_boots_without_secret_keys(monkeypatch) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["voice_mode"] in ("offline-tanglish-engine", "live-neural", "local-unsloth-llm")
    assert body["portals_mapped"] == 6

    import backend.main as main_mod
    monkeypatch.setattr(main_mod, "probe_local_llm", lambda: {"available": False, "provider": "offline-tanglish-engine", "active_model": "deterministic-tanglish-v1", "models": []})
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    cold = client.get("/api/health").json()
    assert cold["voice_mode"] == "offline-tanglish-engine"


def test_critical_safety_spark_overrides_and_splits() -> None:
    res = client.post(
        "/api/turn",
        json={
            "combined_text": "Anna Nagar Tower Park back side 5th Avenue-la streetlight 5 naala eriyala, transformer wire spark aaguthu"
        },
    )
    assert res.status_code == 200
    data = res.json()["analysis"]
    assert data["has_place"] is True
    assert data["has_issue"] is True
    assert data["ambiguous_area"] is None
    assert data["landmark"]["ward"] == "Ward 103"
    assert data["urgency"]["tier"] == "CRITICAL_SAFETY"


def test_ambiguous_velachery_pauses_then_resolves_and_detects_cooldown() -> None:
    amb = client.post("/api/turn", json={"combined_text": "Velachery main road-la saakkadai overflow aaguthu"}).json()
    assert amb["analysis"]["ambiguous_area"] == "velachery"

    resolved = client.post(
        "/api/turn",
        json={"combined_text": "Velachery Vijayanagar Bus Stand main road-la saakkadai overflow aaguthu"},
    ).json()
    assert resolved["analysis"]["ambiguous_area"] is None
    assert resolved["analysis"]["landmark"]["ward"] == "Ward 178"
    assert resolved["cooldown"]["in_cooldown"] is True
    assert resolved["cooldown"]["override_allowed"] is False


def test_semantic_vad_ignores_backchannel_and_honors_stop() -> None:
    bc = client.post(
        "/api/turn",
        json={"combined_text": "seri ok", "assistant_speaking": True},
    ).json()
    assert bc["vad"]["action"] == "not_turn"

    stop = client.post(
        "/api/turn",
        json={"combined_text": "wait niruthunga change to Anna Arch", "assistant_speaking": True},
    ).json()
    assert stop["vad"]["action"] == "interrupt"


def test_otp_and_dual_confirm_hitl_gates() -> None:
    otp = client.post("/api/otp/send", json={"phone_masked": "+91 9840012345"}).json()
    assert otp["demo_otp_hint"] == "4829"
    sid = otp["otp_session_id"]

    # Blocked before OTP verified
    blocked = client.post(
        "/api/hitl/seal",
        json={
            "mode": "voice_double",
            "spoken_phrase": "confirm confirm",
            "modal_ok": False,
            "otp_verified": False,
            "ward": "Ward 103",
            "service_id": "streetlight_eb",
            "urgency_tier": "CRITICAL_SAFETY",
        },
    ).json()
    assert blocked["approved"] is False

    ver = client.post("/api/otp/verify", json={"otp_session_id": sid, "code": "4829"}).json()
    assert ver["verified"] is True

    # Voice double requires two confirmations (1 fails, 2 succeeds)
    one_hit = client.post(
        "/api/hitl/seal",
        json={
            "mode": "voice_double",
            "spoken_phrase": "உறுதி",
            "modal_ok": False,
            "otp_verified": True,
            "ward": "Ward 103",
            "service_id": "streetlight_eb",
            "urgency_tier": "CRITICAL_SAFETY",
        },
    ).json()
    assert one_hit["approved"] is False

    two_hits = client.post(
        "/api/hitl/seal",
        json={
            "mode": "voice_double",
            "spoken_phrase": "உறுதி, உறுதி",
            "modal_ok": False,
            "otp_verified": True,
            "ward": "Ward 103",
            "service_id": "streetlight_eb",
            "urgency_tier": "CRITICAL_SAFETY",
        },
    ).json()
    assert two_hits["approved"] is True
    assert two_hits["seal_method"] == "voice_double_affirmation"

    # Modal OK + single native Tamil confirmation succeeds
    modal_ok = client.post(
        "/api/hitl/seal",
        json={
            "mode": "modal_plus_voice",
            "spoken_phrase": "உறுதி",
            "modal_ok": True,
            "otp_verified": True,
            "ward": "Ward 102",
            "service_id": "streetlight_eb",
            "urgency_tier": "STANDARD",
        },
    ).json()
    assert modal_ok["approved"] is True


def test_greeting_and_mic_check_respond_naturally() -> None:
    hello = client.post("/api/turn", json={"combined_text": "hello ஹலோ", "latest_text": "ஹலோ"}).json()
    assert hello["phase"] == "chitchat"
    assert hello["chitchat"]["kind"] == "greeting_or_mic_check"

    mic = client.post(
        "/api/turn",
        json={"combined_text": "Ward 44 issue\nநான் பேசுறது கேக்குதா", "latest_text": "நான் பேசுறது கேக்குதா"},
    ).json()
    assert mic["phase"] == "chitchat"


def test_reverse_gps_and_telemetry_pii_redaction() -> None:
    geo = client.post("/api/location/reverse", json={"lat": 13.085, "lon": 80.21}).json()
    assert geo["landmark"]["ward"] == "Ward 103"

    tel = client.post(
        "/api/telemetry",
        json={
            "session_id": "test123",
            "phase": "hitl_review",
            "ward": "Ward 103",
            "note": "Citizen caller 9876543210 testuser@example.com corrected landmark",
        },
    ).json()
    note = tel["recorded"]["note"]
    assert "9876543210" not in note
    assert "testuser@example.com" not in note
    assert "[REDACTED_NUM]" in note
    assert "[REDACTED_EMAIL]" in note


def test_llm_bridge_offline_fallback_and_mocked_unsloth_turn(monkeypatch) -> None:
    import io
    import json
    from backend import llm_bridge

    offline = client.post(
        "/api/turn",
        json={"combined_text": "Anna Nagar Tower Park streetlight eriyala", "llm_mode": "offline"},
    ).json()
    assert offline["llm"]["used"] is False

    class _FakeResp(io.BytesIO):
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        llm_bridge,
        "probe_local_llm",
        lambda: {"available": True, "provider": "unsloth-studio", "active_model": "gemma-4-E2B-it-Q4_K_M", "models": ["gemma-4-E2B-it-Q4_K_M"]},
    )
    monkeypatch.setattr(llm_bridge, "_read_env_value", lambda name, default="": "demo-token" if name == "UNSLOTH_API_KEY" else "http://127.0.0.1:8888")

    fake_payload = json.dumps({
        "choices": [{
            "message": {
                "content": json.dumps({
                    "reply": "Purinjidhu! Anna Nagar Tower Park streetlight-ukku urgent report ready panren.",
                    "service_hint": "streetlight_eb",
                    "landmark_text": "Tower Park Vth Avenue",
                    "urgency_hint": "P2"
                })
            }
        }]
    }).encode("utf-8")
    monkeypatch.setattr(llm_bridge.urllib.request, "urlopen", lambda req, timeout=8.0: _FakeResp(fake_payload))

    res = client.post(
        "/api/turn",
        json={"combined_text": "light eriyala pakkathula", "latest_text": "light eriyala pakkathula", "llm_mode": "unsloth"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["llm"]["used"] is True
    assert body["llm"]["model"] == "gemma-4-E2B-it-Q4_K_M"
    assert body["analysis"]["landmark"]["ward"] == "Ward 103"
