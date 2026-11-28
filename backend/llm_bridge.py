"""Optional zero-key-safe bridge to local Unsloth Studio / Ollama or optional OpenAI-compatible APIs.

Deterministic NLU & HITL safety (`Code > LLM`) always remain authoritative in `backend/nlu.py` and
`backend/state.py`. When a local LLM (such as Unsloth Studio serving `gemma-4-E2B-it-Q4_K_M` on
`127.0.0.1:8888` or Ollama on `11434`) is reachable, this bridge enhances conversational Tamil/Tanglish
replies and free-form entity extraction while stripping all reasoning traces and enforcing timeouts.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

from backend.logger import log_event
from backend.state import scrub_pii_and_aadhaar

ROOT_DIR = Path(__file__).resolve().parent.parent

_SYSTEM_PROMPT = """You are NammaKural (நம்ம குரல்), a compassionate Tamil Nadu civic voice assistant.
Respond ONLY with strict JSON (no markdown fences) matching:
{
  "reply": "<1-2 concise natural sentences in the citizen's language (Tanglish, Tamil script, or English)>",
  "service_hint": "<one of: streetlight_eb | sewage_pothole | water_pipe | ration_tnpds | garbage_1100 | unknown>",
  "landmark_text": "<extracted street, area, or landmark if mentioned else empty string>",
  "urgency_hint": "<P1 | P2 | P3>"
}
Never claim a ticket has been submitted before Citizen OTP + Dual-Confirm HITL approval. Do not invent Ward numbers."""


def _read_env_value(name: str, default: str = "") -> str:
    if name in os.environ:
        return os.environ[name].strip()
    env_file = ROOT_DIR / ".env"
    if not env_file.is_file():
        return default
    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            k, v = stripped.split("=", 1)
            if k.strip() == name:
                return v.strip().strip('"').strip("'")
    except OSError:
        pass
    return default


def _pick_chat_model(models: list[str], override: str = "") -> str:
    disallowed = ("asr", "whisper", "tts", "embed", "qwen", "deepseek")
    chat_candidates = [m for m in models if m and not any(tok in m.lower() for tok in disallowed)]
    if override in chat_candidates:
        return override
    if not chat_candidates:
        return ""
    for preferred in ("gemma-4", "nemotron", "phi-4", "sarvam", "llama"):
        for m in chat_candidates:
            if preferred in m.lower():
                return m
    return chat_candidates[0]


def probe_local_llm() -> dict[str, Any]:
    """Local Gemma-4 (Unsloth/Ollama) probe disabled for now; use Cloud APIs or deterministic engine."""
    # unsloth_url = _read_env_value("UNSLOTH_STUDIO_URL", "http://127.0.0.1:8888").rstrip("/")
    # unsloth_key = _read_env_value("UNSLOTH_API_KEY", "")
    # model_override = _read_env_value("LOCAL_LLM_MODEL", "")
    # ... (Gemma-4 local probe commented out to focus on APIs)
    return {
        "available": False,
        "provider": "offline-tanglish-engine",
        "active_model": "deterministic-tanglish-v1",
        "models": [],
    }


def cloud_llm() -> dict[str, str] | None:
    base_url = _read_env_value("LLM_BASE_URL").rstrip("/")
    key = _read_env_value("LLM_API_KEY")
    model = _pick_chat_model([_read_env_value("LLM_MODEL")])
    if base_url.startswith(("https://", "http://")) and key and model:
        return {
            "provider": "cloud-api",
            "active_model": model,
            "url": f"{base_url}/chat/completions",
            "key": key,
        }
    sarvam_key = _read_env_value("SARVAM_API_KEY")
    if sarvam_key and not _read_env_value("LLM_MODEL"):
        return {
            "provider": "sarvam-cloud",
            "active_model": "sarvam-105b-conversations",
            "url": "https://api.sarvam.ai/v1/chat/completions",
            "key": sarvam_key,
        }
    return None


def chat_backends(preferred_mode: str):
    """Yield cloud then local endpoints, allowing callers to fall back on request failure."""
    if preferred_mode == "offline":
        return
    if preferred_mode not in {"unsloth", "ollama", "local_gpu"}:
        cloud = cloud_llm()
        if cloud:
            yield cloud
    local = probe_local_llm()
    if not local["available"]:
        return
    provider = local["provider"]
    if preferred_mode == "ollama" and provider != "ollama":
        return
    unsloth = provider == "unsloth-studio"
    setting, default = ("UNSLOTH_STUDIO_URL", "http://127.0.0.1:8888") if unsloth else ("OLLAMA_URL", "http://127.0.0.1:11434")
    yield {
        "provider": provider,
        "active_model": local["active_model"],
        "url": f"{_read_env_value(setting, default).rstrip('/')}/v1/chat/completions",
        "key": _read_env_value("UNSLOTH_API_KEY") if unsloth else "",
    }


def chat_message(backend: dict[str, str], messages: list[dict[str, Any]], **options: Any) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if backend["key"]:
        if backend["provider"] == "sarvam-cloud":
            headers["api-subscription-key"] = backend["key"]
        else:
            headers["Authorization"] = f"Bearer {backend['key']}"
    if backend["provider"] == "unsloth-studio":
        options["reasoning_effort"] = "none"
    payload = json.dumps({"model": backend["active_model"], "messages": messages, **options}).encode("utf-8")
    req = urllib.request.Request(backend["url"], data=payload, headers=headers)
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        usage = data.get("usage")
        if isinstance(usage, dict):
            from backend.call_telemetry import turn_context

            if turn_context.get():
                detail = usage.get("prompt_tokens_details")
                fields = {key: usage.get(key) for key in ("prompt_tokens", "completion_tokens")}
                if isinstance(detail, dict):
                    fields["cached_tokens"] = detail.get("cached_tokens")
                log_event("llm.usage", data={key: value for key, value in fields.items()
                                           if type(value) is int and value >= 0})
        return data["choices"][0]["message"]


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    cleaned = re.sub(r"```(?:json)?|```", "", raw_text).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(cleaned[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def generate_civic_turn(
    utterance: str,
    combined_text: str,
    lang: str = "en",
    history: list[dict[str, str]] | None = None,
    preferred_mode: str = "auto",
) -> dict[str, Any] | None:
    """Optionally call running local Unsloth/Ollama model for conversational slot extraction & reply."""
    if preferred_mode == "offline":
        return None

    latest = scrub_pii_and_aadhaar(utterance)
    combined = scrub_pii_and_aadhaar(combined_text)
    if latest["aadhaar_blocked"] or combined["aadhaar_blocked"]:
        return None
    utterance = latest["clean_text"]
    combined_text = combined["clean_text"]
    messages: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for item in (history or [])[-4:]:
        role = "assistant" if item.get("role") == "agent" else "user"
        txt = scrub_pii_and_aadhaar(str(item.get("text", "")))["clean_text"].strip()
        if txt:
            messages.append({"role": role, "content": txt})

    lang_hint = "Tamil script (தமிழ்)" if lang == "ta" else "natural Tanglish or English"
    user_msg = (
        f"Preferred language: {lang_hint}\n"
        f"Context so far: {combined_text}\n"
        f"Latest user speech: {utterance}"
    )
    messages.append({"role": "user", "content": user_msg})

    for backend in chat_backends(preferred_mode):
        try:
            message = chat_message(backend, messages, max_tokens=180, temperature=0.35)
            content = str(message.get("content") or "").strip()
            if not content:
                continue
            parsed = _extract_json_object(content)
            return {
                "used": True,
                "provider": backend["provider"],
                "model": backend["active_model"],
                "reply": str(parsed.get("reply", "")) if parsed else content,
                "service_hint": str(parsed.get("service_hint", "")) if parsed else "",
                "landmark_text": str(parsed.get("landmark_text", "")) if parsed else "",
                "urgency_hint": str(parsed.get("urgency_hint", "")) if parsed else "",
            }
        except (OSError, KeyError, IndexError, ValueError, TypeError, AttributeError) as exc:
            log_event("llm.error", f"Chat backend unavailable: {type(exc).__name__}", level="WARN")
    return None
