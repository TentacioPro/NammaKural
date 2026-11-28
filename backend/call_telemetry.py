"""Redacted call timelines for the browser voice workflow."""

from collections import defaultdict, OrderedDict
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import subprocess
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator
from typing import Literal


_IST = timezone(timedelta(hours=5, minutes=30))
_SHA = re.compile(r"[a-f0-9]{7,40}")


def _build_sha() -> str:
    configured = os.getenv("NK_BUILD_SHA") or os.getenv("VERCEL_GIT_COMMIT_SHA") or ""
    if _SHA.fullmatch(configured):
        return configured[:12]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"], cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=1, check=True,
        ).stdout.strip()
        return result if _SHA.fullmatch(result) else ""
    except (OSError, subprocess.SubprocessError):
        return ""


BUILD_SHA = _build_sha()


def _local_changes() -> bool:
    if not BUILD_SHA or os.getenv("NK_BUILD_SHA") or os.getenv("VERCEL_GIT_COMMIT_SHA"):
        return False
    try:
        result = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", "backend", "frontend/src", "state_packs"],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=1,
        )
        return result.returncode == 1
    except (OSError, subprocess.SubprocessError):
        return False


BUILD_HAS_LOCAL_CHANGES = _local_changes()
turn_context: ContextVar[tuple[str, str] | None] = ContextVar("turn_context", default=None)
router = APIRouter(prefix="/api/telemetry")


class BrowserMeasurement(BaseModel):
    kind: Literal["call.started", "call.ended", "call.playback", "call.upload"]
    call_id: UUID
    turn_id: UUID | None = None
    modality: Literal["voice", "text", "gps"] | None = None
    duration_ms: float | None = Field(default=None, ge=0, le=86_400_000)
    recorded_audio_ms: float | None = Field(default=None, ge=0, le=120_000)
    endpoint_wait_ms: float | None = Field(default=None, ge=0, le=60_000)
    browser_stt_ms: float | None = Field(default=None, ge=0, le=60_000)
    post_transcript_ms: float | None = Field(default=None, ge=0, le=60_000)
    speech_to_playback_ms: float | None = Field(default=None, ge=0, le=60_000)

    @model_validator(mode="after")
    def check_event(self):
        if self.kind == "call.playback" and (not self.turn_id or self.post_transcript_ms is None):
            raise ValueError("Playback requires a turn and a playback interval.")
        if self.kind == "call.upload" and (not self.turn_id or self.recorded_audio_ms is None):
            raise ValueError("Upload requires a turn and a recording interval.")
        if self.kind == "call.ended" and self.duration_ms is None:
            raise ValueError("Call end requires a duration.")
        if self.speech_to_playback_ms is not None and (
            self.modality != "voice" or self.post_transcript_ms is None
            or self.speech_to_playback_ms < self.post_transcript_ms
        ):
            raise ValueError("Speech-to-playback requires a valid voice measurement.")
        return self


@router.post("/browser", status_code=202)
def record_browser_measurement(event: BrowserMeasurement) -> dict:
    from backend.logger import log_event

    data = event.model_dump(exclude={"kind", "call_id", "turn_id"}, exclude_none=True)
    token = turn_context.set((str(event.call_id), str(event.turn_id) if event.turn_id else ""))
    try:
        log_event(event.kind, data=data, source="browser")
    finally:
        turn_context.reset(token)
    return {"accepted": True}


_NUMERIC_FIELDS = {
    "latency_ms", "duration_ms", "recorded_audio_ms", "endpoint_wait_ms", "browser_stt_ms",
    "post_transcript_ms", "speech_to_playback_ms", "prompt_tokens", "completion_tokens",
    "cached_tokens", "submitted_chars", "checks_remaining",
}
_WORKFLOW_FIELDS = {
    "draft_status": {"needs_location", "needs_details", "needs_confirmation", "cooldown"},
    "intent": {"road_flooding", "streetlight_eb", "sewage_pothole", "water_pipe", "ration_tnpds", "garbage_1100"},
    "destination": {"gcc_pgrs", "cmwssb_gms", "twad_punal", "tangedco_ccms", "cm_cell_1100", "tnpds"},
    "location_source": {"landmark", "gps"},
    "fsm_state": {"GREET", "TRIAGE", "DISAMBIGUATE", "HITL_SEAL", "LIFE_SAFETY", "DISPATCH"},
}
_STAGES = {
    "call.started", "call.ended", "call.playback", "call.upload",
    "stt.sarvam_saaras", "stt.sarvam_error",
    "llm.fast_turn", "llm.usage", "llm.fast_fallback",
    "workflow.turn_complete", "call.workflow", "tts.sarvam_stream_ttfb",
    "tts.sarvam_bulbul", "tts.neural_synth", "tts.cache_hit", "tts.sarvam_stream_error",
}


def _summary(samples: list[float]) -> dict:
    ordered = sorted(samples)
    return {
        "count": len(ordered),
        "p50": ordered[math.ceil(len(ordered) * .5) - 1] if ordered else None,
        "p95": ordered[math.ceil(len(ordered) * .95) - 1] if ordered else None,
    }


def read_call_history(path: Path, selected_call: str | None = None) -> dict:
    """Build history using logged measurement types and only allowlisted fields."""
    cohorts = defaultdict(list)
    calls: OrderedDict[str, dict] = OrderedDict()
    workflow_turns: set[tuple[str, str]] = set()
    played_turns: set[tuple[str, str]] = set()
    try:
        log = path.open(encoding="utf-8")
    except FileNotFoundError:
        return {"history": [], "calls": [], "selected_call": None}
    with log:
        for line in log:
            try:
                event = json.loads(line)
                timestamp = float(event["ts"])
                day = datetime.fromtimestamp(timestamp, _IST).date().isoformat()
            except (ValueError, TypeError, KeyError, OverflowError, OSError):
                continue
            data = event.get("data") or {}
            if not isinstance(data, dict):
                continue
            version = event.get("agent_version") or "Unversioned"
            build = event.get("build_sha") or ""
            if build and event.get("build_has_local_changes") is True:
                build += " + local changes"
            stage = event.get("stage")
            call_id = event.get("call_id")
            turn_id = event.get("turn_id")
            pair = (call_id, turn_id)
            if stage == "call.workflow" and call_id and turn_id:
                workflow_turns.add(pair)
            if stage == "client.ttfa":
                sample, metric = data.get("latency_ms"), "legacy_playback"
            elif stage == "call.playback":
                if pair not in workflow_turns or pair in played_turns:
                    continue
                played_turns.add(pair)
                sample = data.get("post_transcript_ms") if data.get("modality") == "voice" else None
                metric = "post_transcript"
                end_to_end = data.get("speech_to_playback_ms")
                if type(end_to_end) in (int, float) and math.isfinite(end_to_end):
                    cohorts[(day, version, build, "speech_to_playback")].append(end_to_end)
            else:
                sample, metric = None, ""
            if type(sample) in (int, float) and math.isfinite(sample):
                cohorts[(day, version, build, metric)].append(sample)

            if not call_id or stage not in _STAGES:
                continue
            if call_id not in calls:
                calls[call_id] = {"id": call_id, "first_ts": timestamp, "last_ts": timestamp,
                                  "version": version, "build": build, "duration_ms": None, "turns": {}}
            call = calls[call_id]
            call["last_ts"] = max(timestamp, call["last_ts"])
            if stage == "call.ended":
                call["duration_ms"] = data.get("duration_ms")
            if turn_id:
                turn = call["turns"].setdefault(turn_id, {"id": turn_id, "ts": timestamp, "events": []})
                safe_data = {key: value for key, value in data.items() if key in _NUMERIC_FIELDS
                             and type(value) in (int, float) and math.isfinite(value)}
                if isinstance(data.get("modality"), str) and data["modality"] in ("voice", "text", "gps"):
                    safe_data["modality"] = data["modality"]
                if stage == "llm.fast_turn" and re.fullmatch(r"[\w./:-]{1,100}", str(data.get("model") or ""), re.ASCII):
                    safe_data["model"] = data["model"]
                if stage == "call.workflow":
                    for key, allowed in _WORKFLOW_FIELDS.items():
                        value = data.get(key)
                        if isinstance(value, str) and value in allowed:
                            safe_data[key] = value
                    if "draft_status" in safe_data:
                        call["draft_status"] = safe_data["draft_status"]
                        if call["draft_status"] == "needs_confirmation" and "turns_to_review" not in call:
                            call["turns_to_review"] = len(call["turns"])
                if len(turn["events"]) < 32:
                    turn["events"].append({"stage": stage, "ts": timestamp, "data": safe_data})
            calls.move_to_end(call_id)
            if len(calls) > 26:
                oldest = next(iter(calls))
                if oldest == selected_call:
                    calls.move_to_end(oldest)
                    oldest = next(iter(calls))
                calls.pop(oldest)
    ordered = sorted(calls.values(), key=lambda call: call["last_ts"], reverse=True)
    selected = calls.get(selected_call) if selected_call else (ordered[0] if ordered else None)
    history = [
        {"day": day, "version": version, "build": build, "metric": metric, **_summary(samples)}
        for (day, version, build, metric), samples in sorted(cohorts.items(), reverse=True)[:90]
    ]
    statuses = [call["draft_status"] for call in ordered if "draft_status" in call]
    recent = {
        "calls_with_drafts": len(statuses),
        "ready_for_review": statuses.count("needs_confirmation"),
        "waiting_location": statuses.count("needs_location"),
        "waiting_details": statuses.count("needs_details"),
        "cooldown": statuses.count("cooldown"),
        "turns_to_review_p50": _summary([call["turns_to_review"] for call in ordered if "turns_to_review" in call])["p50"],
    }
    return {
        "history": history,
        "recent": recent,
        "calls": [{**{k: v for k, v in call.items() if k != "turns"}, "turn_count": len(call["turns"])}
                  for call in ordered],
        "selected_call": {**selected, "turns": list(selected["turns"].values())} if selected else None,
    }


@router.get("/runs")
def call_history(call_id: UUID | None = None) -> dict:
    from backend.logger import LOG_FILE

    return read_call_history(LOG_FILE, str(call_id) if call_id else None)
