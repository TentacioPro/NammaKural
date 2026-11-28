from backend.voice_v1.speech.pipeline import (
    PhoneticRepairPack,
    build_speech_output,
    normalize_tts_text,
    strip_markup,
)


def test_markdown_controls_removed_and_known_tanglish_uses_tamil_script():
    assert strip_markup("**vanakkam**\x00 [help](https://example.test)") == "vanakkam help"
    assert normalize_tts_text("vanakkam, streetlight eriyala") == "வணக்கம், தெருவிளக்கு எரியல"
    # Unknown Roman text is not guessed or blindly transliterated.
    assert normalize_tts_text("Anna Nagar") == "Anna Nagar"


def test_output_keeps_two_register_channels_and_provenance():
    out = build_speech_output("**vanakkam**", register="formal", provider="fixture")
    assert out.display_text == "vanakkam"
    assert out.tts_text == "வணக்கம்"
    assert out.register == "formal"
    p = out.provenance
    assert (p.raw_text, p.final_text, p.normalized_text, p.candidate_text, p.validated_text) == (
        "**vanakkam**", "vanakkam", "வணக்கம்", "வணக்கம்", "வணக்கம்")
    assert p.provider == "fixture"


def test_locale_guard_and_critical_slow_readback():
    english = build_speech_output("vanakkam", locale="en-IN")
    assert english.tts_text == "vanakkam"
    assert english.voice_locale == "en-IN"
    assert "locale_guard_en_in" in english.provenance.notes
    critical = build_speech_output("உங்கள் முகவரி", critical_readback=True)
    assert critical.speaking_rate == 0.75


def test_privacy_and_consent_fail_closed_for_tts():
    assert build_speech_output("உங்கள் பெயர்", consented=False).tts_text == ""
    assert build_speech_output("உங்கள் பெயர்", privacy_allowed=False).tts_text == ""


def test_scoped_versioned_repair_fails_closed_on_protected_content():
    pack = PhoneticRepairPack("tn", "3", {"nagar": "நகர்"})
    assert pack.repair("nagar", pack_id="tn", version="3") == "நகர்"
    assert pack.repair("nagar", pack_id="ka", version="3") == "nagar"
    assert pack.repair("nagar", pack_id="tn", version="2") == "nagar"
    for utterance in ("illa", "I do not agree", "consent", "₹500", "Ravi", "AB123"):
        assert pack.repair(utterance, pack_id="tn", version="3") == utterance
