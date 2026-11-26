# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Single-file zero-dependency HTML/CSS/JS prototype (`index.html`), engineered for `<15 KB` gzipped initial load, instant offline/low-3G execution, and mobile-native touch ergonomics.

## Users

Everyday Tamil Nadu citizens across Chennai and all 38 districts—including senior citizens, tenants, daily-wage workers, shopkeepers, homemakers, and working professionals. They speak in code-mixed Tanglish (Tamil in Latin script mixed with English nouns), colloquial regional Tamil (தமிழ் across Chennai, Madurai, Kongu, Tirunelveli, and Trichy dialects), and Indian English. They stand on residential streets in bright daylight or evening streetlamp glare, often on budget Android phones over congested 3G/4G connections, describing civic hazards by neighborhood landmarks rather than administrative Zone, Ward, Depot, or GIS Street IDs.

## Product Purpose

**NammaKural** (*நம்ம குரல்* — "Our Voice") turns a 10-second spoken Tanglish/Tamil/English complaint into verified Tamil Nadu civic jurisdiction data (`Region → District → Civic Body → Zone → Ward/Depot → Official GIS Street ID`), splits multi-agency issues across Tamil Nadu's 6 primary civic portals (`GCC PGRS 1913`, `CMWSSB Metro Water 1916`, `TWAD Board PUNAL 1916`, `TANGEDCO CCMS 1912`, `Mudhalvarin Mugavari 1100`, `TNPDS 1967`), stamps `<1 MB` photo evidence, and lets any citizen file either via **1-Tap Official WhatsApp / Email / Helpline (Zero-Copy-Paste)** or **Field-by-Field Portal Schema Copy Cards**, plus a **Premature-Closure (`1100`) Reopen & Escalation Drafter**.

## Positioning

Unlike single-portal government forms or isolated complaint social feeds, NammaKural is a citizen-side **voice-to-schema router, GIS street/ward disambiguator, and dual-mode filing bridge** that never automates government logins, OTPs, or CAPTCHAs—instead bypassing page-1 friction via official WhatsApp grievance queues (`+91 94450 61913`, `+91 81449 30308`, `+91 94999 91916`, `94987 94987`) and exact character-capped DOM field payloads (such as CMWSSB's strict 200-character `complRemarks` limit and GCC's 17 complaint types / 180 sub-types).

## Operating Context

- Used outdoors on a street corner looking at an overflowing sewage manhole, dead streetlight, sparking transformer wire, or uncollected garbage pile, or indoors escalating a falsely closed ticket.
- Voice input enters through **Wispr Flow** (hotkey dictation directly into the intake surface) or 1-tap Tanglish voice presets.
- Must work immediately on low-bandwidth connections with zero external framework waterfalls, zero layout shift (`CLS = 0`), and full offline resilience.

## Capabilities and Constraints

- **Public schemas only:** Never automate government logins, OTPs, or CAPTCHAs.
- **No PII committed:** Sample fixtures use synthetic complaint IDs and public landmarks only.
- **Anti-Reference (Explicit User Ban):** Must NEVER resemble the 6 inspected government portals (`gccservices.in`, `cmhelpline.tnega.org`, `cms-cmwssb.tn.gov.in`, `punal.tn.gov.in`, `ccms.tangedco.org`, `tnpds.gov.in`)—no bureaucratic multi-step grey bootstrap boxes, no hexagonal clip-art splash screens, no floating social-media sidebars, no tiny cramped dropdowns, no 1-second timeout traps, and no generic SaaS card grids.

## Brand Commitments

- Bilingual clarity: English + Tamil (*தமிழ்*) treated as first-class typographic equals, with conversational Tamil audio read-back (`TTS`) for low-literacy and elder citizens.
- High-contrast daylight-legible civic utility built for speed, dignity, and zero bureaucratic intimidation.

## Evidence on Hand

- Verified live DOM schemas, inner JS bundles, and GIS endpoints from all 6 Tamil Nadu portals (`docs/TN_CIVIC_PORTALS.md`):
  - `GCC PGRS`: 4-step wizard, live ArcGIS `EDPMobile2025/FeatureServer/0/query` (`region`, `new_zone`, `new_ward`, `road_id`, `road_name`, `gis_id`), 17 Complaint Types & 180 Sub-Types (`97`–`454`), `<1 MB` photo rule, WhatsApp `+91 94450 61913` / Helpline `1913`.
  - `CMWSSB`: `Public` vs `Consumer` type, `Area → Depot → Location → Street → Door No → Problem Duration (Days) → Details (max 200 chars)`, WhatsApp `+91 81449 30308` (`#/whatsappNew`), Helpline `1916`.
  - `TWAD PUNAL`: 4-branch urban/rural hierarchy (`Corporation / Municipality / Town Panchayat / Rural Block-Village-Habitation`), WhatsApp `+91 94999 91916`, Helpline `1916`.
  - `TANGEDCO CCMS`: Minnagam `94987 94987` / `1912`, Service/General fault taxonomy.
  - `Mudhalvarin Mugavari`: `1100`, `cmcell@tn.gov.in`, Secretariat department taxonomy, premature-closure escalation.
  - `TNPDS`: `1967`, `support@tnpds.com`, `/pages/feedback` open route & post-OTP `classification` + `1000-char` description.

## Product Principles

1. **Voice in, bureaucracy out:** The citizen speaks landmarks and problems in one breath; the system resolves administrative codes, splits departments, and formats bilingual prose.
2. **Two exit ramps for every citizen:** 1-Tap Official WhatsApp / Helpline / Email for elders and non-tech users; 1-Tap per-field DOM copy for web portal filers.
3. **2G/3G & Daylight First:** Zero heavy JS bundles, inline SVG iconography, instant deterministic routing (<16ms), and 48px+ thumb-zone touch targets.
4. **Evidence that cannot be brushed off:** Tap-to-mark photo canvas stamps official Ward, GIS Street ID, coordinates, and timestamp right onto `<1 MB` compressed evidence.

## Accessibility & Inclusion

- WCAG AAA-inspired daylight contrast, `≥48×48px` coarse-pointer touch targets, Tamil TTS voice read-back, keyboard navigation, and zero hover-only affordances.
