"""Zero-Key Neural Tamil & Indian-English TTS Service (edge-tts + optional Sarvam Bulbul).

Replaces robotic desktop SpeechSynthesis with neural `ta-IN-PallaviNeural`, `ta-IN-ValluvarNeural`,
`en-IN-NeerjaNeural`, and `en-IN-PrabhatNeural` voices, backed by an in-memory LRU cache so
repeated greetings/HITL prompts play in <2ms.
"""

from __future__ import annotations

import re
import time
from collections import OrderedDict
from typing import Any

from backend.logger import log_event

VOICE_CATALOG: dict[str, dict[str, str]] = {
    "ta-IN-PallaviNeural": {"label": "Pallavi · Tamil Nadu (Female Neural)", "lang": "ta-IN"},
    "ta-IN-ValluvarNeural": {"label": "Valluvar · Tamil Nadu (Male Neural)", "lang": "ta-IN"},
    "en-IN-NeerjaNeural": {"label": "Neerja · Indian English (Female Neural)", "lang": "en-IN"},
    "en-IN-PrabhatNeural": {"label": "Prabhat · Indian English (Male Neural)", "lang": "en-IN"},
}

_TTS_CACHE: OrderedDict[tuple[str, str], bytes] = OrderedDict()
_MAX_CACHE_ITEMS = 64


def select_neural_voice(text: str, preferred_voice: str = "auto", lang: str = "en") -> str:
    if preferred_voice in VOICE_CATALOG:
        return preferred_voice
    has_tamil_script = bool(re.search(r"[\u0B80-\u0BFF]", text))
    if has_tamil_script or lang == "ta":
        return "ta-IN-PallaviNeural"
    return "en-IN-NeerjaNeural"


async def synthesize_neural_mp3(
    text: str,
    preferred_voice: str = "auto",
    lang: str = "en",
) -> dict[str, Any]:
    """Synthesize spoken MP3 bytes using free zero-key edge-tts neural voices with LRU cache."""
    clean_text = re.sub(r"[`*_#>\[\]]", "", text).strip()
    if not clean_text:
        return {"ok": False, "voice": "", "audio": b""}

    voice = select_neural_voice(clean_text, preferred_voice, lang)
    cache_key = (voice, clean_text)
    if cache_key in _TTS_CACHE:
        _TTS_CACHE.move_to_end(cache_key)
        log_event("tts.cache_hit", clean_text[:60], {"voice": voice, "bytes": len(_TTS_CACHE[cache_key])})
        return {"ok": True, "voice": voice, "audio": _TTS_CACHE[cache_key], "cached": True}

    t0 = time.time()
    try:
        import edge_tts

        communicate = edge_tts.Communicate(clean_text, voice)
        chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                chunks.append(chunk["data"])
        audio_bytes = b"".join(chunks)
        if not audio_bytes:
            return {"ok": False, "voice": voice, "audio": b""}

        _TTS_CACHE[cache_key] = audio_bytes
        if len(_TTS_CACHE) > _MAX_CACHE_ITEMS:
            _TTS_CACHE.popitem(last=False)

        log_event(
            "tts.neural_synth",
            clean_text[:60],
            {"voice": voice, "bytes": len(audio_bytes), "latency_ms": round((time.time() - t0) * 1000, 1)},
        )
        return {"ok": True, "voice": voice, "audio": audio_bytes, "cached": False}
    except Exception as exc:
        log_event("tts.fallback_browser", f"Neural TTS unavailable ({type(exc).__name__}); browser fallback", {"voice": voice}, level="WARN")
        return {"ok": False, "voice": voice, "audio": b""}
