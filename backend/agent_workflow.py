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
import urllib.request
from typing import Any

from backend.llm_bridge import _read_env_value, probe_local_llm
from backend.logger import log_event
from backend.nlu import analyze_turn, classify_conversational_chitchat, classify_semantic_vad, classify_sentiment_urgency
from backend.state import check_cooldown, scrub_pii_and_aadhaar, verify_hitl_seal
from backend.state_packs import REGISTRY

WORKFLOW_STATES = (
    "GREET",
    "TRIAGE",
    "DISAMBIGUATE",
    "COOLDOWN_AND_OTP",
    "HITL_SEAL",
    "DISPATCH",
)

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
    pack = REGISTRY.get(state_code)
    gps_lm = None
    if gps_lat is not None and gps_lon is not None:
        nearest, _ = REGISTRY.nearest_gps_landmark(gps_lat, gps_lon, pack.state_code)
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
    lm_dict = gps_lm or (matched.model_dump() if matched else pack.landmarks[0].model_dump())
    urgency = classify_sentiment_urgency(query).__dict__
    return {
        "state_code": pack.state_code,
        "has_place": has_place,
        "has_issue": has_issue,
        "ambiguous_area": ambiguous_key,
        "wants_attachment": False,
        "service_id": svc_id if has_issue else lm_dict.get("default_service", "streetlight_eb"),
        "landmark_idx": 0,
        "landmark": lm_dict,
        "ticket_ref": "#GCC-20491",
        "urgency": urgency,
    }


def execute_tool(name: str, args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Deterministic Code > LLM tool execution bounded by DPDP/HITL invariants."""
    state_code = str(args.get("state_code") or ctx.get("state_code", "tn"))
    if name == "lookup_landmark_and_ward":
        query = str(args.get("query") or ctx.get("combined_text", ""))
        analysis = _resolve_pack_turn(query, state_code, ctx.get("gps_lat"), ctx.get("gps_lon"))
        ctx["analysis"] = analysis
        return {
            "has_issue": analysis["has_issue"],
            "has_place": analysis["has_place"],
            "ambiguous_area": analysis["ambiguous_area"],
            "ward": analysis["landmark"]["ward"],
            "landmark_name": analysis["landmark"]["name"],
            "service_id": analysis["service_id"],
            "urgency_tier": analysis["urgency"]["tier"],
        }

    if name == "update_complaint_slot":
        field = str(args.get("field", ""))
        value = scrub_pii_and_aadhaar(str(args.get("value", "")))["clean_text"]
        if field == "landmark":
            matched = REGISTRY.match_landmark(value, state_code)
            ctx["repaired_landmark"] = value
            if matched:
                ctx.setdefault("analysis", {})["landmark"] = matched.model_dump()
                ctx["analysis"]["has_place"] = True
                ctx["analysis"]["ambiguous_area"] = None
                return {"updated": "landmark", "ward": matched.ward, "name": matched.name}
            return {"updated": "landmark_text", "value": value}
        if field == "issue":
            ctx["repaired_issue"] = value
            return {"updated": "issue", "value": value}
        if field == "note":
            ctx["note"] = value
            return {"updated": "note", "value": value}
        return {"updated": False, "error": f"Unknown field {field}"}

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
            otp_verified=bool(args.get("otp_verified", ctx.get("otp_verified", False))),
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
    for m in re.finditer(r"\bWard\s+(\d{1,3})\b", clean, re.IGNORECASE):
        ward_tok = f"Ward {m.group(1)}"
        if allowed_wards and ward_tok not in allowed_wards:
            clean = clean.replace(m.group(0), "your verified Ward")
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
    if not analysis.get("has_issue") or not analysis.get("has_place") or analysis.get("ambiguous_area"):
        return "DISAMBIGUATE"
    return "HITL_SEAL"


def _run_llm_tool_loop(
    utterance: str,
    combined_clean: str,
    state_code: str,
    lang: str,
    ctx: dict[str, Any],
    history: list[dict[str, str]],
) -> tuple[str | None, list[dict[str, Any]], str]:
    """Execute bounded OpenAI tool_calls loop against Bharat-safe Unsloth/Ollama server."""
    status = probe_local_llm()
    if not status["available"] or not status["active_model"]:
        return None, [], "offline-tanglish-engine"

    url = (
        f"{_read_env_value('UNSLOTH_STUDIO_URL', 'http://127.0.0.1:8888').rstrip('/')}/v1/chat/completions"
        if status["provider"] == "unsloth-studio"
        else f"{_read_env_value('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')}/v1/chat/completions"
    )
    headers = {"Content-Type": "application/json"}
    if status["provider"] == "unsloth-studio":
        key = _read_env_value("UNSLOTH_API_KEY", "")
        if key:
            headers["Authorization"] = f"Bearer {key}"

    pack = REGISTRY.get(state_code)
    compacted_slot = {
        "state_pack": pack.state_name,
        "languages": pack.languages,
        "otp_verified": bool(ctx.get("otp_verified", False)),
    }
    sys_msg = (
        f"You are NammaKural ({pack.state_name} Civic Voice Agent). "
        f"Call tools first before citing any Ward or cooldown. Keep final speech <= 2 short sentences in "
        f"{'Tamil script' if lang == 'ta' else 'natural Tanglish/English'}. Compacted state: {json.dumps(compacted_slot)}"
    )
    messages: list[dict[str, Any]] = [{"role": "system", "content": sys_msg}]
    for h in history[-2:]:
        messages.append({"role": "assistant" if h.get("role") == "agent" else "user", "content": scrub_pii_and_aadhaar(h.get("text", ""))["clean_text"]})
    messages.append({"role": "user", "content": f"Latest: {utterance} | Accumulated: {combined_clean}"})

    tool_trace: list[dict[str, Any]] = []
    for _ in range(3):
        payload = json.dumps({
            "model": status["active_model"],
            "messages": messages,
            "tools": TOOL_SCHEMAS,
            "tool_choice": "auto",
            "max_tokens": 360,
            "temperature": 0.2,
        }).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                msg = data["choices"][0]["message"]
        except Exception:
            return None, tool_trace, status["active_model"]

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            content = str(msg.get("content", "")).strip()
            return (content or None), tool_trace, status["active_model"]

        messages.append(msg)
        for tc in tool_calls:
            fn = tc.get("function", {})
            fn_name = str(fn.get("name", ""))
            try:
                fn_args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                fn_args = {}
            out = execute_tool(fn_name, fn_args, ctx)
            tool_trace.append({"tool": fn_name, "args": fn_args, "result": out})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", fn_name),
                "content": json.dumps(out),
            })

    return None, tool_trace, status["active_model"]


def run_workflow_turn(
    utterance: str,
    combined_text: str,
    state_code: str = "tn",
    lang: str = "en",
    llm_mode: str = "offline",
    history: list[dict[str, str]] | None = None,
    gps_lat: float | None = None,
    gps_lon: float | None = None,
    otp_verified: bool = False,
    dpdp_consented: bool = True,
    assistant_speaking: bool = False,
) -> dict[str, Any]:
    """Run full DPDP-guarded workflow turn with optional live tool-calling & deterministic parity."""
    if not dpdp_consented:
        return {
            "fsm_state": "GREET",
            "blocked_reason": "dpdp_consent_withdrawn",
            "reply": "DPDP consent withdrawn. Dial helpline 1913 / 1100 directly for human assistance.",
            "clauses": ["DPDP consent withdrawn.", "Dial helpline 1913 / 1100 directly for human assistance."],
            "tool_trace": [],
        }

    # 1. Pre-LLM Aadhaar & PII Firewall
    t_start = time.time()
    scrub_latest = scrub_pii_and_aadhaar(utterance)
    scrub_combined = scrub_pii_and_aadhaar(combined_text)
    if scrub_latest["aadhaar_blocked"]:
        log_event("guardrail.aadhaar_blocked", "Blocked 12-digit Aadhaar sequence pre-LLM", {"state_code": state_code}, level="WARN")
        warn = (
            "ஆதார் எண் சொல்ல வேண்டாம் — உங்கள் மொபைல் OTP மட்டுமே போதும். தெருப் பிரச்சனையைச் சொல்லுங்கள்."
            if lang == "ta"
            else "Do not share your Aadhaar number — Mobile OTP is sufficient. Please tell me your street issue instead."
        )
        return {
            "fsm_state": "TRIAGE",
            "aadhaar_blocked": True,
            "pii_masked": True,
            "reply": warn,
            "clauses": split_tts_clauses(warn),
            "tool_trace": [{"tool": "pre_llm_aadhaar_firewall", "blocked": True}],
        }

    clean_latest = scrub_latest["clean_text"]
    clean_combined = scrub_combined["clean_text"]
    vad = classify_semantic_vad(clean_latest, assistant_speaking)
    if vad["action"] == "not_turn":
        log_event("vad.ignored", "Ignored backchannel or brief bystander noise", {"text": clean_latest})
        return {"fsm_state": "GREET", "vad": vad, "ignored_backchannel": True, "reply": "", "clauses": [], "tool_trace": []}

    chitchat = classify_conversational_chitchat(clean_latest)
    if chitchat is not None:
        reply = chitchat["reply_ta"] if lang == "ta" else chitchat["reply_en"]
        log_event("workflow.chitchat", "Responded naturally to greeting/mic-check", {"kind": chitchat["kind"], "lang": lang})
        return {"fsm_state": "GREET", "vad": vad, "chitchat": chitchat, "reply": reply, "clauses": split_tts_clauses(reply), "tool_trace": []}

    ctx: dict[str, Any] = {
        "state_code": state_code,
        "combined_text": clean_combined,
        "gps_lat": gps_lat,
        "gps_lon": gps_lon,
        "otp_verified": otp_verified,
        "dpdp_consented": dpdp_consented,
    }

    tool_trace: list[dict[str, Any]] = []
    llm_reply: str | None = None
    model_used = "deterministic-tanglish-v1"

    if llm_mode != "offline":
        llm_reply, tool_trace, model_used = _run_llm_tool_loop(
            clean_latest, clean_combined, state_code, lang, ctx, history or []
        )

    # Guarantee deterministic tool execution even if LLM omitted a tool or runs offline
    if "analysis" not in ctx:
        res = execute_tool("lookup_landmark_and_ward", {"query": clean_combined, "state_code": state_code}, ctx)
        tool_trace.append({"tool": "lookup_landmark_and_ward", "result": res})
    analysis = ctx["analysis"]

    # Detect repair utterances cleanly ("change to ...", "illa ...", "not tower park") before cooldown check
    if re.search(r"\b(illa|change|actually|no\s+not|instead|மாற்று|இல்ல)\b", clean_latest, re.IGNORECASE):
        matched_repair = REGISTRY.match_landmark(clean_latest, state_code)
        if matched_repair:
            rep = execute_tool("update_complaint_slot", {"field": "landmark", "value": matched_repair.name, "state_code": state_code}, ctx)
            tool_trace.append({"tool": "update_complaint_slot", "result": rep})
            analysis = ctx["analysis"]

    if analysis.get("has_place") and analysis.get("has_issue") and not analysis.get("ambiguous_area") and "cooldown" not in ctx:
        cd = execute_tool(
            "check_ward_cooldown",
            {
                "ward": analysis["landmark"]["ward"],
                "service_id": analysis["service_id"],
                "urgency_tier": analysis["urgency"]["tier"],
            },
            ctx,
        )
        tool_trace.append({"tool": "check_ward_cooldown", "result": cd})

    fsm_state = _derive_fsm_state(analysis, ctx.get("seal_result"))
    lm = analysis["landmark"]

    if not llm_reply:
        if fsm_state == "TRIAGE":
            llm_reply = (
                f'"{clean_latest}" — உங்கள் தெருப் பிரச்சனையையும் பகுதியையும் சொல்லுங்கள்.'
                if lang == "ta"
                else f'I heard "{clean_latest}". Tell me what civic problem needs fixing and where.'
            )
        elif fsm_state == "DISAMBIGUATE":
            if analysis.get("ambiguous_area"):
                _, spec = REGISTRY.check_ambiguous_area(clean_combined, state_code)
                llm_reply = (spec.prompt_ta or spec.prompt_en) if (spec and lang == "ta") else (spec.prompt_en if spec else "Which landmark is closest?")
            elif not analysis.get("has_place"):
                llm_reply = "Understood the issue. Allow GPS or share your nearest street landmark?"
            else:
                llm_reply = "Got the location. What civic problem needs fixing there?"
        elif fsm_state == "HITL_SEAL":
            llm_reply = (
                f"{lm['ward']} கண்டறியப்பட்டது ({analysis['urgency']['badge_ta']}). OTP சரிபார்த்து 'உறுதி, உறுதி' சொல்லவும்."
                if lang == "ta"
                else f"Resolved {lm['ward']} ({analysis['urgency']['badge_en']}). Verify OTP and say 'Confirm, Confirm' or review the Clarity Popup."
            )
        else:
            llm_reply = f"Complaint sealed for {lm['ward']}."

    safe_reply = post_guardrail_reply(llm_reply, {lm["ward"]} if analysis.get("has_place") else set())
    latency_ms = round((time.time() - t_start) * 1000, 1)
    log_event(
        "workflow.turn_complete",
        f"FSM={fsm_state} ward={lm['ward']} service={analysis['service_id']}",
        {
            "state_code": state_code,
            "model": model_used,
            "tools": [t.get("tool") for t in tool_trace],
            "latency_ms": latency_ms,
            "pii_masked": scrub_latest["pii_masked"] or scrub_combined["pii_masked"],
        },
    )
    return {
        "fsm_state": fsm_state,
        "state_code": state_code,
        "model": model_used,
        "latency_ms": latency_ms,
        "vad": vad,
        "aadhaar_blocked": False,
        "pii_masked": scrub_latest["pii_masked"] or scrub_combined["pii_masked"],
        "analysis": analysis,
        "cooldown": ctx.get("cooldown"),
        "reply": safe_reply,
        "clauses": split_tts_clauses(safe_reply),
        "tool_trace": tool_trace,
    }
