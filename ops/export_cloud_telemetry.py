"""Export numeric telemetry and allowlisted workflow data for repository handoffs."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import re


STAGES = frozenset("""
call.started call.ended call.upload call.playback call.workflow client.ttfa
guardrail.aadhaar_blocked llm.fast_fallback llm.fast_turn llm.request llm.response llm.usage
stt.clip_received stt.error stt.final stt.noise_filtered stt.sarvam_error stt.sarvam_saaras
stt.speech_start stt.start tts.barge_in tts.cache_hit tts.fallback_browser tts.neural_synth
tts.sarvam_bulbul tts.sarvam_bulbul_error tts.sarvam_stream_error tts.sarvam_stream_ttfb
tts.speak vad.ignored webrtc.offer workflow.chitchat workflow.turn workflow.turn_complete
""".split())
NUMBER_FIELDS = frozenset("""
browser_stt_ms bytes cached_tokens chunks completion_tokens confidence duration_ms endpoint_wait_ms
latency_ms post_transcript_ms prompt_tokens recorded_audio_ms sdp_bytes size_kb speech_to_playback_ms
submitted_chars checks_remaining
""".split())
BOOLEAN_FIELDS = {"cached", "parsed_json", "pii_masked", "streamed"}
VOCABULARIES = {
    "fsm_state": {"GREET", "TRIAGE", "DISAMBIGUATE", "COOLDOWN_AND_OTP", "HITL_SEAL", "LIFE_SAFETY", "DISPATCH"},
    "state_code": {"tn", "ka", "in_central"},
    "modality": {"voice", "text", "gps"},
    "lang": {"ta", "en", "ta-IN", "en-IN", "tanglish"},
    "mode": {"offline", "auto", "unsloth", "cloud", "cloud_api", "local_gpu", "offline_fsm"},
    "model": {"deterministic-tanglish-v1", "sarvam-105b-conversations", "gemma-4-E2B-it-Q4_K_M"},
    "intent": {"road_flooding", "streetlight_eb", "sewage_pothole", "water_pipe", "ration_tnpds", "garbage_1100"},
    "destination": {"gcc_pgrs", "cmwssb_gms", "twad_punal", "tangedco_ccms", "cm_cell_1100", "tnpds"},
    "draft_status": {"needs_location", "needs_details", "needs_confirmation", "cooldown"},
    "location_source": {"landmark", "gps"},
}
AGENT_VERSIONS = {"0.2.0-legacy", "0.3.0-langgraph-livekit"}
SCHEMA_VERSIONS = {"2026-11-27.v1"}


def safe_event(raw: dict, call_ids: dict, turn_ids: dict) -> dict:
    supplied = raw.get("data")
    supplied = supplied if isinstance(supplied, dict) else {}
    data = {
        key: value for key, value in supplied.items()
        if (key in NUMBER_FIELDS and type(value) in (int, float) and 0 <= value <= 100_000_000)
        or (key in BOOLEAN_FIELDS and isinstance(value, bool))
        or (key in VOCABULARIES and isinstance(value, str) and value in VOCABULARIES[key])
    }
    if "fsm_state" not in data and raw.get("stage") == "workflow.turn_complete":
        state = re.match(r"^FSM=([A-Z_]+)\b", str(raw.get("message", "")))
        if state and state[1] in VOCABULARIES["fsm_state"]:
            data["fsm_state"] = state[1]
    version = raw.get("agent_version")
    schema = raw.get("schema_version")
    event = {
        "stage": raw["stage"] if raw.get("stage") in STAGES else "unclassified",
        "agent_version": version if version in AGENT_VERSIONS else "unversioned",
        "schema_version": schema if schema in SCHEMA_VERSIONS else "unversioned",
        "data": data,
    }
    if type(ts := raw.get("ts")) in (int, float) and math.isfinite(ts):
        event["ts"] = ts
    if raw.get("level") in {"ERROR", "WARN", "INFO", "DEBUG"}:
        event["level"] = raw["level"]
    if raw.get("source") in {"backend", "browser"}:
        event["source"] = raw["source"]
    if isinstance(sha := raw.get("build_sha"), str) and re.fullmatch(r"[a-f0-9]{7,40}", sha):
        event["build_sha"] = sha
    if isinstance(call := raw.get("call_id"), str) and call:
        event["call_id"] = call_ids.setdefault(call, f"call-{len(call_ids) + 1:04d}")
        if isinstance(turn := raw.get("turn_id"), str) and turn:
            event["turn_id"] = turn_ids.setdefault((call, turn), f"turn-{len(turn_ids) + 1:04d}")
    return event


def export(source: Path, destination: Path) -> int:
    events = []
    call_ids: dict = {}
    turn_ids: dict = {}
    for line in source.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(safe_event(json.loads(line), call_ids, turn_ids))
    if source.resolve() == destination.resolve():
        raise ValueError("The export destination must differ from the raw log.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in events),
                           encoding="utf-8")
    return len(events)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    count = export(args.input, args.output)
    print(f"Exported {count} records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
