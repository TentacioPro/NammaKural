"""FastAPI entrypoint serving NammaKural Pure Voice Agent & zero-key civic triage APIs."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.nlu import (
    SERVICE_CATALOG,
    analyze_turn,
    classify_conversational_chitchat,
    classify_semantic_vad,
    resolve_gps_to_landmark,
)
from backend.state import (
    check_cooldown,
    issue_mobile_otp,
    list_request_history,
    list_telemetry_spans,
    record_telemetry_span,
    verify_hitl_seal,
    verify_mobile_otp,
)

ROOT_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="NammaKural (நம்ம குரல்) — Civic Voice Agent API",
    version="0.2.0",
    description="Zero-key offline-ready Tamil/Tanglish Voice Agent, GIS resolver, Cooldown & HITL router.",
)

app.mount("/assets", StaticFiles(directory=str(ROOT_DIR / "assets")), name="assets")


class TurnRequest(BaseModel):
    combined_text: str
    latest_text: str | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    assistant_speaking: bool = False


class ReverseGeoRequest(BaseModel):
    lat: float
    lon: float


class OtpSendRequest(BaseModel):
    phone_masked: str = "+91 98XXXXXX10"


class OtpVerifyRequest(BaseModel):
    otp_session_id: str
    code: str


class HitlSealRequest(BaseModel):
    mode: str = "modal_plus_voice"
    spoken_phrase: str = ""
    modal_ok: bool = False
    otp_verified: bool = False
    ward: str
    service_id: str
    urgency_tier: str = "STANDARD"


class TelemetryRequest(BaseModel):
    session_id: str = "local"
    phase: str
    urgency_tier: str = "STANDARD"
    ward: str = ""
    hitl_edited: bool = False
    note: str = ""


@app.get("/")
def serve_home() -> FileResponse:
    """Serve the primary pure light Voice Agent canvas."""
    return FileResponse(str(ROOT_DIR / "index.html"))


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    """Confirm app boots cleanly without required external secret keys."""
    sarvam_ready = bool(os.getenv("SARVAM_API_KEY", "").strip())
    gemini_ready = bool(os.getenv("GEMINI_API_KEY", "").strip())
    return {
        "status": "ok",
        "voice_mode": "live-neural" if (sarvam_ready or gemini_ready) else "offline-tanglish-engine",
        "optional_keys": {
            "SARVAM_API_KEY": "configured" if sarvam_ready else "key not set (offline Tanglish active)",
            "GEMINI_API_KEY": "configured" if gemini_ready else "key not set (offline Tanglish active)",
        },
        "portals_mapped": 6,
    }


@app.post("/api/turn")
def process_agent_turn(req: TurnRequest) -> dict[str, Any]:
    """Run Semantic VAD, natural greeting/mic-check handling, Tanglish NLU, GPS match, and cooldown."""
    utterance = req.latest_text if req.latest_text is not None else req.combined_text
    vad = classify_semantic_vad(utterance, req.assistant_speaking)
    if vad["action"] == "not_turn":
        return {"vad": vad, "phase": "ignored_backchannel"}

    chitchat = classify_conversational_chitchat(utterance)
    if chitchat is not None:
        return {"vad": vad, "phase": "chitchat", "chitchat": chitchat}

    gps_lm = None
    if req.gps_lat is not None and req.gps_lon is not None:
        gps_lm = resolve_gps_to_landmark(req.gps_lat, req.gps_lon)["landmark"]

    analysis = analyze_turn(req.combined_text, gps_lm)
    cooldown = check_cooldown(
        analysis["landmark"]["ward"],
        analysis["service_id"],
        analysis["urgency"]["tier"],
    )
    record_telemetry_span(
        {
            "phase": "clarifying" if (not analysis["has_issue"] or not analysis["has_place"] or analysis["ambiguous_area"]) else "hitl_review",
            "urgency_tier": analysis["urgency"]["tier"],
            "ward": analysis["landmark"]["ward"],
        }
    )
    return {"vad": vad, "phase": "civic", "analysis": analysis, "cooldown": cooldown}


@app.websocket("/ws/voice")
async def voice_live_ws(websocket: WebSocket) -> None:
    """Real-time bidirectional JSON stream for live interim transcripts and instant state transitions."""
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            msg_type = payload.get("type", "turn")
            if msg_type == "interim":
                await websocket.send_json({"type": "interim_ack", "text": payload.get("text", "")})
                continue
            text = str(payload.get("latest_text", "") or payload.get("combined_text", ""))
            combined = str(payload.get("combined_text", text))
            vad = classify_semantic_vad(text, bool(payload.get("assistant_speaking", False)))
            if vad["action"] == "not_turn":
                await websocket.send_json({"type": "turn_result", "vad": vad, "phase": "ignored_backchannel"})
                continue
            chitchat = classify_conversational_chitchat(text)
            if chitchat is not None:
                await websocket.send_json({"type": "turn_result", "vad": vad, "phase": "chitchat", "chitchat": chitchat})
                continue
            analysis = analyze_turn(combined)
            cooldown = check_cooldown(analysis["landmark"]["ward"], analysis["service_id"], analysis["urgency"]["tier"])
            await websocket.send_json({"type": "turn_result", "vad": vad, "phase": "civic", "analysis": analysis, "cooldown": cooldown})
    except WebSocketDisconnect:
        return


@app.post("/api/location/reverse")
def reverse_location(req: ReverseGeoRequest) -> dict[str, Any]:
    """Resolve permitted GPS lat/lon to nearest Tamil Nadu Ward & Road ID."""
    return resolve_gps_to_landmark(req.lat, req.lon)


@app.post("/api/attachment/inspect")
async def inspect_attachment(file: UploadFile = File(...), note: str = "") -> JSONResponse:
    """Validate uploaded hazard photo/bill size (<1 MB GCC limit) & extract ticket/consumer refs safely."""
    raw = await file.read()
    size_kb = round(len(raw) / 1024, 1)
    filename = file.filename or "evidence"
    ticket_m = re.search(r"#?[A-Z]{2,5}-?\d{4,6}", f"{filename} {note}", re.IGNORECASE)
    extracted_ticket = ticket_m.group(0).upper() if ticket_m else None
    is_pdf = filename.lower().endswith(".pdf")
    return JSONResponse(
        {
            "filename": filename,
            "size_kb": size_kb,
            "within_gcc_1mb_limit": size_kb <= 1024,
            "type": "document_pdf" if is_pdf else "street_photo",
            "extracted_ticket": extracted_ticket,
            "pii_stored": False,
        }
    )


@app.get("/api/history")
def get_history() -> dict[str, Any]:
    """List citizen filing history for duplicate prevention."""
    return {"items": list_request_history()}


@app.post("/api/otp/send")
def send_otp(req: OtpSendRequest) -> dict[str, Any]:
    """Start prototype Mobile OTP session."""
    return issue_mobile_otp(req.phone_masked)


@app.post("/api/otp/verify")
def check_otp(req: OtpVerifyRequest) -> dict[str, Any]:
    """Verify Mobile OTP session."""
    return verify_mobile_otp(req.otp_session_id, req.code)


@app.post("/api/hitl/seal")
def seal_hitl(req: HitlSealRequest) -> dict[str, Any]:
    """Enforce Dual-Confirm Tamil HITL seal & 24h cooldown before unlocking dispatch."""
    res = verify_hitl_seal(
        mode=req.mode,
        spoken_phrase=req.spoken_phrase,
        modal_ok=req.modal_ok,
        otp_verified=req.otp_verified,
        ward=req.ward,
        service_id=req.service_id,
        urgency_tier=req.urgency_tier,
    )
    record_telemetry_span(
        {
            "phase": "approved_dispatch" if res.get("approved") else "hitl_blocked",
            "urgency_tier": req.urgency_tier,
            "ward": req.ward,
            "note": res.get("reason", "sealed"),
        }
    )
    return res


@app.post("/api/telemetry")
def log_telemetry(req: TelemetryRequest) -> dict[str, Any]:
    """Record anonymized HITL correction/trace span."""
    return {"recorded": record_telemetry_span(req.model_dump())}


@app.get("/api/telemetry")
def read_telemetry() -> dict[str, Any]:
    """Inspect recent anonymized spans."""
    return {"spans": list_telemetry_spans(), "services_count": len(SERVICE_CATALOG)}
