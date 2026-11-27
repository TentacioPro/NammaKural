"""Zero-Key Neural Tamil (India/SG/MY/LK) & Indian-English TTS Service (edge-tts + LRU cache).

Includes native Tamil Nadu voices (`ta-IN-PallaviNeural`, `ta-IN-ValluvarNeural`), Tamil diaspora
accents (`ta-SG-*`, `ta-MY-*`, `ta-LK-*`), and Indian-English voices (`en-IN-*`), with strict
guarding so `en-IN-*` voices never receive raw Tamil Unicode (which triggers NoAudioReceived).
"""

from __future__ import annotations

import re
import time
from collections import OrderedDict
from typing import Any

from backend.logger import log_event

VOICE_CATALOG: dict[str, dict[str, str]] = {
    "ta-IN-PallaviNeural": {"name": "Pallavi", "label": "Pallavi · Tamil Nadu தமிழ் (Female)", "lang": "ta-IN"},
    "ta-IN-ValluvarNeural": {"name": "Valluvar", "label": "Valluvar · Tamil Nadu தமிழ் (Male)", "lang": "ta-IN"},
    "ta-SG-VenbaNeural": {"name": "Venba", "label": "Venba · Singapore தமிழ் (Female)", "lang": "ta-SG"},
    "ta-SG-AnbuNeural": {"name": "Anbu", "label": "Anbu · Singapore தமிழ் (Male)", "lang": "ta-SG"},
    "ta-MY-KaniNeural": {"name": "Kani", "label": "Kani · Malaysia தமிழ் (Female)", "lang": "ta-MY"},
    "ta-MY-SuryaNeural": {"name": "Surya", "label": "Surya · Malaysia தமிழ் (Male)", "lang": "ta-MY"},
    "ta-LK-SaranyaNeural": {"name": "Saranya", "label": "Saranya · Sri Lanka தமிழ் (Female)", "lang": "ta-LK"},
    "ta-LK-KumarNeural": {"name": "Kumar", "label": "Kumar · Sri Lanka தமிழ் (Male)", "lang": "ta-LK"},
    "en-IN-PrabhatNeural": {"name": "Prabhat", "label": "Prabhat · Indian EN Only (Male)", "lang": "en-IN"},
    "en-IN-NeerjaExpressiveNeural": {"name": "Neerja+", "label": "Neerja Expressive · Indian EN Only (Female)", "lang": "en-IN"},
    "en-IN-NeerjaNeural": {"name": "Neerja", "label": "Neerja · Indian EN Only (Female)", "lang": "en-IN"},
}

_TTS_CACHE: OrderedDict[tuple[str, str], bytes] = OrderedDict()
_MAX_CACHE_ITEMS = 96


def _has_tamil_script(text: str) -> bool:
    return bool(re.search(r"[\u0B80-\u0BFF]", text))


_TA_TTS_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"\bstreet-ல\b|\bstreet-la\b|\bstreet\b", "தெரு"),
    (r"\barea-னு\b|\barea-nu\b", "ஏரியானு"),
    (r"\barea-ல\b|\barea-la\b|\barea\b", "ஏரியா"),
    (r"\bproblem\b|\bissue\b|\btrouble\b", "பிரச்சனை"),
    (r"\bstreetlight\b", "ஸ்ட்ரீட் லைட்"),
    (r"\blight\b", "லைட்"),
    (r"\bwater\b", "தண்ணி"),
    (r"\bpipe\b", "பைப்"),
    (r"\bWard\b", "வார்டு"),
    (r"\bOTP\b", "ஓடிபி"),
    (r"\bGPS\b", "ஜிபிஎஸ்"),
    (r"\bneighborhood\b", "பகுதி"),
    (r"\bhelpful\b", "உதவியா"),
    (r"\bhelp\b", "ஹெல்ப்"),
    (r"\bperson\b", "நபர்"),
    (r"\bConfirm\b", "உறுதி"),
    (r"\bClarity Popup\b", "சரிபார்ப்புப் பெட்டி"),
    (r"\bbus\s+stand\b", "பஸ் ஸ்டாண்ட்"),
    (r"\broad\b", "ரோடு"),
    (r"\bbill\b", "பில்"),
    (r"\bphoto\b", "போட்டோ"),
    (r"\bphone\b", "போன்"),
    (r"\bcall\b", "கால்"),
    (r"\bcheck\b", "செக்"),
    (r"\bnumber\b", "நம்பர்"),
    (r"\bcivic\b", "சிவிக்"),
    (r"\bvoice\b", "வாய்ஸ்"),
    (r"\bassistant\b", "அசிஸ்டென்ட்"),
    (r"\brelated\b", "ரிலேட்டட்"),
    (r"\bdrainage\b", "சாக்கடை"),
    (r"\bgarbage\b", "குப்பை"),
    (r"\bcurrent\b", "கரண்ட்"),
    (r"\bpower\b", "பவர்"),
    (r"\bAI\b", "ஏ ஐ"),
    (r"\bNammaKural\b", "நம்ம குரல்"),
)


def _normalize_tamil_tts(text: str, voice: str) -> str:
    """Convert common English/Tanglish nouns to Tamil phonetics for Tamil neural voices."""
    if not voice.startswith("ta-"):
        return text
    out = text
    for pattern, tamil in _TA_TTS_REPLACEMENTS:
        out = re.sub(pattern, tamil, out, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", out).strip()


def select_neural_voice(text: str, preferred_voice: str = "auto", lang: str = "tanglish") -> str:
    has_ta = _has_tamil_script(text)
    if preferred_voice in VOICE_CATALOG:
        # Never pass raw Tamil Unicode to en-IN voices (edge-tts returns NoAudioReceived)
        if preferred_voice.startswith("en-IN") and has_ta:
            return "ta-IN-ValluvarNeural" if "Prabhat" in preferred_voice else "ta-IN-PallaviNeural"
        return preferred_voice
    if has_ta or lang in ("ta", "tanglish"):
        return "ta-IN-PallaviNeural"
    return "en-IN-PrabhatNeural"


async def synthesize_neural_mp3(
    text: str,
    preferred_voice: str = "auto",
    lang: str = "tanglish",
) -> dict[str, Any]:
    """Synthesize spoken MP3 bytes using free zero-key edge-tts neural voices with LRU cache."""
    clean_text = re.sub(r"[`*_#>\[\]]", "", text).strip()
    if not clean_text:
        return {"ok": False, "voice": "", "audio": b""}

    voice = select_neural_voice(clean_text, preferred_voice, lang)
    tts_input = _normalize_tamil_tts(clean_text, voice)
    cache_key = (voice, tts_input)
    if cache_key in _TTS_CACHE:
        _TTS_CACHE.move_to_end(cache_key)
        log_event("tts.cache_hit", tts_input[:60], {"voice": voice, "bytes": len(_TTS_CACHE[cache_key])})
        return {"ok": True, "voice": voice, "audio": _TTS_CACHE[cache_key], "cached": True}

    t0 = time.time()
    try:
        import edge_tts

        communicate = edge_tts.Communicate(tts_input, voice, rate="+6%")
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
