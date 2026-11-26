# Round 1 Submissions (`Due: 29 Nov 2026` · `1 of 3 complete`)

## Activity 01 — Idea (`50–500 words`, `Text only, no uploads`)
- **Status:** Submitted (`Quality check passed · Evaluation pending`)

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
- **Status:** Finalized with GPS Popup/Fallback, Citizen Micro-Guide, Runtime Photo/Doc Upload, Cooldowns, Dual-Confirm HITL & Real Submission Paths (`689 words`, strictly inside `80–800` word cap)

```text
Act as an expert voice-AI and frontend engineer and build a working web app called "NammaKural (நம்ம குரல்)" — a calm, sunlit conversational Voice Agent, hybrid GPS/landmark-to-ward resolver, runtime evidence intake, anti-spam verified HITL router, and official civic filing bridge for Tamil Nadu's 6 public portals, built for Wispr Flow voice input.

Your users and their languages:
Everyday Tamil Nadu residents across Chennai and 38 districts—senior citizens, daily-wage earners, homemakers, shopkeepers, tenants, and office workers. They speak Tanglish (Tamil mixed with English words like "streetlight", "transformer", "saakkadai"), regional Tamil dialects (Chennai, Madurai, Kongu, Tirunelveli, Trichy), and Indian English, describing places by nearby landmarks ("Tower Park back side") rather than Ward or GIS Road IDs.

The voice flow, step by step:
Step 1 (Guided Onboarding, Orb Intake & Runtime Doc/Photo Upload — Zero Form Wall):
- Screen opens to a clean white Foundry-style canvas with an animated 3-layer Acoustic Orb, a single Wispr Flow dictation bar with a paperclip/camera attach button, a "My Request History" drawer, and a compact 3-step visual + Tamil audio explainer ("How to speak, attach a photo/bill, and confirm"). Zero upfront forms.
- Citizen speaks once ("Anna Nagar Tower Park back side 5th Avenue-la streetlight 5 naala eriyala, transformer wire loose-aa spark aaguthu") and can upload/snap a hazard photo, EB/water bill, or closed ticket screenshot mid-conversation; photos auto-compress under 1MB with Tap-to-Mark hazard targeting, and ticket/consumer numbers extract automatically without storing raw PII.
- Orb animates Listening -> Thinking -> Never-Going-Silent Narration, detects `P1 Critical Safety` (live spark), `P2 High Escalation` (false closure/chronic delay), or `P3 Standard`, and resolves Zone 08, Ward 103, Vth Avenue (Road ID 76370) across GCC PGRS (1913) and TANGEDCO (1912).

Step 2 (Location Permission Popup + Spoken Landmark Fallback & Cooldown Guard):
- Location Resolution: Prompts once with a calm GPS permission popup ("Use current location to auto-detect Ward?"). If allowed, verifies coordinates against ArcGIS Ward boundaries and confirms by voice. If denied or filing remotely, smoothly asks by voice in plain Tamil/Tanglish ("No problem—tell me your area or nearest tea shop, bus stand, or temple") and narrows multi-ward areas ("Velachery -> Vijayanagar Bus Stand Ward 178 or Phoenix Ward 175?").
- Anti-Spam & Cooldown Guard: Checks Request History and enforces a 24h department-per-ward cooldown against duplicate filings—unless `P1 Critical Safety` overrides it or citizen chooses CM Cell 1100 escalation on an existing ticket (#GCC-20491). Tool dispatch is code-gated (`Code > LLM`).

Step 3 (Two-Path Verified HITL Gate — Double Affirmation or Modal + Spoken Seal):
- Citizen authenticates via Mobile OTP (with DigiLocker/API-Setu & e-Sevai Operator hooks—zero raw Aadhaar stored) and completes a strict HITL Clarity Check:
  - Hands-Free Voice Path: Agent reads back Ward, Urgency, and Agencies in Tamil (ta-IN); citizen affirms the confirmation keyword twice ("உறுதி, உறுதி" / "Confirm, Confirm").
  - Dynamic Modal Path: Clarity popup shows full summary, uploaded evidence preview, and cooldown status; citizen clicks OK and speaks once ("உறுதி" / "Confirm") in native Tamil/Tanglish to seal dispatch.

Step 4 (Real Submission Paths — Official WhatsApp, Operator & Web Queues):
- Never automates logins or CAPTCHAs. Post-approval unlocks: (a) Citizen-owned WhatsApp official bots (GCC +91-9445061913, CMWSSB +91-8144930308, TWAD +91-9499991916, TANGEDCO 9498794987) using telecom identity, (b) Priority Helpline Dial (`1912` top-pinned for P1 hazards, plus 1913/1916/1100/1967) & CM Cell email (`cmcell@tn.gov.in`), and (c) e-Sevai Booth Operator payload cards + Tap-to-Mark <1MB GIS stamped photo + TNeGA/ULB webhook schema.

Noise, accents, mixed languages and misheard input:
1. Street Noise & Backchannel Immunity: Semantic VAD ignores "ok", "mm-hmm", "seri", "aama" and bystander noise, while "Talk to interrupt" cues ("stop", "wait", "niruthunga") halt playback (<150ms).
2. Tanglish & Dialect Normalization: Phonetic matcher normalizes variants ("eriyala/light podala", "saakkadai", "thanni varala", "kuppai") and Tamil Unicode.
3. Missing GPS / Misheard Landmarks: Interactive landmark pills and late voice additions ("Pole 42") update the HITL popup before dispatch.

Enough detail to build:
Build a sunlit single-page app with Canvas 3-layer AcousticOrb states, citizen 3-step onboarding micro-guide, GPS permission popup + spoken landmark fallback, mid-chat clip/camera upload (<1MB compressor + OCR stub), Request History & Cooldown engine, Mobile-OTP + Dual-Confirm Tamil HITL popup, official WhatsApp/1912 dispatch, `English | தமிழ்`, `A+ Text`, and `2G Lite` mode.
```

---

## Activity 03 — Impact (`Locked until Activity 02 submitted`)
- **Task:** *"Describe who benefits if your idea works, what changes for them, and how you'd know."*
- **Drafting checklist once unlocked:**
  - **Who benefits:** Tamil Nadu residents (especially elders, working professionals, and Tanglish/Tamil speakers across cities & towns)
  - **What changes:** Minutes-long/hours-long multi-portal form hunting drops to <60s; zero "wrong department" rejections from GCC/TANGEDCO/CMWSSB mix-ups; higher successful reopening when tickets are closed prematurely
  - **How you'd know:** Time from voice input to portal-ready fields (`<45s`), % of multi-issue complaints accurately split, reduction in misrouted/wrong-ward filings, and reopened/resolved escalation rate
