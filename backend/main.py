"""FastAPI entrypoint serving NammaKural Pure Voice Agent & zero-key civic triage APIs."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.agent_workflow import run_workflow_turn, split_tts_clauses
from backend.llm_bridge import generate_civic_turn, probe_local_llm
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
    record_dpdp_consent,
    record_telemetry_span,
    scrub_pii_and_aadhaar,
    verify_hitl_seal,
    verify_mobile_otp,
)
from backend.state_packs import REGISTRY

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
    lang: str = "en"
    llm_mode: str = "offline"
    history: list[dict[str, str]] = Field(default_factory=list)


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
    local_llm = probe_local_llm()
    if local_llm["available"]:
        voice_mode = "local-unsloth-llm"
    elif sarvam_ready or gemini_ready:
        voice_mode = "live-neural"
    else:
        voice_mode = "offline-tanglish-engine"
    return {
        "status": "ok",
        "voice_mode": voice_mode,
        "local_llm": local_llm,
        "optional_keys": {
            "UNSLOTH_API_KEY": "configured" if local_llm["available"] else "optional (offline Tanglish active)",
            "SARVAM_API_KEY": "configured" if sarvam_ready else "key not set (offline Tanglish active)",
            "GEMINI_API_KEY": "configured" if gemini_ready else "key not set (offline Tanglish active)",
        },
        "portals_mapped": 6,
    }


@app.post("/api/turn")
def process_agent_turn(req: TurnRequest) -> dict[str, Any]:
    """Run Semantic VAD, natural greeting/mic-check handling, optional Local Unsloth LLM, Tanglish NLU & cooldown."""
    utterance = req.latest_text if req.latest_text is not None else req.combined_text
    vad = classify_semantic_vad(utterance, req.assistant_speaking)
    if vad["action"] == "not_turn":
        return {"vad": vad, "phase": "ignored_backchannel"}

    llm_res = generate_civic_turn(
        utterance=utterance,
        combined_text=req.combined_text,
        lang=req.lang,
        history=req.history,
        preferred_mode=req.llm_mode,
    )

    chitchat = classify_conversational_chitchat(utterance)
    if chitchat is not None:
        return {"vad": vad, "phase": "chitchat", "chitchat": chitchat, "llm": llm_res or {"used": False}}

    gps_lm = None
    if req.gps_lat is not None and req.gps_lon is not None:
        gps_lm = resolve_gps_to_landmark(req.gps_lat, req.gps_lon)["landmark"]

    analysis = analyze_turn(req.combined_text, gps_lm)
    if (not analysis["has_place"] or not analysis["has_issue"]) and llm_res and llm_res.get("landmark_text"):
        analysis = analyze_turn(f"{req.combined_text} {llm_res['landmark_text']}".strip(), gps_lm)

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
    return {
        "vad": vad,
        "phase": "civic",
        "analysis": analysis,
        "cooldown": cooldown,
        "llm": llm_res or {"used": False, "provider": "offline-tanglish-engine"},
    }


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


class WorkflowTurnRequest(BaseModel):
    utterance: str
    combined_text: str
    state_code: str = "tn"
    lang: str = "en"
    llm_mode: str = "offline"
    history: list[dict[str, str]] = Field(default_factory=list)
    gps_lat: float | None = None
    gps_lon: float | None = None
    otp_verified: bool = False
    dpdp_consented: bool = True
    assistant_speaking: bool = False


class DpdpConsentRequest(BaseModel):
    session_id: str = "local"
    consented: bool


class RtcOfferRequest(BaseModel):
    sdp: str
    type: str = "offer"


@app.get("/api/state-packs")
def list_state_packs() -> dict[str, Any]:
    """List loaded pluggable Pan-Bharat State Packs."""
    packs = REGISTRY.list_summaries()
    return {"count": len(packs), "default_state": "tn", "packs": packs}


@app.post("/api/workflow/turn")
def run_workflow(req: WorkflowTurnRequest) -> dict[str, Any]:
    """Run stateful 6-state Tool-Calling Workflow FSM with Pre-LLM Aadhaar/PII guardrails."""
    res = run_workflow_turn(
        utterance=req.utterance,
        combined_text=req.combined_text,
        state_code=req.state_code,
        lang=req.lang,
        llm_mode=req.llm_mode,
        history=req.history,
        gps_lat=req.gps_lat,
        gps_lon=req.gps_lon,
        otp_verified=req.otp_verified,
        dpdp_consented=req.dpdp_consented,
        assistant_speaking=req.assistant_speaking,
    )
    record_telemetry_span(
        {
            "phase": res.get("fsm_state", "unknown"),
            "urgency_tier": res.get("analysis", {}).get("urgency", {}).get("tier", "STANDARD"),
            "ward": res.get("analysis", {}).get("landmark", {}).get("ward", ""),
            "note": scrub_pii_and_aadhaar(res.get("reply", ""))["clean_text"][:120],
        }
    )
    return res


@app.post("/api/dpdp/consent")
def update_dpdp_consent(req: DpdpConsentRequest) -> dict[str, Any]:
    """Record DPDP Act 2023 explicit notice consent or withdrawal."""
    return record_dpdp_consent(req.session_id, req.consented)


@app.get("/api/rtc/config")
def get_webrtc_config() -> dict[str, Any]:
    """Return self-owned STUN + coturn TURN ICE configuration without SaaS vendor lock-in."""
    turn_url = os.getenv("TURN_SERVER_URL", "turn:127.0.0.1:3478").strip()
    return {
        "transport": "webrtc-opus-plc",
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {
                "urls": [turn_url],
                "username": "nammakural",
                "credential": "bharat-rtc-demo",
            },
        ],
    }


@app.post("/api/rtc/offer")
def rtc_offer_signaling(req: RtcOfferRequest) -> dict[str, Any]:
    """Receive client WebRTC SDP offer and prepare TURN-ready peer signaling metadata."""
    return {
        "status": "signaling_ready",
        "received_type": req.type,
        "sdp_bytes": len(req.sdp),
        "turn_enabled": True,
        "audio_codec": "opus/16000",
    }
