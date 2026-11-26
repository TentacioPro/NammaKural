# Round 1 Submissions (`Due: 27 Nov 2026` · `0 of 3 complete`)

## Activity 01 — Idea (`50–500 words`, `Text only, no uploads`)
- **Status:** Tailored to exact 4-section rubric (`~335 words`)

```text
The problem:
Filing a civic complaint in Tamil Nadu requires navigating over nine fragmented government portals—including Mudhalvarin Mugavari (1100), Greater Chennai Corporation PGRS (1913), CMWSSB Metro Water (14416), TWAD PUNAL (1916), TANGEDCO CCMS (1912), TNPDS (1967), and TN e-Sevai. Every portal forces citizens through rigid, English-heavy cascading dropdowns (District -> Civic Body -> Zone I-XV -> Ward -> Department -> Sub-Category). Most residents do not know their administrative Zone or Ward number, nor which agency owns an overlapping street issue—frequently confusing GCC Electrical vs. TANGEDCO for street poles, or GCC Storm Water Drains vs. CMWSSB for waterlogging. As a result, complaints take hours to file, bounce weeks later as "wrong jurisdiction," or get closed prematurely without a real fix.

Who has it, where and how often:
Tens of millions of urban and semi-urban residents across Chennai and Tamil Nadu's 38 districts—especially senior citizens, tenants, homemakers, shopkeepers, and working professionals. It happens right on residential streets and neighborhoods every week whenever garbage overflows, streetlights fail, sewage backs up, voltage drops, or potholes open after rain. Even tech-literate office workers spend hours hunting ward maps and re-typing complaints across multiple forms, while non-English speakers give up or depend on middlemen.

The voice-first product:
NammaKural (Our Voice) is a Tanglish-first civic grievance router, landmark-to-ward resolver, and form bridge powered by Wispr Flow.
Step 1: The citizen speaks naturally for 10 seconds in Tanglish, Tamil, or English, for example: "Anna Nagar Tower Park back side 3rd cross-la streetlight 5 naala eriyala, transformer wire vera loose-aa irukku."
Step 2: NammaKural extracts the spoken landmark (or asks one quick nearby-landmark question if an area spans multiple wards) and resolves the exact District, Civic Body, Zone, and Ward number.
Step 3: It splits multi-department issues across the right Tamil Nadu portals (such as routing the dead streetlight to GCC Electrical and the loose transformer wire to TANGEDCO CCMS).
Step 4: It generates portal-matched, field-by-field cards with exact dropdown selections, formal English and Tamil descriptions, 1-click Copy buttons for every field, and a 5-second voice-to-escalation drafter for Mudhalvarin Mugavari (1100) if a ticket is closed prematurely.

Why voice comes first:
Citizens experience civic problems while standing on the street and naturally describe locations by spoken landmarks and code-mixed Tanglish—not bureaucratic Ward IDs, department codes, or formal English prose. A menu-first form still traps the user in guesswork; speaking first lets the citizen state the full messy reality in one breath while NammaKural handles location disambiguation, agency splitting, and formal bilingual translation behind the scenes.
```

---

## Activity 02 — Prompt (`80–800 words`, `Text only, no uploads`)
- **Status:** Grounded in verified inner wizard steps, JS bundles & GIS APIs of all 6 TN portals (`~765 words`)

```text
Act as an expert frontend engineer and build a complete, working single-page web application called "NammaKural (நம்ம குரல்)" — a Tanglish-first civic grievance router, GIS street-and-ward resolver, photo-evidence stamper, and inclusive filing bridge for Tamil Nadu's 6 primary civic portals, built for Wispr Flow voice input.

Your users and their languages:
Everyday Tamil Nadu citizens across Chennai and 38 districts—including senior citizens, daily-wage workers, homemakers, shopkeepers, tenants, and office workers, ranging from low-literacy mobile users to tech-savvy residents. They speak in code-mixed Tanglish (Tamil mixed with English words like "streetlight", "transformer", "drainage"), colloquial Tamil (தமிழ்) across regional accents (Chennai Madras Bashai, Madurai, Kongu/Coimbatore, Tirunelveli, Trichy), and Indian English. They describe places by spoken landmarks ("Anna Nagar Tower Park back side", "Velachery Vijayanagar bus stand kitta") rather than administrative Zone, Ward, Depot, or GIS Street IDs.

The voice flow, step by step:
Step 1 (Initial Voice Intake):
- User says (via Wispr Flow into the main voice box or by tapping a sample pill): "Anna Nagar Tower Park back side 5th Avenue-la streetlight 5 naala eriyala, transformer wire vera loose-aa irukku."
- Product says & shows back (on-screen + Tamil/English TTS voice read-back): "Heard 2 issues near Anna Nagar Tower Park: (1) Streetlight not burning, (2) Loose transformer wire. Resolved GIS Location: Chennai -> Central Region -> Zone 08 (Anna Nagar) -> Ward 103 -> Official Street: Vth Avenue (Road ID 76370)."
Step 2 (Voice Landmark Disambiguation when an area spans multiple wards/depots):
- User says: "Velachery main road-la sewage overflow aaguthu, periya pothole irukku."
- Product asks back by voice and big visual pills: "Velachery covers multiple Wards and Metro Water Depots. Which landmark are you closest to? Say or tap: (1) Vijayanagar Bus Stand (Zone XIII, Ward 178), (2) Phoenix Marketcity (Ward 175), or (3) Velachery MRTS Station (Ward 177)."
- User says: "Vijayanagar Bus Stand."
- Product locks "Zone 13 -> Ward / Depot 178 -> Velachery Main Road" and splits the complaint across CMWSSB Metro Water and GCC PGRS Roads.
Step 3 (Photo Evidence Tap-to-Mark & Voice Slot-Filling):
- User snaps or selects a street photo, taps directly on the hazard (pothole/wire/sewage) to drop a red marker ring, and speaks any missing slot ("3 days-aa irukku, door number 14").
- Product inserts "Problem Duration: 3 Days" and "Door No: 14" into the form cards, stamps an official footer onto the photo (Zone, Ward, Official Street Name, Lat/Lng, Timestamp), and compresses it under 1 MB (required by GCC PGRS's strict 1 MB JPG/PNG check).
Step 4 (Premature-Closure 1100 Voice Escalation):
- In the "Closed Without Fix (1100)" tab, user says: "Complaint GCC-20491 fix pannama close pannitanga," plus attaches a "Still Broken Today" photo. Product generates a Reopen Petition and Mudhalvarin Mugavari (1100) escalation.

What the product says or shows back (3 Inclusive Filing Modes):
1. Tamil Audio Read-Back & Verified Jurisdiction Strip: Speaks confirmation aloud in conversational Tamil and displays Region, District, Body Type (Corporation / Municipality / Town Panchayat / Rural Block-Village-Habitation), Zone, Ward/Depot, Official Street Name, and Lat/Lng.
2. Zero-Copy-Paste Mode for Non-Tech / Semi-Literate Users (bypasses OTP/CAPTCHA walls):
   - "1-Tap Official WhatsApp Filing": Deep-links to official TN grievance WhatsApp queues (GCC +91-9445061913, CMWSSB +91-8144930308, TWAD PUNAL +91-9499991916, TANGEDCO Minnagam 9498794987) with the full Ward/Street-resolved bilingual payload ready to hit Send.
   - "1-Tap Official Email & Helpline Voice Cue": Opens pre-filled mailto for Mudhalvarin Mugavari (cmcell@tn.gov.in) or TNPDS (support@tnpds.com), or dials 1913 / 1100 / 1916 / 1912 / 1967 with a 10-second Tamil speakerphone cue card.
3. Portal-Matched Field-by-Field Copy Cards (matching each portal's exact inner DOM schema):
   - GCC PGRS (1913): 4-step wizard fields (Google Places Search string, GIS Street Name, Lat/Lng, Landmark, exact 17 Complaint Types & 180 Sub-Types like "Street Light -> Non burning of Street lights", "<1MB Stamped Photo").
   - CMWSSB (1916): Public/Consumer Type, Area, Depot, Location, Street, Door No, Category, Sub-Category, Problem Duration (Days), and strict 200-character Remarks.
   - TWAD PUNAL (1916), TANGEDCO CCMS (1912), Mudhalvarin Mugavari (1100), and TNPDS (1967): Exact hierarchical dropdown values, formal English + Tamil descriptions, and 1-click Copy per field.

Noise, accents, mixed languages and misheard input:
1. Street Noise & Cut-Off Speech: Retains partial speech, highlights only the missing slot in amber, and appends the next voice phrase without restarting.
2. Regional Accents & Tanglish Variants: Built-in phonetic dictionary maps dialect/spelling variants ("eriyala/light podala", "thanni varala/kudineer", "saakkadai", "kuppai") and Tamil Unicode script.
3. Misheard Landmarks: Speaks and displays top-3 closest landmark pills for 1-tap correction.

Enough detail to build:
Build a responsive two-column layout (Left: Mode Switcher, Wispr Flow voice input, 5 Tanglish demo presets, Landmark Disambiguator pills, and HTML5 Canvas Photo Stamper; Right: Tamil TTS Read-Back bar, 1-Tap WhatsApp/Email/Helpline bar, and Split Portal Schema Cards). Embed real Chennai ArcGIS Zone/Ward/Street mappings, all 17 GCC categories, CMWSSB 200-char schema, PUNAL urban/rural hierarchy, and bilingual templates so it runs 100% live in the browser.
```

---

## Activity 03 — Impact (`Locked until Activity 02 submitted`)
- **Task:** *"Describe who benefits if your idea works, what changes for them, and how you'd know."*
- **Drafting checklist once unlocked:**
  - **Who benefits:** Tamil Nadu residents (especially elders, working professionals, and Tanglish/Tamil speakers across cities & towns)
  - **What changes:** Minutes-long/hours-long multi-portal form hunting drops to <60s; zero "wrong department" rejections from GCC/TANGEDCO/CMWSSB mix-ups; higher successful reopening when tickets are closed prematurely
  - **How you'd know:** Time from voice input to portal-ready fields (`<45s`), % of multi-issue complaints accurately split, reduction in misrouted/wrong-ward filings, and reopened/resolved escalation rate
