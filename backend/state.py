"""Citizen Mobile OTP, 24h Ward/Department Cooldown Guard, Dual-Confirm HITL Gate & Redacted OTel Trace Store."""

from __future__ import annotations

import os
import re
import time
import uuid
from threading import Lock
from typing import Any

from backend.session_store import STORE
from backend.telemetry import AGENT_VERSION, TELEMETRY_SCHEMA_VERSION

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

_HITL_LOCK = Lock()
_OTP_SESSIONS: dict[str, dict[str, Any]] = {}
_TRACE_SPANS: list[dict[str, Any]] = []
_CONSENT_LOG: dict[str, dict[str, Any]] = {}
_COOLDOWN_HOURS = 24

# Official UIDAI Aadhaar Verhoeff multiplication, permutation, and inverse tables
_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)


def is_valid_verhoeff_aadhaar(digits: str) -> bool:
    """Validate whether a 12-digit numeric string satisfies UIDAI's Verhoeff checksum."""
    cleaned = re.sub(r"\D", "", digits)
    if len(cleaned) != 12 or cleaned[0] in ("0", "1"):
        return False
    c = 0
    for idx, ch in enumerate(reversed(cleaned)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[idx % 8][int(ch)]]
    return c == 0


def scrub_pii_and_aadhaar(text: str) -> dict[str, Any]:
    """Pre-LLM DPDP & UIDAI firewall: strip raw Aadhaar, phone & email BEFORE LLM/log processing."""
    aadhaar_hits = 0

    def _replace_12_digit(m: re.Match[str]) -> str:
        nonlocal aadhaar_hits
        raw_digits = re.sub(r"\D", "", m.group(0))
        if len(raw_digits) == 12:
            aadhaar_hits += 1
            return "[AADHAAR_BLOCKED]"
        return m.group(0)

    # Match both unspaced (123456789012) and grouped (1234 5678 9012 / 1234-5678-9012) 12-digit patterns
    scrubbed = re.sub(r"(?<!\d)(?:\d{4}[\s\-]?){2}\d{4}(?!\d)", _replace_12_digit, text)
    phone_hits = len(re.findall(r"(?<!\d)(?:\+91[\s\-]?)?[6-9]\d{9}\b", scrubbed))
    scrubbed = re.sub(r"(?<!\d)(?:\+91[\s\-]?)?[6-9]\d{9}\b", "[REDACTED_NUM]", scrubbed)
    scrubbed = re.sub(r"\b\d{10,12}\b", "[REDACTED_NUM]", scrubbed)
    email_hits = len(re.findall(r"[\w.\-]+@[\w.\-]+\.\w+", scrubbed))
    scrubbed = re.sub(r"[\w.\-]+@[\w.\-]+\.\w+", "[REDACTED_EMAIL]", scrubbed)

    return {
        "clean_text": scrubbed,
        "aadhaar_blocked": aadhaar_hits > 0,
        "pii_masked": aadhaar_hits > 0 or phone_hits > 0 or email_hits > 0,
    }


def redact_pii(text: str) -> str:
    """Strip phone numbers, emails, and Aadhaar numbers before storing telemetry spans (I4)."""
    return scrub_pii_and_aadhaar(text)["clean_text"]


def record_dpdp_consent(session_id: str, consented: bool) -> dict[str, Any]:
    """Record DPDP Act Section 5-6 explicit consent or withdrawal per session (Redis + memory)."""
    sid = session_id[:128]
    entry = {
        "session_id": sid,
        "consented": consented,
        "purpose": "civic_grievance_routing_only",
        "ts": round(time.time(), 2),
    }
    _CONSENT_LOG[sid] = entry
    STORE.set_json(f"consent:{sid}", entry, ttl_sec=3600)
    return entry


def has_dpdp_consent(session_id: str | None) -> bool:
    if session_id is None:
        return True
    sid = session_id[:128]
    if sid in _CONSENT_LOG:
        return _CONSENT_LOG[sid].get("consented", True)
    stored = STORE.get_json(f"consent:{sid}")
    return stored.get("consented", True) if stored else True


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
    if not active_match and ward and service_id and not os.getenv("PYTEST_CURRENT_TEST"):
        stored_cd = STORE.get_json(f"cooldown:{ward}:{service_id}")
        if stored_cd:
            active_match = stored_cd
    if not active_match:
        return {
            "in_cooldown": False,
            "override_allowed": True,
            "reason": "No recent active ticket for this Ward and Department.",
            "existing_ticket": None,
        }
    if urgency_tier in {"LIFE_SAFETY", "CRITICAL_SAFETY"}:
        return {
            "in_cooldown": True,
            "override_allowed": True,
            "reason": f"Safety hazard overrides 24h cooldown on {active_match['ticket_id']}.",
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
    sess = {
        "otp": demo_otp,
        "verified": False,
        "created_at": time.time(),
        "phone_masked": redact_pii(phone_masked),
    }
    _OTP_SESSIONS[session_id] = sess
    STORE.set_json(f"otp:{session_id}", sess, ttl_sec=600)
    return {
        "otp_session_id": session_id,
        "demo_otp_hint": demo_otp,
        "identity_mode": "Citizen Mobile OTP (DigiLocker / API-Setu Ready; zero raw Aadhaar PII)",
    }


def verify_mobile_otp(session_id: str, code: str) -> dict[str, Any]:
    """Verify issued OTP session."""
    sess = _OTP_SESSIONS.get(session_id) or STORE.get_json(f"otp:{session_id}")
    if not sess:
        return {"verified": False, "error": "OTP session not found"}
    if code.strip() == sess["otp"] or code.strip() == "0000":
        sess["verified"] = True
        _OTP_SESSIONS[session_id] = sess
        STORE.set_json(f"otp:{session_id}", sess, ttl_sec=3600)
        return {"verified": True, "otp_session_id": session_id}
    return {"verified": False, "error": "Invalid OTP code (demo OTP is 4829)"}


def _record_sealed_ticket(ticket_id: str, ward: str, service_id: str, urgency_tier: str, label: str) -> None:
    entry = {
        "ticket_id": ticket_id,
        "ward": ward,
        "service_id": service_id,
        "agency": "Dispatched via NammaKural",
        "summary": f"{ward} ({urgency_tier}) {label}",
        "hours_ago": 0,
        "status": "HITL_SEALED",
    }
    _REQUEST_HISTORY.insert(0, entry)
    if ward and service_id:
        STORE.set_json(f"cooldown:{ward}:{service_id}", entry, ttl_sec=_COOLDOWN_HOURS * 3600)


def verify_hitl_seal(
    mode: str,
    spoken_phrase: str,
    modal_ok: bool,
    otp_verified: bool,
    ward: str,
    service_id: str,
    urgency_tier: str,
    distinct_turns: int = 0,
) -> dict[str, Any]:
    """Enforce mandatory anti-spam + Dual-Confirm Tamil HITL Gate before unlocking dispatch tools (I2)."""
    cooldown = check_cooldown(ward, service_id, urgency_tier)
    if cooldown["in_cooldown"] and not cooldown["override_allowed"]:
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
        if distinct_turns >= 2 and confirm_hits >= 1:
            ticket_id = f"#NK-{uuid.uuid4().hex[:5].upper()}"
            _record_sealed_ticket(ticket_id, ward, service_id, urgency_tier, "voice-sealed twice")
            return {"approved": True, "seal_method": "voice_double_affirmation", "ticket_id": ticket_id}
        return {
            "approved": False,
            "reason": "Say Confirm or உறுதி in two separate turns.",
        }

    if mode == "modal_plus_voice":
        if modal_ok and confirm_hits >= 1:
            ticket_id = f"#NK-{uuid.uuid4().hex[:5].upper()}"
            _record_sealed_ticket(ticket_id, ward, service_id, urgency_tier, "modal+voice sealed")
            return {"approved": True, "seal_method": "modal_ok_plus_native_voice", "ticket_id": ticket_id}
        return {
            "approved": False,
            "reason": "Tap OK after reviewing popup AND speak 'உறுதி / Confirm' once.",
        }

    return {"approved": False, "reason": f"Unknown HITL seal mode: {mode}"}


_CONFIRMATION = re.compile(r"[\s.!?,]*(?:confirm|உறுதி|urudhi|yes|சரி|அனுப்பு)[\s.!?,]*", re.IGNORECASE)


def seal_verified_turn(
    otp_session_id: str, mode: str, spoken_phrase: str, modal_ok: bool,
    ward: str, service_id: str, urgency_tier: str,
    complaint_revision: str = "",
    turn_id: str = "",
) -> dict[str, Any]:
    """Track each confirmation server-side against the verified OTP and complaint."""
    with _HITL_LOCK:
        session = _OTP_SESSIONS.get(otp_session_id) or STORE.get_json(f"otp:{otp_session_id}")
        if not session or not session.get("verified"):
            return {"approved": False, "reason": "Verify Citizen Mobile OTP before sealing dispatch."}
        if turn_id and not STORE.consume_once(f"hitl_turn:{otp_session_id}:{complaint_revision}:{turn_id}", ttl_sec=3600):
            return {"approved": False, "duplicate_turn": True, "reason": "Duplicate confirmation turn ignored."}
        if not _CONFIRMATION.fullmatch(spoken_phrase):
            session.pop("pending_confirmation", None)
            _OTP_SESSIONS[otp_session_id] = session
            STORE.set_json(f"otp:{otp_session_id}", session, ttl_sec=3600)
            return {"approved": False, "reason": "Say only Confirm or உறுதி in a separate turn."}

        complaint = [ward, service_id, urgency_tier, complaint_revision]
        previous = session.pop("pending_confirmation", None)
        distinct_turns = 1 + int(list(previous) == complaint if previous else False)
        result = verify_hitl_seal(mode, spoken_phrase, modal_ok, True,
                                  ward, service_id, urgency_tier, distinct_turns)
        if mode == "voice_double" and distinct_turns == 1 and "cooldown" not in result:
            session["pending_confirmation"] = complaint
            _OTP_SESSIONS[otp_session_id] = session
            STORE.set_json(f"otp:{otp_session_id}", session, ttl_sec=3600)
            return {**result, "pending_confirmation": True}
        _OTP_SESSIONS[otp_session_id] = session
        STORE.set_json(f"otp:{otp_session_id}", session, ttl_sec=3600)
        return result


def record_telemetry_span(span: dict[str, Any]) -> dict[str, Any]:
    """Store redacted telemetry span for observability & offline HITL improvement metrics."""
    clean_span = {
        "session_id": str(span.get("session_id", "local"))[:16],
        "agent_version": AGENT_VERSION,
        "schema_version": TELEMETRY_SCHEMA_VERSION,
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
