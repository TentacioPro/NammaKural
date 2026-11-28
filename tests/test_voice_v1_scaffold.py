from fastapi.testclient import TestClient

from backend.voice_v1.app import app
from backend.voice_v1.contracts import AudioFrame, Reply, Transcript
from backend.voice_v1.observability import async_stage_timer
from backend.voice_v1.turn_policy import (
    SessionState,
    SlotKind,
    SpeakerCadence,
    TurnCoordinator,
    classify_backchannel,
    endpoint_window_ms,
    is_explicit_stop,
    should_emit_listening_cue,
)

client = TestClient(app)


def test_health_and_provider_readiness_are_explicit():
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    providers = client.get("/v1/providers").json()
    assert providers["production_audio_ready"] is False
    assert providers["asr"]["required"] == "streaming partial/final transcript adapter"


def test_text_turn_has_traceable_ids_and_does_not_claim_voice_ttfa():
    response = client.post(
        "/v1/test/turn",
        headers={"x-request-id": "test-request-1"},
        json={"utterance": "Anna Nagar-la streetlight eriyala", "session_id": "test-session-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert response.headers["x-request-id"] == "test-request-1"
    assert body["request_id"] == "test-request-1"
    assert body["session_id"] == "test-session-1"
    assert body["turn_id"]
    assert body["input_mode"] == "injected_text"
    assert body["voice_ttfa_ms"] is None
    assert "excludes microphone" in body["voice_ttfa_note"]
    assert body["workflow_ms"] >= 0
    assert "result" in body


def test_playback_ack_uses_one_client_clock_and_records_metric():
    response = client.post(
        "/v1/telemetry/playback",
        json={
            "turn_id": "turn-123",
            "event": "playback_started",
            "clock_origin": "browser-performance.now",
            "end_of_speech_ms": 1000,
            "playback_started_ms": 1450,
        },
    )
    assert response.status_code == 200
    assert response.json()["client_end_of_speech_to_playback_ms"] == 450
    assert "nk_voice_end_of_speech_to_first_audio_seconds_count 1.0" in client.get("/metrics").text


def test_playback_ack_rejects_negative_duration():
    response = client.post(
        "/v1/telemetry/playback",
        json={
            "turn_id": "turn-124",
            "event": "playback_started",
            "clock_origin": "native-monotonic",
            "end_of_speech_ms": 1500,
            "playback_started_ms": 1400,
        },
    )
    assert response.status_code == 422


def test_playback_ack_rejects_duration_over_60_seconds():
    response = client.post(
        "/v1/telemetry/playback",
        json={
            "turn_id": "turn-125",
            "event": "playback_started",
            "clock_origin": "browser-performance.now",
            "end_of_speech_ms": 1000,
            "playback_started_ms": 61001,
        },
    )
    assert response.status_code == 422
    assert "60000 ms" in response.json()["detail"]


def test_404_metrics_use_unmatched_template_not_raw_url():
    missing_path = "/not-found/turn/unique-user-value"
    response = client.get(missing_path)
    assert response.status_code == 404
    metrics = client.get("/metrics").text
    assert 'route="unmatched",status="404"' in metrics
    assert missing_path not in metrics


def test_contracts_preserve_frame_and_transcript_timing_fields():
    frame = AudioFrame(b"pcm", 16000, 1, "s16le", "pcm", 1234, 0)
    transcript = Transcript("வணக்கம்", True, 0.9, "ta-IN", 1234, 5678, 6000)
    reply = Reply("Display", "Tamil speech", voice="ta-IN-Pallavi", speaking_rate=0.75)
    assert frame.sample_rate_hz == 16000
    assert transcript.emitted_monotonic_ns >= transcript.speech_end_monotonic_ns
    assert reply.display_text != reply.tts_text
    assert reply.speaking_rate == 0.75


def test_async_stage_timer_is_usable():
    import asyncio

    async def run():
        async with async_stage_timer("test_async", "fixture"):
            await asyncio.sleep(0)

    asyncio.run(run())


def test_endpointing_is_slot_aware_and_confidence_bounded():
    assert endpoint_window_ms(SlotKind.YES_NO) == (150, 250)
    assert endpoint_window_ms(SlotKind.ADDRESS) == (800, 1200)
    assert endpoint_window_ms(SlotKind.ADDRESS, confidence=0.4) == (800, 1400)


def test_backchannel_context_and_interrupt_epoch_policy():
    assert classify_backchannel("seri", context="clarification", confidence=0.9)
    assert not classify_backchannel("seri", context="confirmation", confidence=0.9)
    assert not classify_backchannel("mm", context="clarification", confidence=0.3)

    turn = TurnCoordinator()
    turn.start_generation()
    old_epoch = turn.start_speaking()
    assert turn.pause_for_possible_barge_in() == old_epoch
    assert turn.state == SessionState.PAUSED
    assert turn.resolve_incoming_speech(is_backchannel=True) == old_epoch
    assert turn.state == SessionState.SPEAKING
    turn.pause_for_possible_barge_in()
    new_epoch = turn.resolve_incoming_speech(is_backchannel=False)
    assert new_epoch == old_epoch + 1
    assert not turn.is_current_epoch(old_epoch)


def test_cadence_stop_cue_listening_cue_and_protected_states():
    cadence = SpeakerCadence()
    cadence.observe_pause(1100)
    assert cadence.adjust_window(SlotKind.ADDRESS)[1] > endpoint_window_ms(SlotKind.ADDRESS)[1]
    assert is_explicit_stop("நிறுத்துங்கள்!")
    assert not is_explicit_stop("different street")
    assert should_emit_listening_cue(continuous_speech_seconds=6, pause_ms=250, already_emitted=False)
    assert not should_emit_listening_cue(continuous_speech_seconds=4, pause_ms=250, already_emitted=False)

    turn = TurnCoordinator()
    tool_epoch = turn.start_tool()
    assert turn.resolve_incoming_speech(is_backchannel=False) == tool_epoch
    assert turn.state == SessionState.TOOL_PENDING
    assert turn.complete_tool(tool_epoch)
    handoff_epoch = turn.epoch
    turn.begin_handoff()
    assert turn.resolve_incoming_speech(is_backchannel=False) == handoff_epoch + 1
    assert turn.state == SessionState.HUMAN_HANDOFF


def test_metrics_endpoint_exposes_request_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "nk_voice_requests_total" in response.text
    assert "nk_voice_stage_duration_seconds" in response.text
