"""Sarvam Saaras v4 Realtime Streaming STT & Bulbul TTS adapters with dynamic call-state keyterms."""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
from typing import Any

from backend.logger import log_event
from backend.state_packs import REGISTRY


def get_dynamic_keyterms(state_code: str = "tn", locality_hint: str = "") -> list[str]:
    """Return call-state-dependent landmark/civic keyterms (Venky B §2: boost active locality, not whole state)."""
    pack = REGISTRY.get(state_code)
    hint = locality_hint.lower().strip()
    terms: list[str] = []
    for lm in pack.landmarks:
        hay = f"{lm.name} {lm.district} {' '.join(lm.aliases)}".lower()
        if not hint or hint in hay:
            terms.extend(lm.aliases[:3])
    # Always include core civic confirmation & interruption cues
    for core in ("streetlight", "urudhi", "confirm", "niruthunga", "illa"):
        if core not in terms:
            terms.append(core)
    return terms[:25]


def synthesize_bulbul_sync(text: str, speaker: str = "anushka", pace: float = 1.06) -> dict[str, Any]:
    """Synthesize Tamil/Tanglish speech via Sarvam Bulbul streaming-ready REST endpoint."""
    sarvam_key = os.getenv("SARVAM_API_KEY", "").strip()
    if not sarvam_key or not text.strip():
        return {"ok": False, "audio": b"", "provider": "sarvam-bulbul-unavailable"}

    t0 = time.monotonic()
    payload = json.dumps(
        {
            "inputs": [text[:490]],
            "target_language_code": "ta-IN",
            "speaker": speaker,
            "pace": pace,
            "speech_sample_rate": 16000,
            "enable_preprocessing": True,
            "model": "bulbul:v2",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.sarvam.ai/text-to-speech",
        data=payload,
        headers={
            "api-subscription-key": sarvam_key,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            audios = body.get("audios") or []
            if not audios:
                return {"ok": False, "audio": b"", "provider": "sarvam-bulbul-empty"}
            raw_wav = base64.b64decode(audios[0])
            latency_ms = round((time.monotonic() - t0) * 1000, 1)
            log_event("tts.sarvam_bulbul", text[:60], {"bytes": len(raw_wav), "latency_ms": latency_ms, "speaker": speaker})
            return {"ok": True, "audio": raw_wav, "media_type": "audio/wav", "voice": f"sarvam-{speaker}", "latency_ms": latency_ms}
    except Exception as exc:
        log_event("tts.sarvam_bulbul_error", type(exc).__name__, level="WARN")
        return {"ok": False, "audio": b"", "provider": "sarvam-bulbul-error"}
