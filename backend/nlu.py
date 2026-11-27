"""Tanglish/Tamil phonetic normalization, GIS landmark/GPS resolver, sentiment triage, and Semantic VAD."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from backend.state_packs import REGISTRY

TN_FIXTURE_MAX_DISTANCE_SQUARED = 0.001 ** 2

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
        r"(spark|fire|shock|live\s*wire|smoke|danger|explode|manhole|flood|child|"
        r"கரண்ட் அடிக்|மின் கம்பி.{0,18}(தீப்பொறி|அறுந்த)|தீப்பொறி)",
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
    if assistant_speaking and not life_safety_helpline(cleaned) and (
        cleaned in _BACKCHANNEL_SET or len(words) < 3 or all(word in _BACKCHANNEL_SET for word in words)
    ):
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
    return {"service_id": best_svc, "landmark": best_lm, "distance_deg": round(best_dist, 5),
            "verified": best_dist <= TN_FIXTURE_MAX_DISTANCE_SQUARED}


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


_ISSUE_PATTERNS = {
    "garbage_1100": r"\b(?:garbage|kuppai|close[ds]?|20491|1100)\b|குப்பை|மூடிட்டாங்க",
    "ration_tnpds": r"\b(?:ration|arisi|fingerprint|tnpds)\b|ரே[ஷச]ன்|விரல்ரேகை",
    "sewage_pothole": r"\b(?:sewage|sa+kka?dai|sa?kaadai|sakadai|potholes?|drainage)\b|சாக்கட|போ[த்]*தோல்|பாட்ஹோல்",
    "water_pipe": r"\b(?:kudineer|water|pipes?|tha+nni|thanniir)\b|குடிநீர்|தண்ண[ீி]|தண்ணி|வாட்ட[ர்]+|பை[ப்]+|குழாய்",
    "streetlight_eb": r"\b(?:street\s*lights?|lights?|eriyal[ae]?|wire|transformer|spark|current|karant|kambam|theru\s*vilakku)\b|தெரு\s*விளக்கு|லை[ட்]+|கரண்[ட்]+|மின்\s*கம்பி|எரியல|பொடல|தீப்பொறி",
}
_ISSUES = [(service, re.compile(pattern)) for service, pattern in _ISSUE_PATTERNS.items()]
_ROAD_DEFECT = re.compile(r"(?:ரோட|சாலை|\broad\b).{0,20}(?:குழி|உடை|மோசம்|gundu|kuzhi|damag)")
_VERIFIED_PLACES = [
    ("streetlight_eb", 0, r"\btower\s*(?:park|paark)\b|\b5th\s*ave|\bvth\s*ave|\b3rd\s*cross|டவர்\s*பார்க"),
    ("streetlight_eb", 1, r"\banna\s*(?:arch|aarch)\b|\biii(?:rd)?\s*ave|அண்ணா\s*(?:ஆர்ச்|ஆர்சு)"),
    ("sewage_pothole", 0, r"vijaya\s*nagar|விஜய\s*நகர்"),
    ("sewage_pothole", 1, r"phoenix|fee?nix|பீனிக்ஸ்|ஃபீனிக்ஸ்"),
    ("water_pipe", 0, r"kuruv[iy]karan|குருவிக்காரன்|anna\s*bus\s*stand|அண்ணா\s*பஸ்\s*ஸ்டாண்ட்"),
    ("water_pipe", 1, r"gandhi\s*puram|காந்தி\s*புர(?:ம்|த்)"),
    ("ration_tnpds", 0, r"\b(?:tnpds shop|anna nagar west ext)\b|அண்ணா\s*நகர்\s*மேற்கு\s*விரிவாக்கம்"),
]
_FUZZY_PLACES = (
    ("streetlight_eb", 0, "tower park"),
    ("streetlight_eb", 1, "anna arch"),
    ("sewage_pothole", 0, "vijayanagar bus stand"),
    ("sewage_pothole", 1, "phoenix marketcity"),
    ("water_pipe", 0, "kuruvikaran salai"),
    ("water_pipe", 1, "gandhipuram 100 feet"),
)
_VICINITY = re.compile(
    r"(?P<before>[^,;.!?]+?)(?:\s+(?:பக்கத்துல|பக்கத்தில்|அருகில்|எதிரில்|ஆப்[போ]+சிட்\S*|"
    r"pakkathula|pakkam|arugil|opposite-la)(?:\s|$)|\s+(?:இருக்கேன்|இருக்கேனுங்க)(?:\s|$))|"
    r"\b(?:near|opposite|by)\s+(?P<after>[^,;.!?]+)", re.I,
)
_PLACE_WORD = re.compile(
    r"\b(?:mall|junction|market|school|temple|bridge|station|park|street|road|avenue|bus stand)\b|"
    r"மால்|சந்தை|பள்ளி|கோவில்|பாலம்|நிலையம்|மார்க்கெட்|பார்க்|தெரு|நகர்|சந்திப்பு",
    re.I,
)


def validate_phone_digits(text: str) -> dict[str, Any]:
    """Venky B §3: Reject partial or letter-corrupted phone spans; accept only 10 valid Indian mobile digits."""
    digits = re.sub(r"\D", "", text or "")
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    has_letters = bool(re.search(r"[A-Za-z]", re.sub(r"\+?91|phone|mobile|number|call|en", "", text or "", flags=re.I)))
    if len(digits) < 10:
        return {"valid": False, "complete": False, "digits_count": len(digits), "reason": "incomplete_digits"}
    if has_letters or not re.match(r"^[6-9]\d{9}$", digits):
        return {"valid": False, "complete": True, "digits_count": len(digits), "reason": "invalid_indian_mobile"}
    return {"valid": True, "complete": True, "digits_count": 10, "masked": f"+91 {digits[:2]}XXXXXX{digits[-2:]}"}


def resolve_explicit_place(txt: str) -> dict[str, Any] | None:
    """Prefer the most recently named fixture landmark when handling a correction."""
    matches = [(m.start(), service, idx) for service, idx, pattern in _VERIFIED_PLACES for m in re.finditer(pattern, txt)]
    if matches:
        _, service, idx = max(matches)
        return SERVICE_CATALOG[service]["landmarks"][idx]

    try:
        from rapidfuzz import fuzz

        rf_scores = [
            (fuzz.token_set_ratio(alias, txt), service, idx)
            for service, idx, alias in _FUZZY_PLACES
        ]
        rf_scores.sort(reverse=True)
        if rf_scores and rf_scores[0][0] >= 86 and (len(rf_scores) == 1 or rf_scores[0][0] - rf_scores[1][0] >= 8):
            _, service, idx = rf_scores[0]
            return SERVICE_CATALOG[service]["landmarks"][idx]
    except Exception:
        pass

    words = re.findall(r"\b[a-z0-9]+\b", txt)
    scores = []
    for service, idx, alias in _FUZZY_PLACES:
        width = len(alias.split())
        score = max((SequenceMatcher(None, alias, " ".join(words[i:i+width])).ratio()
                     for i in range(len(words) - width + 1)), default=0)
        scores.append((score, service, idx))
    scores.sort(reverse=True)
    score, service, idx = scores[0]
    if score >= 0.90 and score - scores[1][0] >= 0.05:
        return SERVICE_CATALOG[service]["landmarks"][idx]
    return None


def _area_name(txt: str) -> str | None:
    if not REGISTRY.list_summaries():
        return None
    matches = [
        (area != "OMR", match.start(), area)
        for area, pattern in REGISTRY.get("tn").spoken_areas.items()
        for match in re.finditer(pattern, txt)
    ]
    return max(matches)[2] if matches else None


def extract_landmark_text(text: str, *, awaiting_location: bool = False) -> str:
    """Keep spoken public place text even when the civic pack has no ward match."""
    for match in reversed(list(_VICINITY.finditer(text))):
        if match["after"]:
            candidate = match["after"]
            issue_positions = [m.start() for _, pattern in _ISSUES if (m := pattern.search(candidate.lower()))]
            candidate = candidate[:min(issue_positions)] if issue_positions else candidate
        else:
            candidate = match[0]
        candidate = re.sub(r"^\s*(?:நான்\s+(?:வந்து\s+)?|illa\s+|இல்ல[ை]?\s+|wait\s+)", "", candidate, flags=re.I).strip()
        if candidate and not any(pattern.match(candidate.lower()) for _, pattern in _ISSUES):
            return candidate[:180]
    if awaiting_location and _PLACE_WORD.search(text) and len(text.split()) <= 9 and not any(
        pattern.search(text.lower()) for _, pattern in _ISSUES
    ) and not re.search(r"\b(?:yes|thanks|please|later|sorry)\b|வேணாம்|நன்றி", text, re.I):
        return re.sub(r"^\s*(?:illa|actually|no|இல்லை?)[\s,]+", "", text, flags=re.I).strip()[:180]
    return ""


def analyze_turn(combined_text: str, gps_landmark: dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize Tanglish/Tamil utterance, detect missing slots or multi-ward ambiguity."""
    txt = unicodedata.normalize("NFC", combined_text).casefold()
    explicit = resolve_explicit_place(txt)
    area = _area_name(txt)
    urgency = classify_sentiment_urgency(txt)
    issue = next((sid for sid, pattern in _ISSUES if pattern.search(txt)), None)
    if not issue and _ROAD_DEFECT.search(txt):
        issue = "sewage_pothole"
    if urgency.tier == "CRITICAL_SAFETY" and _ISSUES[-1][1].search(txt):
        issue = "streetlight_eb"

    ticket_m = re.search(r"#?[A-Z]{2,5}-?\d{4,6}", combined_text, re.IGNORECASE)
    ticket_ref = ticket_m.group(0).upper() if ticket_m else "#GCC-20491"
    if not ticket_ref.startswith("#"):
        ticket_ref = "#" + ticket_ref

    if not explicit and area == "Velachery" and ticket_m and ticket_ref == "#GCC-20491":
        explicit = SERVICE_CATALOG["garbage_1100"]["landmarks"][0]
    resolved = explicit or gps_landmark
    landmark_text = resolved["name"] if resolved else extract_landmark_text(combined_text) or area or ""
    ambiguous_area = {"Velachery": "velachery", "Anna Nagar": "anna_nagar"}.get(area) if not resolved else None
    lm = resolved or {"name": landmark_text, "district": "", "zone": "", "ward": "", "street": "", "road_id": ""}
    svc_id = issue or "streetlight_eb"
    service_places = SERVICE_CATALOG[svc_id]["landmarks"]

    return {
        "has_place": bool(landmark_text),
        "has_issue": bool(issue) or urgency.tier == "LIFE_SAFETY",
        "landmark_text": landmark_text,
        "area": area,
        "ambiguous_area": ambiguous_area,
        "wants_attachment": bool(_ATTACH_MENTION_RE.search(txt)),
        "service_id": svc_id,
        "landmark_idx": service_places.index(lm) if lm in service_places else 0,
        "landmark": lm,
        "ticket_ref": ticket_ref,
        "urgency": urgency.__dict__,
    }
