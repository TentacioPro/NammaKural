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
- **Status:** Tightened & verified `<800 words` (`~725 words` — Voice Agent + Neural Orb + 4-Step Reasoning + 6 TN Portals + 1-Tap WhatsApp + Photo Stamper)

```text
Act as an expert frontend engineer and build a complete single-page web application called "NammaKural (நம்ம குரல்)" — a calm, light-mode Tanglish Voice Agent, GIS street-and-ward resolver, photo-evidence stamper, and inclusive filing bridge for Tamil Nadu's 6 primary civic portals, built for Wispr Flow voice input.

Your users and their languages:
Everyday Tamil Nadu citizens across Chennai and 38 districts—senior citizens, daily-wage workers, homemakers, shopkeepers, tenants, and office workers, from low-literacy mobile users to tech-savvy residents. They speak code-mixed Tanglish (Tamil mixed with English nouns like "streetlight", "transformer", "drainage"), colloquial Tamil (தமிழ்) across regional accents (Chennai Madras Bashai, Madurai, Kongu, Tirunelveli, Trichy), and Indian English. They describe places by landmarks ("Tower Park back side", "Vijayanagar bus stand kitta") rather than Zone, Ward, Depot, or GIS Street IDs.

The voice flow, step by step:
Step 1 (Wispr Flow Voice Intake & Neural Orb):
- User taps the central animated Neural Voice Orb (or presses their Wispr Flow hotkey) and speaks into a plain voice bar: "Anna Nagar Tower Park back side 5th Avenue-la streetlight 5 naala eriyala, transformer wire vera loose-aa irukku."
- Agent animates from Listening to Reasoning and streams 4 transparent steps: (1) Heard 2 issues (streetlight outage + loose wire); (2) GIS Match -> Zone 08, Ward 103, Vth Avenue (Road ID 76370); (3) Split -> GCC PGRS (1913) & TANGEDCO Minnagam (1912); (4) Armed 1-tap WhatsApp & stamped <1MB photo.
Step 2 (Voice Landmark Disambiguation when an area spans multiple wards):
- User says: "Velachery main road-la sewage overflow aaguthu, periya pothole irukku."
- Agent pauses and asks back by voice and landmark pills: "Velachery covers multiple Wards. Which landmark is closest? Say or tap: (1) Vijayanagar Bus Stand (Ward 178), or (2) Phoenix Marketcity (Ward 175)."
- User says: "Vijayanagar Bus Stand." Agent locks Zone 13 -> Ward / Depot 178 and splits CMWSSB Metro Water (strict 200-char remark cap) and GCC PGRS Roads.
Step 3 (Service Photo Tap-to-Mark & Voice Slot-Filling):
- Displays a matching street photo for each service (Streetlight/EB, Sewage/Pothole, Water Leak, Ration Shop, Garbage). User taps the hazard to move a red target ring and appends missing details by voice ("Door number 14"). Agent stamps Zone, Ward, Road ID, and timestamp onto the <1MB JPEG.
Step 4 (Premature-Closure 1100 Voice Escalation):
- User says: "Complaint GCC-20491 fix pannama close pannitanga," and attaches a current photo. Agent drafts a Mudhalvarin Mugavari (1100) reopen petition.

What the product says or shows back (No Dense Form Wall):
1. Calm Agent Outcome Card & Tamil Audio Read-Back: Speaks confirmation aloud in conversational Tamil (ta-IN TTS) so blind, elder, and low-literacy users verify Ward and Department by ear.
2. Zero-Copy-Paste Assisted Actions (bypasses OTP/CAPTCHA gates):
   - "1-Tap Official WhatsApp / Email": Deep-links to official TN queues (GCC +91-9445061913, CMWSSB +91-8144930308, TWAD PUNAL +91-9499991916, TANGEDCO 9498794987, CM Cell cmcell@tn.gov.in, TNPDS support@tnpds.com) pre-filled with resolved bilingual text.
   - "1-Tap Helpline Dial": Calls 1913, 1100, 1916, 1912, or 1967.
3. Collapsible Portal Form Drawer (plus a "Full Form View" toggle): Expands per-field Copy cards matching inner DOM schemas—GCC PGRS (open 4-step wizard, anonymous mode, 17 types), CMWSSB (200-char cap), TWAD PUNAL (urban/rural tree), TANGEDCO, Mudhalvarin Mugavari, and TNPDS.

Noise, accents, mixed languages and misheard input:
1. Street Noise & Cut-Off Speech: Retains partial transcripts and lets users append missing pole/door numbers without restarting.
2. Accents & Tanglish Variants: Phonetic matcher normalizes dialect variants ("eriyala/light podala", "thanni varala/kudineer", "saakkadai", "kuppai") and Tamil Unicode.
3. Misheard Landmarks: Shows top-3 closest landmark pills for 1-tap correction.

Enough detail to build:
Build a sunlit, light-mode Voice Agent UI (inspired by Azure AI Foundry Agent Preview) with an HTML5 Canvas animated neural orb, clean Wispr Flow bar, 5 photo-thumbnail service pills, 4-step streaming reasoning trace, Outcome Card with Tamil TTS + 1-tap WhatsApp + Tap-to-Mark photo stamper, collapsible portal copy drawer, `English | தமிழ்` switcher, `A+` large-text toggle, and `2G Lite` mode. Embed real Chennai ArcGIS Zone/Ward/Street data and bilingual templates so it runs 100% offline.
```

---

## Activity 03 — Impact (`Locked until Activity 02 submitted`)
- **Task:** *"Describe who benefits if your idea works, what changes for them, and how you'd know."*
- **Drafting checklist once unlocked:**
  - **Who benefits:** Tamil Nadu residents (especially elders, working professionals, and Tanglish/Tamil speakers across cities & towns)
  - **What changes:** Minutes-long/hours-long multi-portal form hunting drops to <60s; zero "wrong department" rejections from GCC/TANGEDCO/CMWSSB mix-ups; higher successful reopening when tickets are closed prematurely
  - **How you'd know:** Time from voice input to portal-ready fields (`<45s`), % of multi-issue complaints accurately split, reduction in misrouted/wrong-ward filings, and reopened/resolved escalation rate
