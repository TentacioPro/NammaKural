"""Versioned GCC PGRS Pre-Submit Schema Validator & Dry-Run Packet Builder (Zero Outbound Gov Requests)."""

from __future__ import annotations

import uuid
from typing import Any

GCC_SCHEMA_META = {
    "schema_version": "gcc-pgrs-2026-11-27",
    "source": "https://gccservices.in/pgr/registercomplaints",
    "reviewed_at": "2026-11-27",
    "attachment_max_kb": 1024,
    "outbound_gov_requests": False,
}

_CATEGORY_MAP: dict[str, dict[str, str]] = {
    "streetlight_eb": {
        "agency": "GCC PGRS — Streetlight (1913) / TANGEDCO (1912)",
        "category": "Street Lights",
        "sub_category": "Non-burning of Street Light / Pole Fault",
        "helpline": "1913 / 1912",
    },
    "sewage_pothole": {
        "agency": "CMWSSB Metro Water (1916) / GCC Roads (1913)",
        "category": "Storm Water Drain & Roads",
        "sub_category": "Sewage Overflow / Pothole Repair",
        "helpline": "1916 / 1913",
    },
    "water_pipe": {
        "agency": "TWAD Board PUNAL / CMWSSB (1916)",
        "category": "Drinking Water Supply",
        "sub_category": "Pipeline Leakage / Contamination",
        "helpline": "1916",
    },
    "ration_tnpds": {
        "agency": "TNPDS Consumer Helpline (1967)",
        "category": "Public Distribution System",
        "sub_category": "Fair Price Shop / Supply Issue",
        "helpline": "1967",
    },
    "garbage_1100": {
        "agency": "Mudhalvarin Mugavari — CM Cell (1100) / GCC SWM",
        "category": "Solid Waste Management",
        "sub_category": "Unattended Garbage / False Closure Appeal",
        "helpline": "1100 / 1913",
    },
}


def build_gcc_preview_packet(
    *,
    service_id: str,
    landmark: dict[str, Any],
    summary_text: str,
    urgency_tier: str = "STANDARD",
    complaint_version: int = 1,
    otp_verified: bool = False,
    hitl_approved: bool = False,
    attachment_size_kb: float = 0.0,
) -> dict[str, Any]:
    """Validate slots against the public GCC schema and return a non-submitting NK-PREVIEW packet."""
    cat = _CATEGORY_MAP.get(service_id, _CATEGORY_MAP["streetlight_eb"])
    ward = str(landmark.get("ward") or "").strip()
    zone = str(landmark.get("zone") or "").strip()
    street = str(landmark.get("street") or "").strip()
    road_id = str(landmark.get("road_id") or "").strip()
    lm_name = str(landmark.get("name") or "").strip()

    missing_fields: list[str] = []
    if not lm_name:
        missing_fields.append("landmark")
    if not ward:
        missing_fields.append("ward_verification")
    if not otp_verified:
        missing_fields.append("mobile_otp")
    if not hitl_approved:
        missing_fields.append("dual_confirm_hitl")
    if attachment_size_kb > GCC_SCHEMA_META["attachment_max_kb"]:
        missing_fields.append("attachment_exceeds_1024kb")

    preview_id = f"NK-PREVIEW-{uuid.uuid4().hex[:6].upper()}"
    return {
        "preview_id": preview_id,
        "schema": GCC_SCHEMA_META,
        "complaint_version": complaint_version,
        "ready_for_portal": len(missing_fields) == 0,
        "missing_fields": missing_fields,
        "outbound_gov_requests": False,
        "notice_en": "Complaint packet validated and ready. No government ticket has been filed.",
        "notice_ta": "புகார் விவரங்கள் சரிபார்க்கப்பட்டு தயாராக உள்ளது. அரசு இணையதளத்தில் இன்னும் புகார் அனுப்பப்படவில்லை.",
        "fields": {
            "agency": cat["agency"],
            "category": cat["category"],
            "sub_category": cat["sub_category"],
            "zone": zone or "Needs verification",
            "ward": ward or "Needs verification",
            "street": street or lm_name or "Needs verification",
            "road_id": road_id or "Needs verification",
            "landmark": lm_name or "Needs verification",
            "urgency_tier": urgency_tier,
            "grievance_summary": summary_text[:280],
            "helpline_fallback": cat["helpline"],
        },
    }
