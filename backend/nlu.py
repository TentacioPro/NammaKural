"""Tanglish/Tamil phonetic normalization, GIS landmark/GPS resolver, sentiment triage, and Semantic VAD."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Embedded public TN landmark & ArcGIS Ward schema (mirrors live GCC EDPMobile2025 schema)
SERVICE_CATALOG: dict[str, dict[str, Any]] = {
    "streetlight_eb": {
        "id": "streetlight_eb",
        "title_en": "Streetlight & EB",
        "title_ta": "தெருவிளக்கு & EB",
        "photo": "assets/streetlight_eb.jpg",
        "default_coords": (48, 22),
        "agencies": ["GCC PGRS — Streetlight (1913)", "TANGEDCO — Minnagam Wire (1912)"],
        "helpline": "1912",
        "whatsapp": "919498794987",
        "landmarks": [
            {
                "name": "Tower Park Back Side · Vth Ave",
                "district": "Chennai",
                "zone": "Zone 08",
                "ward": "Ward 103",
                "street": "Vth Avenue",
                "road_id": "76370",
                "lat": 13.0850,
                "lon": 80.2101,
            },
            {
                "name": "Anna Arch · IIIrd Ave",
                "district": "Chennai",
                "zone": "Zone 08",
                "ward": "Ward 102",
                "street": "IIIrd Avenue",
                "road_id": "76312",
                "lat": 13.0792,
                "lon": 80.2156,
            },
        ],
    },
    "sewage_pothole": {
        "id": "sewage_pothole",
        "title_en": "Sewage & Pothole",
        "title_ta": "சாக்கடை & சாலை",
        "photo": "assets/sewage_pothole.jpg",
        "default_coords": (52, 62),
        "agencies": ["CMWSSB Metro Water (1916)", "GCC PGRS Roads (1913)"],
        "helpline": "1916",
        "whatsapp": "918144930308",
        "landmarks": [
            {
                "name": "Vijayanagar Bus Stand · Velachery Main Rd",
                "district": "Chennai",
                "zone": "Zone 13",
                "ward": "Ward 178",
                "street": "Velachery Main Rd",
                "road_id": "91420",
                "lat": 12.9792,
                "lon": 80.2212,
            },
            {
                "name": "Phoenix Marketcity · 100 Feet Rd",
                "district": "Chennai",
                "zone": "Zone 13",
                "ward": "Ward 175",
                "street": "Velachery Bypass Rd",
                "road_id": "91105",
                "lat": 12.9915,
                "lon": 80.2167,
            },
        ],
    },
    "water_pipe": {
        "id": "water_pipe",
        "title_en": "Water Pipe Leak",
        "title_ta": "குடிநீர் குழாய் உடைப்பு",
        "photo": "assets/water_pipe_leak.jpg",
        "default_coords": (46, 58),
        "agencies": ["TWAD Board PUNAL (1916)"],
        "helpline": "1916",
        "whatsapp": "919499991916",
        "landmarks": [
            {
                "name": "Kuruvikaran Salai · Anna Bus Stand",
                "district": "Madurai",
                "zone": "Zone II",
                "ward": "Ward 44",
                "street": "Kuruvikaran Salai",
                "road_id": "MD-4402",
                "lat": 9.9312,
                "lon": 78.1342,
            },
            {
                "name": "Gandhipuram 100 Feet Road",
                "district": "Coimbatore",
                "zone": "Central",
                "ward": "Ward 32",
                "street": "100 Feet Road",
                "road_id": "CB-3210",
                "lat": 11.0183,
                "lon": 76.9685,
            },
        ],
    },
    "ration_tnpds": {
        "id": "ration_tnpds",
        "title_en": "Ration Shop Issue",
        "title_ta": "ரேஷன் கடை புகார்",
        "photo": "assets/ration_shop_tnpds.jpg",
        "default_coords": (54, 48),
        "agencies": ["TNPDS Consumer Helpline (1967)"],
        "helpline": "1967",
        "whatsapp": None,
        "landmarks": [
            {
                "name": "TNPDS Shop · Anna Nagar West",
                "district": "Chennai",
                "zone": "Zone 08",
                "ward": "Ward 101",
                "street": "Anna Nagar West Ext",
                "road_id": "TN-PDS-101",
                "lat": 13.0921,
                "lon": 80.1972,
            }
        ],
    },
    "garbage_1100": {
        "id": "garbage_1100",
        "title_en": "False Closure (1100)",
        "title_ta": "தவறான முடிவு (1100)",
        "photo": "assets/garbage_overflow.jpg",
        "default_coords": (42, 65),
        "agencies": ["Mudhalvarin Mugavari — CM Cell (1100)"],
        "helpline": "1100",
        "whatsapp": None,
        "landmarks": [
            {
                "name": "Velachery Main Rd · Vijayanagar",
                "district": "Chennai",
                "zone": "Zone 13",
                "ward": "Ward 178",
                "street": "Velachery Main Rd",
                "road_id": "91420",
                "lat": 12.9792,
                "lon": 80.2212,
            }
        ],
    },
}

_BACKCHANNEL_SET = {
    "ok",
    "okay",
    "mm-hmm",
    "mhm",
    "hmm",
    "seri",
    "aama",
    "aa",
    "right",
    "yes",
    "yep",
    "yeah",
    "got it",
    "sari",
    "சரி",
    "ஆமா",
}
_INTERRUPT_RE = re.compile(
    r"\b(stop|wait|hold on|pause|excuse me|niruthunga|nillunga|maathu|change)\b|நிறுத்து",
    re.IGNORECASE,
)


@dataclass
class UrgencyResult:
    tier: str
    badge_en: str
    badge_ta: str
    action_en: str
    action_ta: str
    prefix: str
    helpline: str | None = None


_EMERGENCY_ROUTES = (
    (r"\b(?:1906|(?:lpg |cooking )?gas leak(?:ing)?|gas kasivu)\b|எரிவாயு கசிவு|கேஸ் கசிவு", "1906"),
    (r"\b(?:101|fire|on fire|thee pidich\w*)\b|தீப்பிடி|தீ பிடி|தீ விபத்து", "101"),
    (r"\b(?:108|ambulance|heart attack|unconscious)\b|ஆம்புலன்ஸ்|மயங்கி|மாரடைப்பு", "108"),
    (r"\b(?:112|electrocut(?:ed|ion|ing)|life.threatening)\b|மின்சாரம் தாக்கி|உயிருக்கு ஆபத்து", "112"),
)


def life_safety_helpline(text: str) -> str | None:
    numbers = [number for pattern, number in _EMERGENCY_ROUTES if re.search(pattern, text, re.IGNORECASE)]
    return "112" if len(numbers) > 1 else next(iter(numbers), None)


def classify_sentiment_urgency(text: str) -> UrgencyResult:
    """Classify urgency and emotional register from code-mixed Tanglish/Tamil text."""
    if number := life_safety_helpline(text):
        return UrgencyResult(
            tier="LIFE_SAFETY",
            badge_en="P0 Life Safety",
            badge_ta="உயிருக்கு ஆபத்து",
            action_en=f"Call {number} now for emergency help.",
            action_ta=f"அவசர உதவிக்கு உடனே {number} எண்ணை அழையுங்க.",
            prefix="[P0 LIFE SAFETY] ",
            helpline=number,
        )
    if re.search(
        r"(spark|fire|shock|live\s*wire|current|smoke|danger|explode|manhole|flood|child)",
        text,
        re.IGNORECASE,
    ):
        return UrgencyResult(
            tier="CRITICAL_SAFETY",
            badge_en="P1 Critical Safety · Urgent Hazard",
            badge_ta="P1 அவசர பாதுகாப்பு எச்சரிக்கை",
            action_en="Live electrical/safety risk detected -> Prioritizing TANGEDCO 1912 emergency dial + GCC split.",
            action_ta="உடனடி மின்/பாதுகாப்பு ஆபத்து -> TANGEDCO 1912 அவசர அழைப்பு முன்னுரிமை.",
            prefix="[P1 CRITICAL SAFETY HAZARD] ",
        )
    if re.search(
        r"(close|reopen|1100|20491|fix\s*pannama|again|5\s*naal|days|week|month|varala|fraud|complaint)",
        text,
        re.IGNORECASE,
    ):
        return UrgencyResult(
            tier="HIGH_ESCALATION",
            badge_en="P2 High Urgency · Frustrated / Chronic",
            badge_ta="P2 அதிக அவசரம் · தொடர் புறக்கணிப்பு",
            action_en="Multi-day delay / false closure detected -> Escalation tone enabled (+ CM Cell 1100 option).",
            action_ta="பல நாள் தாமதம் / தவறான முடிவு -> 1100 மேல்முறையீட்டுத் தொனி சேர்க்கப்பட்டது.",
            prefix="[P2 CHRONIC / ESCALATION] ",
        )
    return UrgencyResult(
        tier="STANDARD",
        badge_en="P3 Standard Civic Request",
        badge_ta="P3 சாதாரண மக்கள் புகார்",
        action_en="Clear civic service outage -> Routed cleanly to official no-login / WhatsApp queue.",
        action_ta="தெளிவான தெருப் பிரச்சனை -> சரியான துறை வாட்ஸ்அப் வரிசைக்கு மாற்றப்பட்டது.",
        prefix="",
    )


def classify_semantic_vad(transcript: str, assistant_speaking: bool = False) -> dict[str, Any]:
    """Distinguish backchannels & street bystander chatter from real interruption turns."""
    cleaned = re.sub(r"[^\w\s\u0B80-\u0BFF-]", "", transcript.strip().lower())
    words = [w for w in cleaned.split() if w]
    if _INTERRUPT_RE.search(cleaned):
        return {
            "action": "interrupt",
            "reason": "explicit_stop_cue",
            "truncate_audio": True,
        }
    if assistant_speaking and (cleaned in _BACKCHANNEL_SET or len(words) < 3):
        return {
            "action": "not_turn",
            "reason": "backchannel_or_short_bystander_noise",
            "truncate_audio": False,
        }
    return {
        "action": "process_turn",
        "reason": "complete_citizen_utterance",
        "truncate_audio": assistant_speaking,
    }


def resolve_gps_to_landmark(lat: float, lon: float) -> dict[str, Any]:
    """Find nearest verified civic landmark and Ward within Tamil Nadu boundaries."""
    best_dist = float("inf")
    best_lm = SERVICE_CATALOG["streetlight_eb"]["landmarks"][0]
    best_svc = "streetlight_eb"
    for svc_id, svc in SERVICE_CATALOG.items():
        for lm in svc["landmarks"]:
            dist = (lm["lat"] - lat) ** 2 + (lm["lon"] - lon) ** 2
            if dist < best_dist:
                best_dist = dist
                best_lm = lm
                best_svc = svc_id
    return {"service_id": best_svc, "landmark": best_lm, "distance_deg": round(best_dist, 5)}


_CHAT_GREETING_RE = re.compile(
    r"^(\s*((hello|hi|hey|vanakkam|namaste|ஹலோ|வணக்கம்)[\s,!?.]*)+)$|(கேக்குதா|கேட்கிறதா|kekutha|kekudha|hear me|mic test|listening)",
    re.IGNORECASE,
)
_CHAT_HELP_RE = re.compile(
    r"(how (does|do) (this|it|you) work|what can you do|என்ன செய்ய|எப்படி பயன்படுத்து|guide)",
    re.IGNORECASE,
)
_ATTACH_MENTION_RE = re.compile(
    r"(attach|upload|photo|picture|image|bill|receipt|screenshot|புகைப்படம்|படம்|ரசீது|பில்)",
    re.IGNORECASE,
)


def classify_conversational_chitchat(text: str) -> dict[str, Any] | None:
    """Respond naturally to greetings, mic checks, and how-to questions without repeating ticket summaries."""
    cleaned = text.strip()
    if _CHAT_GREETING_RE.search(cleaned):
        return {
            "kind": "greeting_or_mic_check",
            "reply_en": "Yes, I hear you clearly! Tell me your street problem and landmark in Tanglish or Tamil.",
            "reply_tanglish": "Ama, nalla kekudhu! Ungal street problem-a yum landmark-a yum sollunga.",
            "reply_ta": "வணக்கம், நன்றாகக் கேட்கிறது! உங்கள் தெருப் பிரச்சனையையும் பகுதியையும் சொல்லுங்கள்.",
        }
    if _CHAT_HELP_RE.search(cleaned):
        return {
            "kind": "help",
            "reply_en": "Just tell me what broke on your street and where. I will detect urgency, verify your Ward, and wait for your confirmation before sending.",
            "reply_tanglish": "Ungal theru problem-um landmark-um sollunga podhum; Ward check panni confirm ketutu send panren.",
            "reply_ta": "உங்கள் தெருப் பிரச்சனையையும் இடத்தையும் சொன்னால் போதும்; வார்டு கண்டறிந்து உங்கள் அனுமதியுடன் புகார் அனுப்புவேன்.",
        }
    return None


def resolve_explicit_place(txt: str) -> dict[str, Any] | None:
    """Resolve spoken TN landmark independently of the civic issue category."""
    if re.search(r"(tower\s*park|5th\s*ave|vth\s*ave|3rd\s*cross)", txt):
        return SERVICE_CATALOG["streetlight_eb"]["landmarks"][0]
    if re.search(r"(anna\s*arch|iii(rd)?\s*ave)", txt):
        return SERVICE_CATALOG["streetlight_eb"]["landmarks"][1]
    if re.search(r"(vijaya\s*nagar|velachery\s*main)", txt):
        return SERVICE_CATALOG["sewage_pothole"]["landmarks"][0]
    if "phoenix" in txt:
        return SERVICE_CATALOG["sewage_pothole"]["landmarks"][1]
    if re.search(r"(madurai|kuruvikaran|anna\s*bus\s*stand|மதுரை)", txt):
        return SERVICE_CATALOG["water_pipe"]["landmarks"][0]
    if re.search(r"(coimbatore|gandhipuram|கோவை)", txt):
        return SERVICE_CATALOG["water_pipe"]["landmarks"][1]
    return None


def analyze_turn(combined_text: str, gps_landmark: dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize Tanglish/Tamil utterance, detect missing slots or multi-ward ambiguity."""
    txt = combined_text.lower()
    place_re = re.compile(
        r"(anna\s*nagar|tower\s*park|arch|velachery|vijaya\s*nagar|phoenix|madurai|kuruvikaran|coimbatore|gandhipuram|100\s*feet|அண்ணா|வேளச்சேரி|மதுரை|கோவை)"
    )
    issue_re = re.compile(
        r"(streetlight|light|eriyala|wire|transformer|spark|sewage|saakkadai|pothole|water|kudineer|pipe|ration|arisi|fingerprint|garbage|kuppai|close|20491|1100|தெருவிளக்கு|சாக்கடை|குடிநீர்|ரேஷன்|குப்பை)"
    )

    has_place = bool(place_re.search(txt)) or gps_landmark is not None
    has_issue = bool(issue_re.search(txt))

    has_velachery_broad = bool(re.search(r"\bvelachery\b|வேளச்சேரி", txt)) and not bool(
        re.search(r"(vijaya\s*nagar|phoenix|bus\s*stand|20491|close|garbage|kuppai)", txt)
    )
    has_anna_broad = bool(re.search(r"\banna\s*nagar\b|அண்ணா", txt)) and not bool(
        re.search(r"(tower\s*park|arch|5th|3rd|iii)", txt)
    )

    svc_id = "streetlight_eb"
    if any(k in txt for k in ("close", "20491", "1100")):
        svc_id = "garbage_1100"
    elif any(k in txt for k in ("ration", "arisi", "fingerprint", "ரேஷன்")):
        svc_id = "ration_tnpds"
    elif any(k in txt for k in ("madurai", "kudineer", "pipe", "குடிநீர்")):
        svc_id = "water_pipe"
    elif any(k in txt for k in ("velachery", "saakkadai", "sewage", "pothole", "சாக்கடை")):
        svc_id = "sewage_pothole"

    ticket_m = re.search(r"#?[A-Z]{2,5}-?\d{4,6}", combined_text, re.IGNORECASE)
    ticket_ref = ticket_m.group(0).upper() if ticket_m else "#GCC-20491"
    if not ticket_ref.startswith("#"):
        ticket_ref = "#" + ticket_ref

    ambiguous_area = None
    if gps_landmark is None:
        if has_velachery_broad:
            ambiguous_area = "velachery"
        elif has_anna_broad:
            ambiguous_area = "anna_nagar"

    svc = SERVICE_CATALOG[svc_id]
    lm_idx = 1 if ("phoenix" in txt or "arch" in txt or "coimbatore" in txt) else 0
    explicit_lm = resolve_explicit_place(txt)
    lm = gps_landmark or explicit_lm or svc["landmarks"][min(lm_idx, len(svc["landmarks"]) - 1)]
    urgency = classify_sentiment_urgency(combined_text)
    has_issue = has_issue or urgency.tier == "LIFE_SAFETY"

    wants_attachment = bool(_ATTACH_MENTION_RE.search(txt))

    return {
        "has_place": has_place,
        "has_issue": has_issue,
        "ambiguous_area": ambiguous_area,
        "wants_attachment": wants_attachment,
        "service_id": svc_id,
        "landmark_idx": lm_idx,
        "landmark": lm,
        "ticket_ref": ticket_ref,
        "urgency": urgency.__dict__,
    }
