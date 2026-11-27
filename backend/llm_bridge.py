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
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

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
    val = os.getenv(name, "").strip()
    if val:
        return val
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
    if override and override in models:
        return override
    # Exclude STT/TTS/embed utilities and non-compliant model families (Bharat sovereign/open-weight policy)
    disallowed = ("asr", "whisper", "tts", "embed", "qwen", "deepseek")
    chat_candidates = [m for m in models if not any(tok in m.lower() for tok in disallowed)]
    if not chat_candidates:
        chat_candidates = [m for m in models if not any(tok in m.lower() for tok in ("asr", "whisper", "tts", "embed"))]
    if not chat_candidates:
        return models[0] if models else ""
    for preferred in ("gemma-4", "nemotron", "phi-4", "sarvam", "llama"):
        for m in chat_candidates:
            if preferred in m.lower():
                return m
    return chat_candidates[0]


def probe_local_llm() -> dict[str, Any]:
    """Detect running local Unsloth Studio or Ollama endpoints without exposing any secret keys."""
    unsloth_url = _read_env_value("UNSLOTH_STUDIO_URL", "http://127.0.0.1:8888").rstrip("/")
    unsloth_key = _read_env_value("UNSLOTH_API_KEY", "")
    model_override = _read_env_value("LOCAL_LLM_MODEL", "")

    if unsloth_url and unsloth_key:
        try:
            req = urllib.request.Request(
                f"{unsloth_url}/v1/models",
                headers={"Authorization": f"Bearer {unsloth_key}"},
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [str(m.get("id", "")) for m in data.get("data", []) if m.get("id")]
                if models:
                    return {
                        "available": True,
                        "provider": "unsloth-studio",
                        "active_model": _pick_chat_model(models, model_override),
                        "models": models,
                    }
        except Exception:
            pass

    ollama_url = _read_env_value("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    try:
        with urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=1.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [str(m.get("name", "")) for m in data.get("models", []) if m.get("name")]
            if models:
                return {
                    "available": True,
                    "provider": "ollama",
                    "active_model": _pick_chat_model(models, model_override),
                    "models": models,
                }
    except Exception:
        pass

    return {
        "available": False,
        "provider": "offline-tanglish-engine",
        "active_model": "deterministic-tanglish-v1",
        "models": [],
    }


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

    status = probe_local_llm()
    if not status["available"] or not status["active_model"]:
        return None

    if preferred_mode == "ollama" and status["provider"] != "ollama":
        return None

    unsloth_url = _read_env_value("UNSLOTH_STUDIO_URL", "http://127.0.0.1:8888").rstrip("/")
    unsloth_key = _read_env_value("UNSLOTH_API_KEY", "")
    ollama_url = _read_env_value("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")

    messages: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for item in (history or [])[-4:]:
        role = "assistant" if item.get("role") == "agent" else "user"
        txt = str(item.get("text", "")).strip()
        if txt:
            messages.append({"role": role, "content": txt})

    lang_hint = "Tamil script (தமிழ்)" if lang == "ta" else "natural Tanglish or English"
    user_msg = (
        f"Preferred language: {lang_hint}\n"
        f"Context so far: {combined_text}\n"
        f"Latest user speech: {utterance}"
    )
    messages.append({"role": "user", "content": user_msg})

    endpoint = (
        f"{unsloth_url}/v1/chat/completions"
        if status["provider"] == "unsloth-studio"
        else f"{ollama_url}/v1/chat/completions"
    )
    headers = {"Content-Type": "application/json"}
    if status["provider"] == "unsloth-studio" and unsloth_key:
        headers["Authorization"] = f"Bearer {unsloth_key}"

    payload = json.dumps(
        {
            "model": status["active_model"],
            "messages": messages,
            "max_tokens": 360,
            "temperature": 0.25,
        }
    ).encode("utf-8")

    try:
        req = urllib.request.Request(endpoint, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            content = str(body["choices"][0]["message"].get("content", "")).strip()
            if not content:
                return None
            parsed = _extract_json_object(content)
            reply = str(parsed.get("reply", "")).strip() if parsed else content
            return {
                "used": True,
                "provider": status["provider"],
                "model": status["active_model"],
                "reply": reply,
                "service_hint": str(parsed.get("service_hint", "")) if parsed else "",
                "landmark_text": str(parsed.get("landmark_text", "")) if parsed else "",
                "urgency_hint": str(parsed.get("urgency_hint", "")) if parsed else "",
            }
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError):
        return None
