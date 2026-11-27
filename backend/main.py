"""FastAPI entrypoint serving NammaKural Pure Voice Agent & zero-key civic triage APIs."""

from __future__ import annotations

import json
import os
import uuid
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.agent_workflow import run_workflow_turn, set_workflow_consent, split_tts_clauses
from backend.llm_bridge import _read_env_value, cloud_llm, generate_civic_turn, probe_local_llm
from backend.logger import LOG_FILE, clear_logs, get_conversations, get_logs, log_event, observability_status, save_conversation_turn
from backend.tts_service import VOICE_CATALOG, synthesize_neural_mp3
from backend.nlu import (
    SERVICE_CATALOG,
    analyze_turn,
    classify_conversational_chitchat,
    classify_semantic_vad,
    resolve_gps_to_landmark,
    validate_phone_digits,
)
from backend.portal_bridge import build_gcc_preview_packet
from backend.sarvam_realtime import get_dynamic_keyterms
from backend.session_store import STORE
from backend.state import (
    check_cooldown,
    issue_mobile_otp,
    list_request_history,
    list_telemetry_spans,
    record_telemetry_span,
    scrub_pii_and_aadhaar,
    seal_verified_turn,
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
_spa_assets = ROOT_DIR / "frontend" / "dist" / "spa-assets"
if _spa_assets.is_dir():
    app.mount("/spa-assets", StaticFiles(directory=str(_spa_assets)), name="spa-assets")


class TurnRequest(BaseModel):
    combined_text: str
    latest_text: str | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    assistant_speaking: bool = False
    lang: str = "en"
    llm_mode: str = "auto"
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
    otp_session_id: str = ""
    ward: str
    service_id: str
    urgency_tier: str = "STANDARD"
    complaint_revision: str = Field(default="", max_length=160)
    turn_id: str = Field(default="", max_length=64)


class TelemetryRequest(BaseModel):
    session_id: str = "local"
    phase: str
    urgency_tier: str = "STANDARD"
    ward: str = ""
    hitl_edited: bool = False
    note: str = ""


@app.get("/")
@app.get("/debug")
@app.get("/traces")
@app.get("/telemetry")
def serve_home() -> FileResponse:
    """Serve the built React SPA if present, else fall back to index.html."""
    spa_index = ROOT_DIR / "frontend" / "dist" / "index.html"
    if spa_index.is_file() and os.getenv("NK_LEGACY_INDEX", "") != "1":
        return FileResponse(str(spa_index))
    return FileResponse(str(ROOT_DIR / "index.html"))


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    """Confirm app boots cleanly without required external secret keys."""
    sarvam_ready = bool(_read_env_value("SARVAM_API_KEY"))
    gemini_ready = bool(os.getenv("GEMINI_API_KEY", "").strip())
    cloud = cloud_llm()
    local_llm = probe_local_llm()
    if local_llm["available"]:
        voice_mode = "local-unsloth-llm"
    elif sarvam_ready or gemini_ready:
        voice_mode = "live-neural"
    else:
        voice_mode = "offline-tanglish-engine"
    pregenerated = len(list((ROOT_DIR / "assets" / "voice").glob("*.mp3")))
    return {
        "status": "ok",
        "voice_mode": voice_mode,
        "engine_mode": "cloud_api" if cloud else ("local_gpu" if local_llm["available"] else "offline_fsm"),
        "store_backend": STORE.backend_name,
        "vercel_region": os.getenv("VERCEL_REGION", "local"),
        "sarvam_stt": sarvam_ready,
        "sarvam_tts": sarvam_ready,
        "pregenerated_prompts": pregenerated,
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
    combined = scrub_pii_and_aadhaar(req.combined_text)["clean_text"]
    emergency = analyze_turn(f"{combined} {scrub_pii_and_aadhaar(utterance)['clean_text']}")
    if emergency["urgency"]["tier"] == "LIFE_SAFETY":
        return {"phase": "life_safety", "analysis": emergency, "cooldown": None, "llm": {"used": False}}
    vad = classify_semantic_vad(scrub_pii_and_aadhaar(utterance)["clean_text"], req.assistant_speaking)
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
        gps = resolve_gps_to_landmark(req.gps_lat, req.gps_lon)
        if gps["verified"]:
            gps_lm = gps["landmark"]

    analysis = analyze_turn(combined, gps_lm)
    if (not analysis["has_place"] or not analysis["has_issue"]) and llm_res and llm_res.get("landmark_text"):
        candidate = analyze_turn(f"{combined} {llm_res['landmark_text']}".strip(), gps_lm)
        if candidate["urgency"] == analysis["urgency"]:
            analysis = candidate

    cooldown = check_cooldown(
        analysis["landmark"]["ward"],
        analysis["service_id"],
        analysis["urgency"]["tier"],
    )
    record_telemetry_span(
        {
            "phase": "clarifying" if (not analysis["has_issue"] or not analysis["landmark"]["ward"] or analysis["ambiguous_area"]) else "hitl_review",
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
    res = seal_verified_turn(
        otp_session_id=req.otp_session_id,
        mode=req.mode,
        spoken_phrase=req.spoken_phrase,
        modal_ok=req.modal_ok,
        ward=req.ward,
        service_id=req.service_id,
        urgency_tier=req.urgency_tier,
        complaint_revision=req.complaint_revision,
        turn_id=req.turn_id,
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
    combined_text: str = ""
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    state_code: str = "tn"
    lang: str = "tanglish"
    llm_mode: str = "auto"
    history: list[dict[str, str]] = Field(default_factory=list)
    gps_lat: float | None = None
    gps_lon: float | None = None
    otp_verified: bool = False
    dpdp_consented: bool = True
    assistant_speaking: bool = False
    persona_name: str = "Pallavi"


class DpdpConsentRequest(BaseModel):
    session_id: str = Field(default="local", min_length=1, max_length=128)
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
        persona_name=req.persona_name,
        session_id=req.session_id,
    )
    record_telemetry_span(
        {
            "phase": res.get("fsm_state", "unknown"),
            "urgency_tier": res.get("analysis", {}).get("urgency", {}).get("tier", "STANDARD"),
            "ward": res.get("analysis", {}).get("landmark", {}).get("ward", ""),
            "note": scrub_pii_and_aadhaar(res.get("reply", ""))["clean_text"][:120],
        }
    )
    ward_lbl = res.get("analysis", {}).get("landmark", {}).get("ward", "")
    if req.dpdp_consented and not res.get("blocked_reason") and res.get("fsm_state") != "LIFE_SAFETY":
        save_conversation_turn("browser", "user", scrub_pii_and_aadhaar(req.utterance)["clean_text"],
                               fsm_state=res.get("fsm_state", ""), ward=ward_lbl, persona=scrub_pii_and_aadhaar(req.persona_name)["clean_text"])
        save_conversation_turn("browser", "agent", res.get("reply", ""),
                               fsm_state=res.get("fsm_state", ""), ward=ward_lbl, persona=scrub_pii_and_aadhaar(req.persona_name)["clean_text"])
    return res


@app.post("/api/dpdp/consent")
def update_dpdp_consent(req: DpdpConsentRequest) -> dict[str, Any]:
    """Record DPDP Act 2023 explicit notice consent or withdrawal."""
    return set_workflow_consent(req.session_id, req.consented)


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
    log_event("webrtc.offer", "Received client WebRTC SDP signaling offer", {"sdp_bytes": len(req.sdp)})
    return {
        "status": "signaling_ready",
        "received_type": req.type,
        "sdp_bytes": len(req.sdp),
        "turn_enabled": True,
        "audio_codec": "opus/16000",
    }


class ClientLogRequest(BaseModel):
    stage: str
    message: str = ""
    level: str = "INFO"
    data: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/client-log")
def ingest_client_log(req: ClientLogRequest) -> dict[str, Any]:
    """Capture PII-scrubbed browser STT/Audio/TTS events into unified backend logs."""
    entry = log_event(req.stage, req.message, req.data, level=req.level, source="browser")
    return {"logged": True, "entry": entry}


@app.get("/api/logs")
def read_logs(limit: int = 80) -> dict[str, Any]:
    """Expose recent structured pipeline logs (browser + backend + workflow tools)."""
    items = get_logs(limit)
    return {
        "count": len(items),
        "log_file": str(LOG_FILE.name),
        "observability": observability_status(),
        "items": items,
    }


@app.get("/api/conversations")
def read_past_conversations(limit: int = 60) -> dict[str, Any]:
    """Return persisted PII-redacted past conversation turns across sessions."""
    items = get_conversations(limit)
    return {"count": len(items), "items": items}


@app.delete("/api/logs")
def wipe_logs() -> dict[str, Any]:
    """Clear in-memory log ring buffer cleanly."""
    clear_logs()
    return {"cleared": True}


class TtsRequest(BaseModel):
    text: str
    voice: str = "auto"
    lang: str = "en"


@app.get("/api/tts/voices")
def list_tts_voices() -> dict[str, Any]:
    """List available neural Tamil Nadu & Indian English voices."""
    return {"voices": VOICE_CATALOG}


@app.post("/api/tts")
async def synthesize_tts(req: TtsRequest) -> Response:
    """Stream neural Tamil / Indian-English audio via Sarvam Bulbul or edge-tts, or 204 for client fallback."""
    res = await synthesize_neural_mp3(req.text, preferred_voice=req.voice, lang=req.lang)
    if not res["ok"] or not res["audio"]:
        return Response(status_code=204)
    return Response(
        content=res["audio"],
        media_type=res.get("media_type", "audio/mpeg"),
        headers={"X-NammaKural-Voice": res["voice"], "X-NammaKural-Cached": str(res.get("cached", False)).lower()},
    )


class PortalPreviewRequest(BaseModel):
    service_id: str = "streetlight_eb"
    landmark: dict[str, Any] = Field(default_factory=dict)
    summary_text: str = ""
    urgency_tier: str = "STANDARD"
    complaint_version: int = 1
    otp_verified: bool = False
    hitl_approved: bool = False
    attachment_size_kb: float = 0.0


@app.post("/api/portal/preview")
def portal_preview(req: PortalPreviewRequest) -> dict[str, Any]:
    """Validate complaint fields against GCC PGRS schema and return NK-PREVIEW packet (zero outbound gov requests)."""
    return build_gcc_preview_packet(
        service_id=req.service_id,
        landmark=req.landmark,
        summary_text=req.summary_text,
        urgency_tier=req.urgency_tier,
        complaint_version=req.complaint_version,
        otp_verified=req.otp_verified,
        hitl_approved=req.hitl_approved,
        attachment_size_kb=req.attachment_size_kb,
    )


@app.get("/api/debug/session")
def debug_session(session_id: str = "browser", state_code: str = "tn", locality: str = "") -> dict[str, Any]:
    """Expose persisted ComplaintSlots, dynamic keyterms, and store backend for /debug UI."""
    slots = STORE.get_json(f"slots:{session_id}:{state_code}") or {}
    return {
        "session_id": session_id,
        "state_code": state_code,
        "store_backend": STORE.backend_name,
        "slots": slots,
        "dynamic_keyterms": get_dynamic_keyterms(state_code, locality),
    }


@app.get("/api/telemetry/summary")
def telemetry_summary() -> dict[str, Any]:
    """Compute live P50/P90/P95/TTFT/TTFA and <500ms SLA metrics for /telemetry UI."""
    import math

    def _pct(vals: list[float], f: float) -> float | None:
        if not vals:
            return None
        s = sorted(vals)
        return round(s[math.ceil(len(s) * f) - 1], 1)

    wf_all: list[float] = []
    wf_det: list[float] = []
    llm_vals: list[float] = []
    tts_vals: list[float] = []
    ttfa_vals: list[float] = []
    pending_wf: tuple[float, float] | None = None
    for item in get_logs(150):
        st = item.get("stage", "")
        data = item.get("data") or {}
        ms = data.get("latency_ms")
        ts = item.get("ts")
        if st == "workflow.turn_complete" and isinstance(ms, (int, float)):
            wf_all.append(float(ms))
            if data.get("model") == "deterministic-tanglish-v1":
                wf_det.append(float(ms))
            if isinstance(ts, (int, float)):
                pending_wf = (float(ts), float(ms))
        elif st == "llm.fast_turn" and isinstance(ms, (int, float)):
            llm_vals.append(float(ms))
        elif st == "tts.neural_synth" and isinstance(ms, (int, float)):
            tts_vals.append(float(ms))
            if pending_wf and isinstance(ts, (int, float)) and 0 <= float(ts) - pending_wf[0] <= 10.0:
                ttfa_vals.append(pending_wf[1] + float(ms))
                pending_wf = None
        elif st == "tts.cache_hit" and pending_wf and isinstance(ts, (int, float)) and 0 <= float(ts) - pending_wf[0] <= 10.0:
            ttfa_vals.append(pending_wf[1])
            pending_wf = None
    under_500 = sum(1 for v in ttfa_vals if v <= 500.0)
    return {
        "workflow": {"count": len(wf_all), "p50": _pct(wf_all, 0.5), "p90": _pct(wf_all, 0.9), "p95": _pct(wf_all, 0.95)},
        "deterministic": {"count": len(wf_det), "p50": _pct(wf_det, 0.5), "p90": _pct(wf_det, 0.9), "p95": _pct(wf_det, 0.95)},
        "llm_ttft": {"count": len(llm_vals), "p50": _pct(llm_vals, 0.5), "p90": _pct(llm_vals, 0.9), "p95": _pct(llm_vals, 0.95)},
        "tts_synth": {"count": len(tts_vals), "p50": _pct(tts_vals, 0.5), "p90": _pct(tts_vals, 0.9), "p95": _pct(tts_vals, 0.95)},
        "ttfa": {
            "count": len(ttfa_vals),
            "p50": _pct(ttfa_vals, 0.5),
            "p90": _pct(ttfa_vals, 0.9),
            "p95": _pct(ttfa_vals, 0.95),
            "under_500ms_pct": round((under_500 / len(ttfa_vals) * 100), 1) if ttfa_vals else 0.0,
        },
        "observability": observability_status(),
    }


@app.post("/api/stt")
async def transcribe_audio_clip(audio: UploadFile = File(...), lang: str = "ta-IN") -> JSONResponse:
    """Optional backend STT endpoint routing recorded WebM/WAV clips to Sarvam Saaras or local whisper-server."""
    raw = await audio.read()
    size_kb = round(len(raw) / 1024, 1)
    sarvam_key = _read_env_value("SARVAM_API_KEY")
    if sarvam_key:
        import urllib.request

        boundary = uuid.uuid4().hex
        formats = {"audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3",
                   "audio/mp4": "m4a", "audio/ogg": "ogg", "audio/webm": "webm"}
        mime = (audio.content_type or "").split(";")[0]
        if mime not in formats:
            mime = "audio/webm"
        extension = formats[mime]
        fields = {"model": "saaras:v4", "mode": "codemix"}
        body = "".join(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
            for name, value in fields.items()
        ).encode("utf-8")
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="speech.{extension}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8") + raw + f"\r\n--{boundary}--\r\n".encode("utf-8")
        try:
            req = urllib.request.Request(
                "https://api.sarvam.ai/speech-to-text",
                data=body,
                headers={
                    "api-subscription-key": sarvam_key,
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))
                txt = str(parsed.get("transcript", "")).strip()
                log_event("stt.sarvam_saaras", "Transcribed audio clip", {"size_kb": size_kb, "lang": lang})
                return JSONResponse({"ok": True, "provider": "sarvam-saaras", "transcript": txt})
        except Exception as exc:
            log_event("stt.sarvam_error", type(exc).__name__, {"size_kb": size_kb}, level="WARN")

    log_event("stt.clip_received", "Audio clip inspected; set SARVAM_API_KEY or whisper-server for server ASR", {"size_kb": size_kb, "lang": lang}, level="WARN")
    return JSONResponse(
        {
            "ok": False,
            "provider": "browser-fallback",
            "size_kb": size_kb,
            "message": "Server STT key/daemon not set — use ta-IN browser speech.",
        }
    )
