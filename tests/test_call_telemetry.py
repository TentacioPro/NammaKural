from uuid import uuid4

from fastapi.testclient import TestClient

from backend import logger, main


def test_telemetry_correlates_and_deduplicates_browser_playback(monkeypatch, tmp_path):
    monkeypatch.setattr(logger, "LOG_FILE", tmp_path / "metrics.jsonl")
    monkeypatch.setattr(main, "save_conversation_turn", lambda *args, **kwargs: None)
    client = TestClient(main.app)
    call_id, turn_id = str(uuid4()), str(uuid4())
    headers = {"X-NK-Call-ID": call_id, "X-NK-Turn-ID": turn_id}
    logger.log_event("client.ttfa", "private historical details", {"latency_ms": 1300})
    response = client.post("/api/workflow/turn", json={
        "utterance": "Synthetic landmark road is flooded",
        "llm_mode": "offline", "input_mode": "voice",
    }, headers=headers)
    assert response.is_success
    async def audio(*args, **kwargs):
        logger.log_event("tts.sarvam_stream_ttfb", "private synthesis details",
                         {"latency_ms": 300, "submitted_chars": 38})
        yield b"synthetic audio"

    monkeypatch.setattr(main, "stream_neural_mp3", audio)
    reply = client.post("/api/tts/stream", json={"text": "synthetic"}, headers=headers)
    assert reply.is_success and reply.content == b"synthetic audio"

    playback = {"kind": "call.playback", "call_id": call_id, "turn_id": turn_id, "modality": "voice",
                "post_transcript_ms": 800, "speech_to_playback_ms": 1600}
    assert client.post("/api/telemetry/browser", json=playback).status_code == 202
    assert client.post("/api/telemetry/browser", json=playback).status_code == 202
    assert client.post("/api/telemetry/browser", json={**playback, "turn_id": str(uuid4())}).status_code == 202
    assert client.post("/api/telemetry/browser", json={**playback, "speech_to_playback_ms": 100}).status_code == 422
    assert client.post("/api/telemetry/browser", json={
        "kind": "call.ended", "call_id": call_id, "duration_ms": 7000,
    }).status_code == 202

    response = client.get("/api/telemetry/runs", params={"call_id": call_id})
    assert response.is_success
    data = response.json()
    assert data["selected_call"]["duration_ms"] == 7000
    turn, = data["selected_call"]["turns"]
    assert turn["id"] == turn_id
    stages = [event["stage"] for event in turn["events"]]
    assert "call.workflow" in stages
    assert "tts.sarvam_stream_ttfb" in stages
    assert stages.count("call.playback") == 1
    server_history = [entry for entry in data["history"] if entry["metric"] == "speech_to_playback"]
    assert len(server_history) == 1
    assert server_history[0]["count"] == 1 and server_history[0]["p50"] == 1600
    assert "private historical details" not in response.text
    assert "Synthetic landmark" not in response.text
    assert "private synthesis details" not in response.text
