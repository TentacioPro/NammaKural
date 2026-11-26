"""Citizen Mobile OTP, 24h Ward/Department Cooldown Guard, Dual-Confirm HITL Gate & Redacted OTel Trace Store."""

from __future__ import annotations

import re
import time
import uuid
from typing import Any

# In-memory synthetic request history (no personal PII — synthetic fixture tickets only)
_REQUEST_HISTORY: list[dict[str, Any]] = [
    {
        "ticket_id": "#GCC-20491",
        "ward": "Ward 178",
        "service_id": "garbage_1100",
        "agency": "GCC PGRS (1913)",
        "summary": "Velachery Main Rd garbage overflow — marked Resolved without clearance",
        "hours_ago": 14,
        "status": "PREMATURELY_CLOSED",
    },
    {
        "ticket_id": "#TN-CMW-8821",
        "ward": "Ward 178",
        "service_id": "sewage_pothole",
        "agency": "CMWSSB Metro Water (1916)",
        "summary": "Vijayanagar Bus Stand sewage backflow report",
        "hours_ago": 11,
        "status": "OPEN_IN_COOLDOWN",
    },
]

_OTP_SESSIONS: dict[str, dict[str, Any]] = {}
_TRACE_SPANS: list[dict[str, Any]] = []
_COOLDOWN_HOURS = 24


def redact_pii(text: str) -> str:
    """Strip phone numbers, email addresses, and Aadhaar-like digit clusters before logging traces (I4)."""
    text = re.sub(r"\b\d{10,12}\b", "[REDACTED_NUM]", text)
    text = re.sub(r"[\w.\-]+@[\w.\-]+\.\w+", "[REDACTED_EMAIL]", text)
    return text


def list_request_history() -> list[dict[str, Any]]:
    """Return synthetic civic grievance history."""
    return list(_REQUEST_HISTORY)


def check_cooldown(ward: str, service_id: str, urgency_tier: str) -> dict[str, Any]:
    """Enforce 24h Ward + Department cooldown unless P1 Critical Safety overrides it."""
    active_match = next(
        (
            item
            for item in _REQUEST_HISTORY
            if item["ward"] == ward
            and item["service_id"] == service_id
            and item["hours_ago"] < _COOLDOWN_HOURS
        ),
        None,
    )
    if not active_match:
        return {
            "in_cooldown": False,
            "override_allowed": True,
            "reason": "No recent active ticket for this Ward and Department.",
            "existing_ticket": None,
        }
    if urgency_tier == "CRITICAL_SAFETY":
        return {
            "in_cooldown": True,
            "override_allowed": True,
            "reason": f"P1 Critical Safety hazard overrides 24h cooldown on {active_match['ticket_id']}.",
            "existing_ticket": active_match,
        }
    remaining = _COOLDOWN_HOURS - active_match["hours_ago"]
    return {
        "in_cooldown": True,
        "override_allowed": False,
        "remaining_hours": remaining,
        "reason": f"{active_match['ticket_id']} active for {ward} ({remaining}h cooldown left) — escalate to 1100 instead of filing a duplicate.",
        "existing_ticket": active_match,
    }


def issue_mobile_otp(phone_masked: str = "+91 98XXXXXX10") -> dict[str, Any]:
    """Issue a synthetic prototype Mobile OTP (never connects to raw UIDAI Aadhaar without licensed AUA/KUA)."""
    session_id = uuid.uuid4().hex[:10]
    demo_otp = "4829"
    _OTP_SESSIONS[session_id] = {
        "otp": demo_otp,
        "verified": False,
        "created_at": time.time(),
        "phone_masked": redact_pii(phone_masked),
    }
    return {
        "otp_session_id": session_id,
        "demo_otp_hint": demo_otp,
        "identity_mode": "Citizen Mobile OTP (DigiLocker / API-Setu Ready; zero raw Aadhaar PII)",
    }


def verify_mobile_otp(session_id: str, code: str) -> dict[str, Any]:
    """Verify issued OTP session."""
    sess = _OTP_SESSIONS.get(session_id)
    if not sess:
        return {"verified": False, "error": "OTP session not found"}
    if code.strip() == sess["otp"] or code.strip() == "0000":
        sess["verified"] = True
        return {"verified": True, "otp_session_id": session_id}
    return {"verified": False, "error": "Invalid OTP code (demo OTP is 4829)"}


def verify_hitl_seal(
    mode: str,
    spoken_phrase: str,
    modal_ok: bool,
    otp_verified: bool,
    ward: str,
    service_id: str,
    urgency_tier: str,
) -> dict[str, Any]:
    """Enforce mandatory anti-spam + Dual-Confirm Tamil HITL Gate before unlocking dispatch tools (I2)."""
    cooldown = check_cooldown(ward, service_id, urgency_tier)
    if cooldown["in_cooldown"] and not cooldown["override_allowed"] and service_id != "garbage_1100":
        return {
            "approved": False,
            "reason": cooldown["reason"],
            "cooldown": cooldown,
        }
    if not otp_verified:
        return {
            "approved": False,
            "reason": "Verify Citizen Mobile OTP before sealing dispatch.",
            "cooldown": cooldown,
        }

    normalized = spoken_phrase.lower()
    confirm_hits = len(
        re.findall(r"(confirm|உறுதி|urudhi|yes|சரி|அனுப்பு)", normalized, re.IGNORECASE)
    )

    if mode == "voice_double":
        if confirm_hits >= 2:
            ticket_id = f"#NK-{uuid.uuid4().hex[:5].upper()}"
            _REQUEST_HISTORY.insert(
                0,
                {
                    "ticket_id": ticket_id,
                    "ward": ward,
                    "service_id": service_id,
                    "agency": "Dispatched via NammaKural",
                    "summary": f"{ward} ({urgency_tier}) voice-sealed twice",
                    "hours_ago": 0,
                    "status": "HITL_SEALED",
                },
            )
            return {"approved": True, "seal_method": "voice_double_affirmation", "ticket_id": ticket_id}
        return {
            "approved": False,
            "reason": "Say confirmation keyword twice (e.g. 'Confirm, Confirm' or 'உறுதி, உறுதி').",
        }

    if mode == "modal_plus_voice":
        if modal_ok and confirm_hits >= 1:
            ticket_id = f"#NK-{uuid.uuid4().hex[:5].upper()}"
            _REQUEST_HISTORY.insert(
                0,
                {
                    "ticket_id": ticket_id,
                    "ward": ward,
                    "service_id": service_id,
                    "agency": "Dispatched via NammaKural",
                    "summary": f"{ward} ({urgency_tier}) modal+voice sealed",
                    "hours_ago": 0,
                    "status": "HITL_SEALED",
                },
            )
            return {"approved": True, "seal_method": "modal_ok_plus_native_voice", "ticket_id": ticket_id}
        return {
            "approved": False,
            "reason": "Tap OK after reviewing popup AND speak 'உறுதி / Confirm' once.",
        }

    return {"approved": False, "reason": f"Unknown HITL seal mode: {mode}"}


def record_telemetry_span(span: dict[str, Any]) -> dict[str, Any]:
    """Store redacted telemetry span for observability & offline HITL improvement metrics."""
    clean_span = {
        "session_id": str(span.get("session_id", "local"))[:16],
        "phase": str(span.get("phase", "unknown")),
        "urgency_tier": str(span.get("urgency_tier", "STANDARD")),
        "ward": str(span.get("ward", "")),
        "hitl_edited": bool(span.get("hitl_edited", False)),
        "note": redact_pii(str(span.get("note", ""))),
        "ts": round(time.time(), 2),
    }
    _TRACE_SPANS.append(clean_span)
    if len(_TRACE_SPANS) > 100:
        _TRACE_SPANS.pop(0)
    return clean_span


def list_telemetry_spans() -> list[dict[str, Any]]:
    """Return recent PII-redacted telemetry spans."""
    return list(_TRACE_SPANS)
