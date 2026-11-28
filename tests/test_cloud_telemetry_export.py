import json

from ops.export_cloud_telemetry import export, safe_event


def test_only_numeric_and_allowlisted_metadata_leave_the_raw_log(tmp_path):
    raw = {"stage": "workflow.turn_complete", "message": "FSM=HITL_SEAL ward=private landmark",
           "data": {"latency_ms": 23, "model": "private provider", "text": "private utterance",
                    "ward": "private landmark", "bytes": 8 * 10**9},
           "call_id": "private call", "turn_id": "private turn", "ts": 1_795_000_000}
    result = safe_event(raw, {}, {})
    assert result["data"] == {"latency_ms": 23, "fsm_state": "HITL_SEAL"}
    assert "private" not in json.dumps(result)
    assert (result["call_id"], result["turn_id"]) == ("call-0001", "turn-0001")
    path = tmp_path / "input.jsonl"
    path.write_text("\n".join(json.dumps(item) for item in [raw, {**raw, "stage": "private stage"}]), encoding="utf-8")
    output = tmp_path / "output.jsonl"
    assert export(path, output) == 2
    events = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert events[0]["turn_id"] == events[1]["turn_id"]
    assert events[1]["stage"] == "unclassified"
