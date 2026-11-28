"""Citizen-facing channels and the facts the agent may collect for each."""

CHANNELS = {
    "gcc_pgrs": {
        "name": "Greater Chennai Corporation", "web": "https://gccservices.in/pgr/",
        "whatsapp": "https://wa.me/919445061913", "helpline": "1913",
        "collect": ["Issue category and subtype", "Incident street and landmark", "Specific complaint details"],
        "citizen_enters": ["Any name, contact or OTP requested by the chosen GCC form"],
        "optional": ["Photo under 1 MB", "Incident map pin"],
        "access": "Citizen web form, WhatsApp or phone. The legacy ERP form has its own mobile OTP.",
    },
    "cmwssb_gms": {
        "name": "Chennai Metro Water", "web": "https://cms-cmwssb.tn.gov.in/",
        "whatsapp": "https://wa.me/918144930308", "helpline": "1916",
        "collect": ["Public or consumer issue", "Area, depot or ward, locality and street", "Problem duration in days",
                    "Category, subtype and remarks up to 200 characters"],
        "citizen_enters": ["Contact details and any door or consumer number", "Portal CAPTCHA and OTP"],
        "optional": ["Attachment under 5 MB"],
        "access": "Citizen portal, WhatsApp or phone. Citizen completes portal verification.",
    },
    "twad_punal": {
        "name": "TWAD PUNAL", "web": "https://punal.tn.gov.in/grievance/#/",
        "helpline": "1916", "whatsapp": "https://wa.me/919499991916",
        "collect": ["District and local body type", "Block or ward and street or habitation", "Category and description"],
        "citizen_enters": ["Portal phone verification"],
        "optional": ["Photo"],
        "access": "Citizen portal, WhatsApp or phone. Verify local body and water authority before using this route.",
    },
    "tangedco_ccms": {
        "name": "TNPDCL Minnagam", "web": "https://ccms.tangedco.org/tangedco-public/",
        "helpline": "9498794987",
        "collect": ["General or service-related fault", "Public pole landmark or incident street", "Description and hazard"],
        "citizen_enters": ["Service number for account-related cases", "Portal mobile OTP and CAPTCHA"],
        "optional": ["Safe public landmark or pole identifier"],
        "access": "Citizen portal or the Minnagam call centre.",
    },
    "cm_cell_1100": {
        "name": "Tamil Nadu CM Helpline", "web": "https://cmhelpline.tnega.org/portal/en/signin",
        "email": "cmhelpline@tn.gov.in", "helpline": "1100",
        "collect": ["District and local body or incident locality", "Department if known", "Subject and petition description"],
        "citizen_enters": ["Portal sign-in or their own reply address for email"],
        "optional": ["Supporting attachment", "Previous complaint reference for an escalation"],
        "access": "Citizen portal, phone or email. The helpline can route an unknown department.",
    },
    "tnpds": {
        "name": "Tamil Nadu Public Distribution System", "web": "https://www.tnpds.gov.in/auth/login",
        "helpline": "1967",
        "collect": ["Fair-price shop or locality", "Complaint category and description"],
        "citizen_enters": ["Account and contact information in the official portal"],
        "optional": ["Public shop identifier"],
        "access": "Citizen portal or helpline. The account complaint flow requires citizen verification.",
    },
}


def checklist(destination: str, values: dict) -> dict:
    """Describe both the draft checks and fields that stay with the citizen."""
    channel = CHANNELS.get(destination, CHANNELS["cm_cell_1100"])
    return {**channel, "checks": [
        {"label": "Grievance type and details", "complete": bool(values.get("summary"))},
        {"label": "Incident location checked", "complete": bool(values.get("verified_location"))},
        *([{"label": "Problem duration", "complete": values.get("duration_days") is not None}]
          if destination == "cmwssb_gms" else []),
    ]}
