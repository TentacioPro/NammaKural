"""6-State Tool-Calling Workflow FSM with Pre-LLM PII/Aadhaar Firewall & Post-LLM Grounding Guardrails.

Architecture (`Code > LLM`):
- States: GREET -> TRIAGE -> DISAMBIGUATE -> COOLDOWN_AND_OTP -> HITL_SEAL -> DISPATCH
- Compact State Window (~180 tokens): avoids 8-min context bloat by passing compacted slot state + last 2 turns.
- Bharat-Safe LLM Loop: Executes genuine OpenAI `tool_calls` against Google Gemma-4 / NVIDIA Nemotron / Phi-4 / Sarvam
  when available, falling back cleanly to identical deterministic tool execution under zero-key Docker mode.
"""

from __future__ import annotations

import json
import re
import time
from collections import OrderedDict
from threading import Lock
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.llm_bridge import chat_backends, chat_message
from backend.nlu import TN_FIXTURE_MAX_DISTANCE_SQUARED, extract_landmark_text, life_safety_helpline, resolve_gps_to_landmark
from backend.logger import log_event
from backend.nlu import analyze_turn, classify_conversational_chitchat, classify_semantic_vad, classify_sentiment_urgency
from backend.portal_bridge import build_gcc_preview_packet
from backend.session_store import STORE
from backend.state import check_cooldown, has_dpdp_consent, record_dpdp_consent, scrub_pii_and_aadhaar, verify_hitl_seal
from backend.state_packs import REGISTRY

WORKFLOW_STATES = (
    "GREET",
    "TRIAGE",
    "DISAMBIGUATE",
    "COOLDOWN_AND_OTP",
    "HITL_SEAL",
    "DISPATCH",
)

_SLOT_LOCK = Lock()
_SESSIONS: OrderedDict[tuple[str, str], tuple[float, dict[str, Any]]] = OrderedDict()
_SESSION_TTL = 30 * 60
_SESSION_LIMIT = 512
_CORRECTION = re.compile(r"^\s*(?:\b(?:illa|change|actually|instead|no)\b|மாற்று|இல்ல)", re.I)


def set_workflow_consent(session_id: str, consented: bool) -> dict[str, Any]:
    with _SLOT_LOCK:
        if not consented:
            for key in list(_SESSIONS):
                if key[0] == session_id:
                    del _SESSIONS[key]
                    STORE.set_json(f"slots:{key[0]}:{key[1]}", {}, ttl_sec=1)
            STORE.set_json(f"slots:{session_id}:tn", {}, ttl_sec=1)
        return record_dpdp_consent(session_id, consented)


def _remember(key: tuple[str, str], slots: dict[str, Any]) -> None:
    now = time.monotonic()
    _SESSIONS[key] = now, slots
    _SESSIONS.move_to_end(key)
    while len(_SESSIONS) > _SESSION_LIMIT or next(iter(_SESSIONS.values()))[0] < now - _SESSION_TTL:
        _SESSIONS.popitem(last=False)


def _public_slots(slots: dict[str, Any]) -> dict[str, str]:
    return {key: slots[key] for key in ("issue", "landmark", "area", "note", "ticket_ref") if slots.get(key)}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "lookup_landmark_and_ward",
            "description": "Resolve spoken street/landmark or GPS coordinates against the active Bharat State Pack.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Combined spoken complaint + landmark text"},
                    "state_code": {"type": "string", "description": "Two-letter state pack code (e.g. 'tn', 'ka', 'in_central')"},
                },
                "required": ["query", "state_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_complaint_slot",
            "description": "Update an extracted civic field during mid-call self-correction (e.g., 'illa Anna Arch').",
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {"type": "string", "enum": ["landmark", "issue", "note", "ticket_ref"]},
                    "value": {"type": "string"},
                    "state_code": {"type": "string"},
                },
                "required": ["field", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_ward_cooldown",
            "description": "Check 24h anti-spam cooldown for a resolved Ward and service category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ward": {"type": "string"},
                    "service_id": {"type": "string"},
                    "urgency_tier": {"type": "string"},
                },
                "required": ["ward", "service_id", "urgency_tier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "seal_complaint",
            "description": "Attempt HITL dual-confirmation dispatch unlock after citizen OTP + spoken confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["voice_double", "modal_plus_voice"]},
                    "spoken_phrase": {"type": "string"},
                    "modal_ok": {"type": "boolean"},
                    "otp_verified": {"type": "boolean"},
                    "ward": {"type": "string"},
                    "service_id": {"type": "string"},
                    "urgency_tier": {"type": "string"},
                },
                "required": ["mode", "spoken_phrase", "otp_verified", "ward", "service_id"],
            },
        },
    },
]


def _resolve_pack_turn(query: str, state_code: str = "tn", gps_lat: float | None = None, gps_lon: float | None = None) -> dict[str, Any]:
    """Unified multi-state resolver supporting pluggable JSON State Packs while keeping TN deep fidelity."""
    if not REGISTRY.list_summaries():
        gps = resolve_gps_to_landmark(gps_lat, gps_lon) if gps_lat is not None and gps_lon is not None else {}
        return {**analyze_turn(query, gps["landmark"] if gps.get("verified") else None), "state_code": "tn"}
    pack = REGISTRY.get(state_code)
    gps_lm = None
    if gps_lat is not None and gps_lon is not None:
        nearest, distance_squared = REGISTRY.nearest_gps_landmark(gps_lat, gps_lon, pack.state_code)
        if pack.state_code != "tn" or distance_squared <= TN_FIXTURE_MAX_DISTANCE_SQUARED:
            gps_lm = nearest.model_dump()

    if pack.state_code == "tn":
        analysis = analyze_turn(query, gps_lm)
        analysis["state_code"] = "tn"
        return analysis

    low = query.lower()
    svc_id = "streetlight_eb"
    has_issue = False
    for sid, keywords in pack.issue_lexicon.items():
        if any(kw.lower() in low for kw in keywords):
            svc_id = sid
            has_issue = True
            break

    matched = REGISTRY.match_landmark(query, pack.state_code)
    has_place = matched is not None or gps_lm is not None
    ambiguous_key, _ = REGISTRY.check_ambiguous_area(query, pack.state_code)
    lm_dict = gps_lm or (matched.model_dump() if matched else {"name": "", "ward": ""})
    urgency = classify_sentiment_urgency(query).__dict__
    return {
        "state_code": pack.state_code,
        "has_place": has_place,
        "has_issue": has_issue,
        "landmark_text": lm_dict["name"],
        "area": None,
        "ambiguous_area": ambiguous_key,
        "wants_attachment": False,
        "service_id": svc_id if has_issue else lm_dict.get("default_service", "streetlight_eb"),
        "landmark_idx": 0,
        "landmark": lm_dict,
        "ticket_ref": "#GCC-20491",
        "urgency": urgency,
    }


def _capture_slots(slots: dict[str, Any], candidate: dict[str, Any], text: str) -> None:
    if candidate["has_issue"] and candidate["urgency"]["tier"] != "LIFE_SAFETY":
        slots.update(issue=candidate["service_id"], urgency=candidate["urgency"])
    if candidate["has_place"]:
        slots.update(landmark=candidate["landmark_text"], area=candidate["area"],
                     match=candidate["landmark"], ambiguous_area=candidate["ambiguous_area"])
    if re.search(r"\b(?:add|note|also)\b|^(?:pole|pillar)\s+\d+\b|குறிப்பு|கூடவே", text, re.I):
        slots["note"] = text[:180]
    if re.search(r"\b[A-Z]{2,5}-?\d{4,6}\b", text, re.I):
        slots["ticket_ref"] = candidate["ticket_ref"]


def _with_slots(analysis: dict[str, Any], slots: dict[str, Any]) -> dict[str, Any]:
    return {
        **analysis,
        "has_issue": bool(slots.get("issue")),
        "has_place": bool(slots.get("landmark")),
        "service_id": slots.get("issue", analysis["service_id"]),
        "landmark_text": slots.get("landmark", ""),
        "landmark": slots.get("match", analysis["landmark"]),
        "area": slots.get("area"),
        "ambiguous_area": slots.get("ambiguous_area"),
        "urgency": slots.get("urgency", analysis["urgency"]),
        "ticket_ref": slots.get("ticket_ref", analysis["ticket_ref"]),
    }


def execute_tool(name: str, args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Deterministic Code > LLM tool execution bounded by DPDP/HITL invariants."""
    state_code = str(args.get("state_code") or ctx.get("state_code", "tn"))
    if name == "lookup_landmark_and_ward":
        query = str(args.get("query") or ctx.get("combined_text", ""))
        analysis = ctx.get("analysis") or _resolve_pack_turn(query, state_code, ctx.get("gps_lat"), ctx.get("gps_lon"))
        return {
            "has_issue": analysis["has_issue"],
            "has_place": analysis["has_place"],
            "ambiguous_area": analysis["ambiguous_area"],
            "ward": analysis["landmark"]["ward"],
            "landmark_name": analysis["landmark"]["name"],
            "landmark_text": analysis["landmark_text"],
            "service_id": analysis["service_id"],
            "urgency_tier": analysis["urgency"]["tier"],
        }

    if name == "update_complaint_slot":
        field = str(args.get("field", ""))
        scrubbed = scrub_pii_and_aadhaar(str(args.get("value", "")))
        value = scrubbed["clean_text"].strip()
        latest = ctx.get("latest", "")
        if (scrubbed["pii_masked"] or not 2 <= len(value) <= 180
                or value.casefold() not in latest.casefold() or "[REDACTED" in value):
            return {"updated": False, "error": "Use a short phrase quoted from the current turn."}
        slots = ctx["slots"]
        if field == "note":
            slots["note"] = value
        elif field in {"issue", "landmark", "ticket_ref"}:
            candidate = _resolve_pack_turn(value, ctx["state_code"])
            if field == "issue" and candidate["has_issue"]:
                # An excerpt cannot downgrade urgency or replace the code-selected route.
                if slots.get("issue") not in (None, candidate["service_id"]):
                    return {"updated": False, "error": "Use the issue selected from the complete turn."}
                if not slots.get("issue"):
                    slots.update(issue=candidate["service_id"], urgency=candidate["urgency"])
            elif field == "landmark" and ctx["state_code"] == "tn":
                current_place = ctx["latest_analysis"].get("landmark_text")
                can_replace = not slots.get("landmark") or (
                    _CORRECTION.search(latest) and extract_landmark_text(value, awaiting_location=True)
                )
                if not current_place and can_replace and not candidate["has_issue"]:
                    slots.update(landmark=value, area=candidate["area"], ambiguous_area=candidate["ambiguous_area"],
                                 match={**candidate["landmark"], "name": candidate["landmark_text"] or value})
                elif not current_place or not slots.get("landmark"):
                    return {"updated": False, "error": "A correction must identify a place in the current turn."}
            elif field == "ticket_ref" and re.fullmatch(r"#?[A-Z]{2,5}-?\d{4,6}", value, re.I):
                slots["ticket_ref"] = candidate["ticket_ref"]
            else:
                return {"updated": False, "error": "The quoted value does not identify this field."}
        else:
            return {"updated": False, "error": "Unknown complaint field."}
        ctx["analysis"] = _with_slots(ctx["analysis"], slots)
        return {"updated": field, "value": slots[field]}

    if name == "check_ward_cooldown":
        res = check_cooldown(
            ward=str(args.get("ward", "")),
            service_id=str(args.get("service_id", "streetlight_eb")),
            urgency_tier=str(args.get("urgency_tier", "STANDARD")),
        )
        ctx["cooldown"] = res
        return res

    if name == "seal_complaint":
        # Strict Code > LLM precondition guard
        if not ctx.get("dpdp_consented", True):
            return {"approved": False, "reason": "Citizen DPDP consent is required before dispatch."}
        res = verify_hitl_seal(
            mode=str(args.get("mode", "voice_double")),
            spoken_phrase=str(args.get("spoken_phrase", "")),
            modal_ok=bool(args.get("modal_ok", False)),
            otp_verified=bool(ctx.get("otp_verified", False)),
            ward=str(args.get("ward", "")),
            service_id=str(args.get("service_id", "")),
            urgency_tier=str(args.get("urgency_tier", "STANDARD")),
        )
        ctx["seal_result"] = res
        return res

    return {"error": f"Unknown tool: {name}"}


def post_guardrail_reply(reply: str, allowed_wards: set[str]) -> str:
    """Enforce grounding (never hallucinate unknown Wards), scrub PII, and keep speakable."""
    clean = scrub_pii_and_aadhaar(reply)["clean_text"]
    clean = re.sub(r"[`*_#>\[\]]", "", clean).strip()
    # Prevent hallucinated Ward IDs not returned by lookup tools
    for m in re.finditer(r"(?:\bWard|வார்டு)\s+(\d{1,3})\b", clean, re.IGNORECASE):
        ward_tok = f"Ward {m.group(1)}"
        if ward_tok not in allowed_wards:
            clean = clean.replace(m.group(0), "your verified Ward" if allowed_wards else "your area")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", clean) if s.strip()]
    return " ".join(sentences[:2]) if sentences else clean[:220]


def split_tts_clauses(reply: str) -> list[str]:
    """Break final reply into short speech synthesis clauses for low-TTFA streaming playback."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?,।])\s+", reply.strip()) if p.strip()]
    return parts or ([reply.strip()] if reply.strip() else [])


def _derive_fsm_state(analysis: dict[str, Any], seal_res: dict[str, Any] | None) -> str:
    if seal_res and seal_res.get("approved"):
        return "DISPATCH"
    if not analysis.get("has_issue") and not analysis.get("has_place"):
        return "TRIAGE"
    if not analysis.get("has_issue") or not analysis["landmark"].get("ward") or analysis.get("ambiguous_area"):
        return "DISAMBIGUATE"
    return "HITL_SEAL"


def _parse_bilingual_json(raw: str) -> tuple[str, str | None]:
    """Parse optional {"display_text", "tts_text"} JSON from fast LLM turn."""
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(cleaned[start : end + 1])
            if isinstance(obj, dict) and obj.get("display_text"):
                disp = str(obj["display_text"]).strip()
                tts = str(obj.get("tts_text") or "").strip() or None
                return disp, tts
        except json.JSONDecodeError:
            pass
    return cleaned, None


def _generate_natural_reply(
    utterance: str,
    state_code: str,
    lang: str,
    preferred_mode: str,
    fsm_state: str,
    analysis: dict[str, Any],
    cooldown: dict[str, Any] | None,
    history: list[dict[str, str]],
    slots: dict[str, str],
    persona_name: str = "Pallavi",
) -> tuple[str | None, str | None, str]:
    """Single fast (~450ms) LLM conversational turn grounded directly on deterministic tool output.

    Skips Gemma-4's slow hidden thinking loop (`reasoning_effort='none'`) so natural Tamil/Tanglish
    conversation replies stream fast without falling back to rigid templates.
    Returns `(display_text, tts_text, model_used)`.
    """
    state_name = REGISTRY.get(state_code).state_name if REGISTRY.list_summaries() else "Tamil Nadu"
    lm = analysis.get("landmark", {})
    grounded_ctx = {
        "fsm_state": fsm_state,
        "slots": slots,
        "has_issue": analysis.get("has_issue"),
        "has_place": analysis.get("has_place"),
        "ambiguous_area": analysis.get("ambiguous_area"),
        "verified_ward": lm.get("ward") or None,
        "landmark": analysis["landmark_text"] or None,
        "service_id": analysis.get("service_id") if analysis.get("has_issue") else None,
        "urgency": analysis.get("urgency", {}).get("tier"),
        "in_cooldown": bool(cooldown and cooldown.get("in_cooldown")),
    }
    has_ta_script = bool(re.search(r"[\u0B80-\u0BFF]", utterance))
    if lang == "en" and not has_ta_script:
        lang_rule = "Reply in warm, intelligent, natural Indian English (1-2 concise sentences, plain text)."
    else:
        lang_rule = (
            "Reply in warm, intelligent, natural Chennai-style spoken Tamil mixed naturally with everyday English words "
            "(plain text only, 1-2 concise conversational sentences, no JSON, no markdown)."
        )

    has_active_complaint = bool(slots or analysis.get("has_issue") or analysis.get("has_place"))
    if has_active_complaint:
        sys_msg = (
            f"You are {persona_name}, a sharp, warm, human-like assistant for NammaKural ({state_name}). {lang_rule} "
            f"Active civic state: {json.dumps(grounded_ctx, ensure_ascii=False)}. "
            "Respond naturally to what the user just said. Do not re-ask for an issue or place already in slots. "
            "If verified_ward is missing and they are reporting an issue, naturally ask for a nearby landmark or junction (never invent a Ward number). "
            "If fsm_state is HITL_SEAL, confirm the exact verified_ward and ask them to verify Mobile OTP and say 'Confirm' / 'உறுதி' twice."
        )
    else:
        sys_msg = (
            f"You are {persona_name}, an intelligent, warm, witty Tamil/Tanglish conversational assistant for NammaKural ({state_name}). {lang_rule} "
            "Answer any general question, movie/life reference, or casual conversation with genuine intelligence and warmth — "
            "do NOT force civic forms or ask for a location unless the user actually mentions a problem or asks for civic help."
        )
    messages: list[dict[str, Any]] = [{"role": "system", "content": sys_msg}]
    for h in history[-8:]:
        messages.append({
            "role": "assistant" if h.get("role") == "agent" else "user",
            "content": scrub_pii_and_aadhaar(h.get("text", ""))["clean_text"],
        })
    messages.append({"role": "user", "content": utterance})

    for backend in chat_backends(preferred_mode):
        try:
            t_llm = time.monotonic()
            message = chat_message(backend, messages, max_tokens=180, temperature=0.55)
            content = str(message.get("content") or "").strip()
            if content:
                disp, tts = _parse_bilingual_json(content)
                log_event("llm.fast_turn", "Generated grounded reply", {
                    "model": backend["active_model"],
                    "latency_ms": round((time.monotonic() - t_llm) * 1000, 1),
                })
                return disp, tts, backend["active_model"]
        except (OSError, KeyError, IndexError, ValueError, TypeError, AttributeError) as exc:
            log_event("llm.fast_fallback", type(exc).__name__, level="WARN")
    return None, None, "deterministic-tanglish-v1"


def _run_llm_tool_loop(
    utterance: str,
    state_code: str,
    lang: str,
    ctx: dict[str, Any],
    preferred_mode: str,
) -> tuple[str | None, list[dict[str, Any]], str]:
    """Execute bounded OpenAI tool_calls loop against Bharat-safe Unsloth/Ollama server."""
    backend = next(iter(chat_backends(preferred_mode)), None)
    if not backend:
        return None, [], "deterministic-tanglish-v1"

    allowed_tools = {"lookup_landmark_and_ward", "check_ward_cooldown", "update_complaint_slot"}
    tool_schemas = [tool for tool in TOOL_SCHEMAS if tool["function"]["name"] in allowed_tools]
    pack = REGISTRY.get(state_code) if REGISTRY.list_summaries() else None
    state_name = pack.state_name if pack else "Tamil Nadu"
    compacted_slot = {
        "state_pack": state_name,
        "languages": pack.languages if pack else ["ta", "en"],
        "otp_verified": bool(ctx.get("otp_verified", False)),
        "slots": _public_slots(ctx["slots"]),
    }
    lang_instruction = (
        "Tamil script (தமிழ்)"
        if lang == "ta"
        else ("natural Romanized Tanglish (Tamil spoken in English letters + simple English civic terms)" if lang == "tanglish" else "natural Indian English / Tanglish")
    )
    sys_msg = (
        f"You are NammaKural ({state_name} Civic Voice Agent). "
        "Use update_complaint_slot for relevant fields. Quote a short exact phrase from the latest user turn, "
        "including for a correction. Use lookup_landmark_and_ward for verified routing. "
        f"Keep any final speech to two short sentences in {lang_instruction}. State: {json.dumps(compacted_slot, ensure_ascii=False)}"
    )
    messages: list[dict[str, Any]] = [{"role": "system", "content": sys_msg}]
    messages.append({"role": "user", "content": utterance})

    tool_trace: list[dict[str, Any]] = []
    for _ in range(3):
        try:
            msg = chat_message(backend, messages, tools=tool_schemas, tool_choice="auto",
                               max_tokens=180, temperature=0.25)
        except (OSError, KeyError, IndexError, ValueError, TypeError, AttributeError):
            return None, tool_trace, backend["active_model"]

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            content = str(msg.get("content", "")).strip()
            return (content or None), tool_trace, backend["active_model"]

        messages.append(msg)
        for tc in tool_calls:
            fn = tc.get("function", {})
            fn_name = str(fn.get("name", ""))
            try:
                fn_args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                fn_args = {}
            out = (execute_tool(fn_name, fn_args, ctx if fn_name == "update_complaint_slot" else ctx.copy())
                   if fn_name in allowed_tools and isinstance(fn_args, dict)
                   else {"error": "Tool unavailable to the language model"})
            tool_trace.append({"tool": fn_name, "result": out})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", fn_name),
                "content": json.dumps(out),
            })

    return None, tool_trace, backend["active_model"]


def speech_fields(display: str, spoken: str) -> dict[str, Any]:
    """Keep display compatibility and synthesize only Tamil-script speech and numbers."""
    return {
        "reply": display,
        "display_text": display,
        "tts_text": spoken,
        "clauses": split_tts_clauses(spoken),
    }


def _consent_blocked() -> dict[str, Any]:
    return {
        "fsm_state": "GREET",
        "blocked_reason": "dpdp_consent_withdrawn",
        **speech_fields(
            "DPDP consent withdrawn. Dial helpline 1913 / 1100 directly for human assistance.",
            "உங்க ஒப்புதல் திரும்பப் பெறப்பட்டது. உதவிக்கு 1913 அல்லது 1100 எண்ணை அழையுங்க.",
        ),
        "tool_trace": [],
    }


def _tamil_prompt(state: str, analysis: dict[str, Any], cooldown: dict[str, Any] | None) -> str:
    if cooldown and not cooldown["override_allowed"]:
        return "இந்தப் புகார் ஏற்கனவே இருக்கு. மேல் உதவிக்கு 1100 எண்ணை அழையுங்க."
    if state == "DISAMBIGUATE":
        area = analysis.get("ambiguous_area")
        if area == "velachery":
            return "விஜயநகர் பேருந்து நிலையம் பக்கமா, பீனிக்ஸ் மால் பக்கமா?"
        if area == "anna_nagar":
            return "டவர் பார்க் பக்கமா, அண்ணா ஆர்ச் பக்கமா?"
        if analysis.get("has_place") and not analysis["landmark"].get("ward"):
            return "இடத்தை குறிச்சுக்கிட்டேன். வார்டை சரிபார்க்க அருகிலுள்ள சந்திப்பு பெயரை சொல்லுங்க அல்லது ஜிபிஎஸ் அனுமதிங்க."
        if not analysis.get("has_place"):
            return "பிரச்சனை புரிஞ்சுது. பக்கத்துல இருக்கிற அடையாளம் அல்லது தெருப் பேரை சொல்லுங்க."
        return "இடத்தை குறிச்சுக்கிட்டேன். அங்க என்ன பிரச்சனைன்னு சொல்லுங்க."
    if state == "HITL_SEAL":
        ward = re.sub(r"[^0-9]", "", analysis["landmark"]["ward"])
        prefix = f"வார்டு {ward} கிடைச்சிருக்கு. " if ward else ""
        warning = "மின் ஆபத்துக்கு 1912 எண்ணை அழையுங்க. " if analysis["urgency"]["tier"] == "CRITICAL_SAFETY" else ""
        return warning + prefix + "ஒருமுறை கடவுச்சொல்லை சரிபார்த்துட்டு, தனித்தனி முறையா உறுதின்னு சொல்லுங்க."
    return "என்ன உதவி அல்லது புகார் சொல்ல விரும்புறீங்க? எந்த இடம்னு சொல்லுங்க."


class _GraphState(TypedDict, total=False):
    utterance: str
    combined_text: str
    state_code: str
    lang: str
    llm_mode: str
    history: list[dict[str, str]]
    gps_lat: float | None
    gps_lon: float | None
    otp_verified: bool
    dpdp_consented: bool
    assistant_speaking: bool
    persona_name: str
    session_id: str | None
    t_start: float
    clean_latest: str
    clean_combined: str
    pii_masked: bool
    vad: dict[str, Any]
    slots: dict[str, Any]
    snapshot: dict[str, Any]
    key: tuple[str, str] | None
    latest_analysis: dict[str, Any]
    ctx: dict[str, Any]
    analysis: dict[str, Any]
    fsm_state: str
    tool_trace: list[dict[str, Any]]
    llm_reply: str | None
    llm_tts: str | None
    use_generated_speech: bool
    model_used: str
    early_return: dict[str, Any] | None
    response: dict[str, Any]


def _node_safety_and_vad(state: _GraphState) -> dict[str, Any]:
    """Gate 1: Life-safety short-circuit, DPDP consent, Aadhaar/PII firewall, VAD & chitchat."""
    utterance = state["utterance"]
    combined_text = state["combined_text"]
    session_id = state.get("session_id")
    lang = state.get("lang", "tanglish")
    dpdp_consented = state.get("dpdp_consented", True)

    safe_input = scrub_pii_and_aadhaar(utterance if session_id else f"{combined_text} {utterance}")["clean_text"]
    if life_safety_helpline(safe_input):
        urgency = classify_sentiment_urgency(safe_input)
        return {
            "early_return": {
                "fsm_state": "LIFE_SAFETY",
                "analysis": {"has_issue": True, "has_place": False, "urgency": urgency.__dict__},
                "cooldown": None,
                "tool_trace": [],
                **speech_fields(urgency.action_ta if lang == "ta" else urgency.action_en, urgency.action_ta),
            }
        }
    if not dpdp_consented and session_id:
        set_workflow_consent(session_id, False)
    if not dpdp_consented or not has_dpdp_consent(session_id):
        return {"early_return": _consent_blocked()}

    scrub_latest = scrub_pii_and_aadhaar(utterance)
    scrub_combined = scrub_pii_and_aadhaar(combined_text)
    if scrub_latest["aadhaar_blocked"] or scrub_combined["aadhaar_blocked"]:
        log_event("guardrail.aadhaar_blocked", "Blocked 12-digit Aadhaar sequence pre-LLM", {"state_code": state["state_code"]}, level="WARN")
        warn = (
            "ஆதார் எண் சொல்ல வேண்டாம் — உங்கள் மொபைல் OTP மட்டுமே போதும். தெருப் பிரச்சனையைச் சொல்லுங்கள்."
            if lang == "ta"
            else "Do not share your Aadhaar number — Mobile OTP is sufficient. Please tell me your street issue instead."
        )
        return {
            "early_return": {
                "fsm_state": "TRIAGE",
                "aadhaar_blocked": True,
                "pii_masked": True,
                **speech_fields(warn, "ஆதார் எண் சொல்ல வேண்டாம். ஒருமுறை கடவுச்சொல் போதும். தெருப் பிரச்சனையை சொல்லுங்க."),
                "tool_trace": [{"tool": "pre_llm_aadhaar_firewall", "blocked": True}],
            }
        }

    clean_latest = scrub_latest["clean_text"]
    clean_combined = scrub_combined["clean_text"]
    vad = classify_semantic_vad(clean_latest, state.get("assistant_speaking", False))
    if vad["action"] == "not_turn":
        log_event("vad.ignored", "Ignored backchannel or brief bystander noise", {"text": clean_latest})
        return {"early_return": {"fsm_state": "GREET", "vad": vad, "ignored_backchannel": True, **speech_fields("", ""), "tool_trace": []}}

    chitchat = classify_conversational_chitchat(clean_latest)
    if chitchat is not None and not next(iter(chat_backends(state.get("llm_mode", "offline"))), None):
        reply = chitchat["reply_ta"] if lang == "ta" else (chitchat.get("reply_tanglish", chitchat["reply_en"]) if lang == "tanglish" else chitchat["reply_en"])
        log_event("workflow.chitchat", "Responded naturally to greeting/mic-check", {"kind": chitchat["kind"], "lang": lang})
        return {
            "early_return": {
                "fsm_state": "GREET",
                "vad": vad,
                "chitchat": chitchat,
                **speech_fields(reply, re.sub(r"[^\u0B80-\u0BFF0-9 .!?,]", "", chitchat["reply_ta"])),
                "tool_trace": [],
            }
        }

    return {
        "clean_latest": clean_latest,
        "clean_combined": clean_combined,
        "pii_masked": bool(scrub_latest["pii_masked"] or scrub_combined["pii_masked"]),
        "vad": vad,
        "early_return": None,
    }


def _node_slot_and_nlu(state: _GraphState) -> dict[str, Any]:
    """Gate 2: StatePack + RapidFuzz + GPS + correction versioning + Redis/Memory slot persistence."""
    clean_latest = state["clean_latest"]
    clean_combined = state["clean_combined"]
    state_code = state["state_code"]
    session_id = state.get("session_id")
    gps_lat = state.get("gps_lat")
    gps_lon = state.get("gps_lon")

    latest_analysis = _resolve_pack_turn(clean_latest, state_code)
    state_code = latest_analysis["state_code"]
    key = (session_id, state_code) if session_id else None
    with _SLOT_LOCK:
        if not has_dpdp_consent(session_id):
            if session_id:
                STORE.set_json(f"slots:{session_id}:{state_code}", {}, ttl_sec=1)
            return {"early_return": _consent_blocked()}
        entry = _SESSIONS.get(key) if key else None
        slots = entry[1].copy() if entry and time.monotonic() - entry[0] < _SESSION_TTL else {}
        if not slots and key:
            stored = STORE.get_json(f"slots:{session_id}:{state_code}")
            if stored:
                slots = stored
        prev_lm, prev_issue = slots.get("landmark"), slots.get("issue")
        if not slots and clean_combined != clean_latest:
            _capture_slots(slots, _resolve_pack_turn(clean_combined, state_code), clean_combined)
        if (
            state_code == "tn"
            and slots.get("issue")
            and (not slots.get("landmark") or _CORRECTION.search(clean_latest))
            and not latest_analysis["has_issue"]
            and not latest_analysis["has_place"]
        ):
            place = extract_landmark_text(clean_latest, awaiting_location=True)
            if place:
                latest_analysis.update(has_place=True, landmark_text=place, landmark={**latest_analysis["landmark"], "name": place})
        _capture_slots(slots, latest_analysis, clean_latest)
        if not latest_analysis["has_place"] and gps_lat is not None and gps_lon is not None:
            gps = _resolve_pack_turn("", state_code, gps_lat, gps_lon)
            _capture_slots(slots, gps, "")
        ver = int(slots.get("complaint_version") or 1)
        if (prev_lm and slots.get("landmark") != prev_lm) or (prev_issue and slots.get("issue") != prev_issue):
            ver += 1
        slots["complaint_version"] = ver
        snapshot = slots.copy()
        if key:
            _remember(key, snapshot)
            STORE.set_json(f"slots:{session_id}:{state_code}", snapshot, ttl_sec=3600)

    ctx: dict[str, Any] = {
        "state_code": state_code,
        "combined_text": clean_combined,
        "latest": clean_latest,
        "latest_analysis": latest_analysis,
        "slots": slots,
        "analysis": _with_slots(latest_analysis, slots),
        "otp_verified": state.get("otp_verified", False),
        "dpdp_consented": state.get("dpdp_consented", True),
    }

    tool_trace: list[dict[str, Any]] = []
    llm_reply: str | None = None
    model_used = "deterministic-tanglish-v1"
    llm_mode = state.get("llm_mode", "offline")

    first_backend = next(iter(chat_backends(llm_mode)), None) if llm_mode != "offline" else None
    if (
        llm_mode != "offline"
        and ctx["analysis"]["urgency"]["tier"] != "CRITICAL_SAFETY"
        and first_backend is not None
        and first_backend.get("provider") != "sarvam-cloud"
        and (llm_mode == "unsloth" or (key and not (latest_analysis["has_issue"] and latest_analysis["landmark"].get("ward"))))
    ):
        tool_reply, tool_trace, model_used = _run_llm_tool_loop(clean_latest, state_code, state.get("lang", "tanglish"), ctx, llm_mode)
        if not key:
            llm_reply = tool_reply
        if key and slots != snapshot:
            with _SLOT_LOCK:
                current = _SESSIONS.get(key)
                if current and current[1] is snapshot and has_dpdp_consent(session_id):
                    _remember(key, slots.copy())
                    STORE.set_json(f"slots:{session_id}:{state_code}", slots.copy(), ttl_sec=3600)

    if not any(step["tool"] == "lookup_landmark_and_ward" for step in tool_trace):
        res = execute_tool("lookup_landmark_and_ward", {}, ctx)
        tool_trace.append({"tool": "lookup_landmark_and_ward", "result": res})
    analysis = ctx["analysis"]

    if latest_analysis["has_place"] and _CORRECTION.search(clean_latest):
        tool_trace.append({"tool": "update_complaint_slot", "result": {"updated": "landmark"}})

    if analysis["landmark"].get("ward") and analysis["has_issue"] and not analysis["ambiguous_area"]:
        cd = execute_tool(
            "check_ward_cooldown",
            {"ward": analysis["landmark"]["ward"], "service_id": analysis["service_id"], "urgency_tier": analysis["urgency"]["tier"]},
            ctx,
        )
        tool_trace.append({"tool": "check_ward_cooldown", "result": cd})

    fsm_state = _derive_fsm_state(analysis, ctx.get("seal_result"))
    if not has_dpdp_consent(session_id):
        return {"early_return": _consent_blocked()}

    return {
        "state_code": state_code,
        "key": key,
        "slots": slots,
        "snapshot": snapshot,
        "latest_analysis": latest_analysis,
        "ctx": ctx,
        "analysis": analysis,
        "fsm_state": fsm_state,
        "tool_trace": tool_trace,
        "llm_reply": llm_reply,
        "llm_tts": None,
        "model_used": model_used,
    }


def _node_respond_conversational(state: _GraphState) -> dict[str, Any]:
    """Generate natural grounded Tanglish/Tamil reply via fast LLM when available."""
    llm_reply = state.get("llm_reply")
    llm_tts = state.get("llm_tts")
    model_used = state.get("model_used", "deterministic-tanglish-v1")
    analysis = state["analysis"]
    fsm_state = state["fsm_state"]
    lm = analysis["landmark"]

    if not llm_reply and state.get("llm_mode") != "offline" and analysis["urgency"]["tier"] != "CRITICAL_SAFETY":
        llm_reply, llm_tts, fast_model = _generate_natural_reply(
            utterance=state["clean_latest"],
            preferred_mode=state.get("llm_mode", "auto"),
            state_code=state["state_code"],
            lang=state.get("lang", "tanglish"),
            fsm_state=fsm_state,
            analysis=analysis,
            cooldown=state["ctx"].get("cooldown"),
            history=state.get("history") or [],
            slots=_public_slots(state["slots"]),
            persona_name=state.get("persona_name", "Pallavi"),
        )
        if llm_reply:
            model_used = fast_model

    # Enforce Code > LLM on HITL_SEAL so Ward IDs are never omitted or hallucinated.
    if fsm_state == "HITL_SEAL" and llm_reply and (
        lm["ward"].lower() not in llm_reply.lower() and lm["ward"].replace("Ward", "வார்டு") not in llm_reply
    ):
        llm_reply = llm_tts = None

    if not llm_reply:
        return _node_respond_deterministic(state)
    return {"llm_reply": llm_reply, "llm_tts": llm_tts, "use_generated_speech": True, "model_used": model_used}


def _node_respond_deterministic(state: _GraphState) -> dict[str, Any]:
    """Zero-key deterministic Tamil/Tanglish/English prompt builder."""
    if state.get("llm_reply"):
        return {}
    fsm_state = state["fsm_state"]
    analysis = state["analysis"]
    lm = analysis["landmark"]
    lang = state.get("lang", "tanglish")
    clean_latest = state["clean_latest"]

    if fsm_state == "TRIAGE":
        if lang == "ta":
            reply = f'"{clean_latest}" — என்ன பிரச்சனை அல்லது உதவி தேவை, எந்த இடம்னு சொல்லுங்கள்.'
        elif lang == "tanglish":
            reply = f'"{clean_latest}" keten. Enna vishayam / problem, endha idam pakkam-nu sollunga?'
        else:
            reply = f'I heard "{clean_latest}". Tell me what issue or help you need and where it is located.'
    elif fsm_state == "DISAMBIGUATE":
        if analysis.get("ambiguous_area"):
            area = analysis["ambiguous_area"]
            if area == "velachery":
                reply = "Are you near Vijayanagar Bus Stand or Phoenix Marketcity?"
            elif area == "anna_nagar":
                reply = "Are you near Tower Park or Anna Arch?"
            else:
                _, spec = REGISTRY.check_ambiguous_area(state["clean_combined"], state["state_code"])
                reply = spec.prompt_en if spec else "Which landmark is closest?"
            if lang == "ta":
                reply = _tamil_prompt(fsm_state, analysis, state["ctx"].get("cooldown"))
        elif analysis.get("has_place") and not lm.get("ward"):
            reply = (
                _tamil_prompt(fsm_state, analysis, state["ctx"].get("cooldown"))
                if lang == "ta"
                else f"I noted {analysis['landmark_text']}. To verify its ward, share a nearby junction or allow GPS."
            )
        elif not analysis.get("has_place"):
            reply = (
                "Vishayam purinjidhu. GPS allow pannunga illa nearest landmark / area sollunga?"
                if lang == "tanglish"
                else "Understood the issue. Allow GPS or share your nearest landmark or area?"
            )
        else:
            reply = (
                "Location note pannitten. Anga enna issue-nu sollunga?"
                if lang == "tanglish"
                else "Got the location. What issue needs fixing there?"
            )
    elif fsm_state == "HITL_SEAL":
        if lang == "ta":
            reply = f"{lm['ward']} கண்டறியப்பட்டது ({analysis['urgency']['badge_ta']}). OTP சரிபார்த்து தனித்தனி முறையா 'உறுதி' சொல்லவும்."
        elif lang == "tanglish":
            reply = f"Seri! {lm['ward']} ({analysis['urgency']['badge_en']}) ready-aa irukku. OTP check panni rendu thani turns-la 'Confirm' sollunga illa Clarity Popup open pannunga."
        else:
            reply = f"Resolved {lm['ward']} ({analysis['urgency']['badge_en']}). Verify OTP and say 'Confirm' in two separate turns or review the Clarity Popup."
    else:
        reply = f"Complaint sealed for {lm['ward']}."

    return {"llm_reply": reply, "llm_tts": None, "use_generated_speech": False}


def _node_finalize(state: _GraphState) -> dict[str, Any]:
    """Apply post-LLM Ward grounding, build TTS text & GCC preview packet, and emit telemetry."""
    analysis = state["analysis"]
    lm = analysis["landmark"]
    fsm_state = state["fsm_state"]
    slots = state["slots"]
    session_id = state.get("session_id")
    if not has_dpdp_consent(session_id):
        return {"response": _consent_blocked()}

    raw_reply = state.get("llm_reply") or ""
    llm_tts = state.get("llm_tts")
    safe_reply = post_guardrail_reply(raw_reply, {lm["ward"]} if analysis.get("has_place") else set())
    candidate_tts = llm_tts or (safe_reply if state.get("use_generated_speech") else "")
    if candidate_tts and re.search(r"[\u0B80-\u0BFF]", candidate_tts):
        for eng, tam in (
            (r"\bWard\b", "வார்டு"),
            (r"\bOTP\b", "ஓடிபி"),
            (r"\bGPS\b", "ஜிபிஎஸ்"),
            (r"\barea\b", "ஏரியா"),
            (r"\bstreetlight\b", "ஸ்ட்ரீட் லைட்"),
            (r"\bstreet\b", "தெரு"),
            (r"\bneighborhood\b", "பகுதி"),
            (r"\bhelpful\b", "உதவியா"),
            (r"\bhelp\b", "ஹெல்ப்"),
            (r"\bperson\b", "நபர்"),
            (r"\btrouble\b", "பிரச்சனை"),
            (r"\bissue\b", "பிரச்சனை"),
            (r"\bproblem\b", "பிரச்சனை"),
            (r"\bConfirm\b", "உறுதி"),
            (r"\bClarity Popup\b", "சரிபார்ப்புப் பெட்டி"),
        ):
            candidate_tts = re.sub(eng, tam, candidate_tts, flags=re.IGNORECASE)
        tts_out = post_guardrail_reply(candidate_tts, {lm["ward"]} if analysis.get("has_place") else set())
    elif state.get("use_generated_speech") and safe_reply:
        tts_out = safe_reply
    else:
        tts_out = _tamil_prompt(fsm_state, analysis, state["ctx"].get("cooldown"))

    latency_ms = round((time.time() - state["t_start"]) * 1000, 1)
    model_used = state.get("model_used", "deterministic-tanglish-v1")
    tool_trace = state.get("tool_trace", [])
    log_event(
        "workflow.turn_complete",
        f"FSM={fsm_state} ward={lm['ward']} service={analysis['service_id']}",
        {
            "state_code": state["state_code"],
            "model": model_used,
            "tools": [t.get("tool") for t in tool_trace],
            "latency_ms": latency_ms,
            "pii_masked": state.get("pii_masked", False),
        },
    )
    preview_packet = (
        build_gcc_preview_packet(
            service_id=analysis["service_id"],
            landmark=lm,
            summary_text=state["clean_combined"] or state["clean_latest"],
            urgency_tier=analysis["urgency"]["tier"],
            complaint_version=int(slots.get("complaint_version") or 1),
            otp_verified=state.get("otp_verified", False),
            hitl_approved=(fsm_state == "DISPATCH"),
        )
        if fsm_state in ("HITL_SEAL", "DISPATCH")
        else None
    )
    return {
        "response": {
            "fsm_state": fsm_state,
            "state_code": state["state_code"],
            "model": model_used,
            "latency_ms": latency_ms,
            "vad": state["vad"],
            "aadhaar_blocked": False,
            "pii_masked": state.get("pii_masked", False),
            "complaint_version": int(slots.get("complaint_version") or 1),
            "text_contract": {"raw_asr": state["utterance"], "normalized_text": state["clean_latest"]},
            "analysis": analysis,
            "slots": _public_slots(slots),
            "cooldown": state["ctx"].get("cooldown"),
            "preview_packet": preview_packet,
            **speech_fields(safe_reply, tts_out),
            "tool_trace": tool_trace,
        }
    }


def _route_after_safety(state: _GraphState) -> str:
    return END if state.get("early_return") is not None else "slot_and_nlu"


def _route_after_nlu(state: _GraphState) -> str:
    if state.get("early_return") is not None:
        return END
    if state.get("llm_mode") != "offline" and state["analysis"]["urgency"]["tier"] != "CRITICAL_SAFETY":
        return "respond_conversational"
    return "respond_deterministic"


def _build_workflow_graph():
    builder = StateGraph(_GraphState)
    builder.add_node("safety_and_vad", _node_safety_and_vad)
    builder.add_node("slot_and_nlu", _node_slot_and_nlu)
    builder.add_node("respond_conversational", _node_respond_conversational)
    builder.add_node("respond_deterministic", _node_respond_deterministic)
    builder.add_node("finalize", _node_finalize)

    builder.add_edge(START, "safety_and_vad")
    builder.add_conditional_edges("safety_and_vad", _route_after_safety, {END: END, "slot_and_nlu": "slot_and_nlu"})
    builder.add_conditional_edges(
        "slot_and_nlu",
        _route_after_nlu,
        {
            END: END,
            "respond_conversational": "respond_conversational",
            "respond_deterministic": "respond_deterministic",
        },
    )
    builder.add_edge("respond_conversational", "finalize")
    builder.add_edge("respond_deterministic", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile()


_WORKFLOW_GRAPH = _build_workflow_graph()


def run_workflow_turn(
    utterance: str,
    combined_text: str,
    state_code: str = "tn",
    lang: str = "tanglish",
    llm_mode: str = "offline",
    history: list[dict[str, str]] | None = None,
    gps_lat: float | None = None,
    gps_lon: float | None = None,
    otp_verified: bool = False,
    dpdp_consented: bool = True,
    assistant_speaking: bool = False,
    persona_name: str = "Pallavi",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Execute one turn through the LangGraph StateGraph with Code > LLM & DPDP guardrails."""
    out = _WORKFLOW_GRAPH.invoke(
        {
            "utterance": utterance,
            "combined_text": combined_text,
            "state_code": state_code,
            "lang": lang,
            "llm_mode": llm_mode,
            "history": history or [],
            "gps_lat": gps_lat,
            "gps_lon": gps_lon,
            "otp_verified": otp_verified,
            "dpdp_consented": dpdp_consented,
            "assistant_speaking": assistant_speaking,
            "persona_name": persona_name,
            "session_id": session_id,
            "t_start": time.time(),
        }
    )
    if out.get("early_return") is not None:
        return out["early_return"]
    return out["response"]
