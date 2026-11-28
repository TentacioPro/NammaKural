"""Conservative, provider-independent speech text utilities for voice v1.

These primitives intentionally avoid claims of general Tamil transliteration,
NER, or semantic understanding. Unknown text is preserved rather than guessed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Mapping


# Small, reviewed phrase-level map: this is not a general Tanglish transliterator.
_TAMIL_LEXICON = {
    "vanakkam": "வணக்கம்", "nandri": "நன்றி", "aama": "ஆமாம்",
    "illa": "இல்லை", "illai": "இல்லை", "seri": "சரி",
    "theriyala": "தெரியல", "sollunga": "சொல்லுங்கள்", "unga": "உங்கள்",
    "streetlight": "தெருவிளக்கு", "eriyala": "எரியல", "pannunga": "பண்ணுங்கள்",
}
_EXPANSIONS = {
    "otp": "ஓடிபி", "sms": "எஸ்எம்எஸ்", "ஏடிஎம்": "ஏடிஎம்",
}
_MARKDOWN = re.compile(r"```.*?```|`([^`]*)`|!?\[([^\]]*)\]\([^)]*\)|[*_~>#]+", re.S)
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_TOKEN = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*|[^\s]", re.UNICODE)


@dataclass(frozen=True)
class SpeechProvenance:
    raw_text: str
    final_text: str
    normalized_text: str
    candidate_text: str
    validated_text: str
    provider: str = "deterministic"
    locale: str = "ta-IN"
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SpeechOutput:
    display_text: str
    tts_text: str
    register: str
    voice_locale: str
    speaking_rate: float
    provenance: SpeechProvenance


def strip_markup(text: str) -> str:
    """Remove common markdown and control characters; retain visible label text."""
    text = _MARKDOWN.sub(lambda m: m.group(1) or m.group(2) or " ", text)
    text = _CONTROL.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_tts_text(text: str, *, expansions: Mapping[str, str] | None = None,
                       pronunciation_lexicon: Mapping[str, str] | None = None) -> str:
    """Normalize known tokens only; unknown Roman words remain unchanged."""
    lex = {**_TAMIL_LEXICON, **(pronunciation_lexicon or {})}
    exp = {**_EXPANSIONS, **(expansions or {})}
    clean = strip_markup(text)
    def convert(match: re.Match[str]) -> str:
        token = match.group(0)
        if token.casefold() in lex:
            return lex[token.casefold()]
        return exp.get(token.casefold(), exp.get(token, token))
    return _TOKEN.sub(convert, clean)


def build_speech_output(text: str, *, register: str = "conversational",
                        locale: str = "ta-IN", provider: str = "deterministic",
                        final_text: str | None = None, critical_readback: bool = False,
                        consented: bool = True, privacy_allowed: bool = True,
                        pronunciation_lexicon: Mapping[str, str] | None = None) -> SpeechOutput:
    """Create the two registers and guarded TTS text. en-IN is never spoken as Tamil."""
    if register not in {"conversational", "formal"}:
        raise ValueError("register must be conversational or formal")
    clean = strip_markup(text)
    source = strip_markup(final_text if final_text is not None else text)
    candidate = normalize_tts_text(source, pronunciation_lexicon=pronunciation_lexicon)
    notes: list[str] = []
    if locale.lower() == "en-in":
        # No silent locale substitution or potentially incorrect Tamil rendering.
        validated, actual_locale = source, "en-IN"
        notes.append("locale_guard_en_in")
    elif locale.lower() != "ta-in":
        validated, actual_locale = source, locale
        notes.append("unsupported_locale_preserved")
    else:
        validated, actual_locale = candidate, "ta-IN"
    if not consented or not privacy_allowed:
        validated = ""
        notes.append("speech_blocked_without_consent_or_privacy_approval")
    # Display remains accessible and separate; formal register is a label/policy choice,
    # not an unsafe automatic paraphrase of the user's meaning.
    display = clean
    rate = 0.75 if critical_readback else 1.0
    provenance = SpeechProvenance(raw_text=text, final_text=source,
        normalized_text=normalize_tts_text(clean, pronunciation_lexicon=pronunciation_lexicon),
        candidate_text=candidate, validated_text=validated, provider=provider,
        locale=actual_locale, notes=tuple(notes))
    return SpeechOutput(display, validated, register, actual_locale, rate, provenance)


_PROTECTED_WORDS = re.compile(r"\b(?:illa|illai|no|not|yes|consent|agree)\b", re.I)
_PROTECTED_AMOUNT = re.compile(r"(?:₹|\bINR\s*)\s*\d[\d,.]*", re.I)
_PROTECTED_ID = re.compile(r"\b(?:[A-Z]{2,}\d+|[A-Z][a-z]{2,})\b")


@dataclass
class PhoneticRepairPack:
    """Opt-in, versioned exact substitutions scoped to a state pack."""
    pack_id: str
    version: str
    replacements: Mapping[str, str] = field(default_factory=dict)

    def repair(self, text: str, *, pack_id: str, version: str) -> str:
        if pack_id != self.pack_id or version != self.version:
            return text
        # Fail closed on a whole utterance containing potentially protected content.
        if _PROTECTED_WORDS.search(text) or _PROTECTED_AMOUNT.search(text) or _PROTECTED_ID.search(text):
            return text
        return self.replacements.get(text, text)
