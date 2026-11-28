"""Versioned GCC PGRS Pre-Submit Schema Validator & Dry-Run Packet Builder (Zero Outbound Gov Requests)."""

from __future__ import annotations

import uuid
from typing import Any

from backend.civic_channels import checklist
from backend.state_packs import REGISTRY

GCC_SCHEMA_META = {
    "schema_version": "gcc-pgrs-2026-11-27",
    "source": "https://gccservices.in/pgr/registercomplaints",
    "reviewed_at": "2026-11-27",
    "attachment_max_kb": 1024,
    "outbound_gov_requests": False,
}

_CATEGORY_MAP: dict[str, dict[str, str]] = {
    "road_flooding": {
        "agency": "GCC PGRS",
        "category": "Water Stagnation",
        "sub_category": "Road waterlogging",
        "helpline": "1913",
    },
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

_ISSUE_LABELS = {
    "road_flooding": ("Road flooding", "சாலையில் மழைநீர் தேக்கம்"),
    "streetlight_eb": ("Streetlight or electrical fault", "தெருவிளக்கு அல்லது மின் கோளாறு"),
    "sewage_pothole": ("Sewage or road damage", "கழிவுநீர் அல்லது சாலை சேதம்"),
    "water_pipe": ("Water supply or pipe fault", "குடிநீர் அல்லது குழாய் கோளாறு"),
    "ration_tnpds": ("Ration shop issue", "ரேஷன் கடை பிரச்சனை"),
    "garbage_1100": ("Waste or grievance escalation", "குப்பை அல்லது புகார் மேல்முறையீடு"),
}


def build_grievance_draft(analysis: dict[str, Any], slots: dict[str, Any], cooldown: dict[str, Any] | None) -> dict[str, Any] | None:
    """Prepare the citizen's information for review without issuing a ticket."""
    if not analysis["has_issue"] or analysis.get("state_code") != "tn":
        return None
    intent = analysis["service_id"]
    label, label_ta = _ISSUE_LABELS.get(intent, ("Civic grievance", "பொதுப் புகார்"))
    landmark = analysis["landmark"]
    ward = landmark.get("ward") or ""
    gcc_area = bool(ward and landmark.get("district") == "Chennai")
    destination_id = "cm_cell_1100"
    if intent == "streetlight_eb" and analysis["urgency"]["tier"] == "CRITICAL_SAFETY":
        destination_id = "tangedco_ccms"
    elif gcc_area:
        destination_id = {
            "road_flooding": "gcc_pgrs", "streetlight_eb": "gcc_pgrs",
            "water_pipe": "cmwssb_gms",
        }.get(intent, destination_id)
    portals = REGISTRY.get("tn").portals if REGISTRY.list_summaries() else ()
    target = next((portal for portal in portals if portal.id == destination_id), None)
    destination = (
        {key: getattr(target, key) for key in ("id", "name", "url", "helpline")} if target else
        {"id": "cm_cell_1100", "name": "Tamil Nadu CM Helpline", "url": "", "helpline": "1100"}
    )
    if intent == "ration_tnpds":
        destination = {"id": "tnpds", "name": "Tamil Nadu Public Distribution System",
                       "url": "https://www.tnpds.gov.in/auth/login", "helpline": "1967"}
    status = "needs_confirmation"
    next_field = None
    if not ward or analysis.get("ambiguous_area"):
        status = "needs_location"
    elif cooldown and cooldown.get("in_cooldown") and not cooldown.get("override_allowed"):
        status = "cooldown"
    elif destination["id"] == "cmwssb_gms" and slots.get("duration_days") is None:
        status = "needs_details"
        next_field = "duration"
    elif intent == "road_flooding" and slots.get("focused_intake") and not slots.get("impact"):
        status = "needs_details"
        next_field = "impact"
    summary = slots.get("description") or label
    location = {
        "landmark": slots.get("reported_landmark") or landmark.get("name") or "",
        "area": analysis.get("area") or "",
        "ward": ward,
        "street": landmark.get("street") or "",
        "source": slots.get("location_source") or ("landmark" if analysis["has_place"] else None),
    }
    intake = checklist(destination["id"], {"summary": slots.get("description"),
                                           "verified_location": ward and not analysis.get("ambiguous_area"),
                                           "duration_days": slots.get("duration_days")})
    if intent == "road_flooding" and slots.get("focused_intake"):
        intake["checks"].append({"label": "Road passability", "complete": bool(slots.get("impact"))})
    return {
        "status": status, "intent": intent, "label": label, "label_ta": label_ta,
        "summary": summary[:200] if destination["id"] == "cmwssb_gms" else summary,
        "duration_days": slots.get("duration_days") if destination["id"] == "cmwssb_gms" else None,
        "impact": slots.get("impact") if intent == "road_flooding" else None,
        "next_field": next_field,
        "location": location, "destination": destination,
        "checklist": intake,
        "revision": slots.get("complaint_version", 1), "urgency_tier": analysis["urgency"]["tier"], "submitted": False,
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
