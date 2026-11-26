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
- **Status:** Fully aligned with Pure HITL Voice Agent + Sentiment/Urgency Triage + Non-Silent VAD architecture (`~705 words`, safely inside `80–800` word cap)

```text
Act as an expert voice-AI and frontend engineer and build a working web application called "NammaKural (நம்ம குரல்)" — a calm, sunlit, pure conversational Voice Agent, GIS landmark-to-ward resolver, sentiment/urgency router, and Human-in-the-Loop (HITL) civic filing bridge for Tamil Nadu's 6 public portals, using Wispr Flow as the voice intake layer.

Your users and their languages:
Everyday Tamil Nadu residents across Chennai and 38 districts—senior citizens, daily-wage earners, homemakers, tenants, shopkeepers, and office workers across urban and semi-urban streets. They speak Tanglish (colloquial Tamil mixed with English nouns like "streetlight", "transformer", "saakkadai", "ration card"), regional Tamil dialects (Chennai Madras Bashai, Madurai, Kongu, Tirunelveli, Trichy), and Indian English. They describe places by street landmarks ("Tower Park back side", "Vijayanagar bus stand kitta") rather than Zone, Ward, Depot, or GIS Road IDs, and reject intimidating multi-field government forms.

The voice flow, step by step:
Step 1 (Minimal Orb Intake, Reasoning & Urgency Triage — Zero Form Wall):
- The screen opens to a clean white/sunlit Foundry-style canvas with an animated 3-layer harmonic Acoustic Orb, a single Wispr Flow dictation bar, and 5 quick spoken examples. There are zero upfront forms.
- Citizen taps the orb or Wispr Flow hotkey and speaks in one breath: "Anna Nagar Tower Park back side 5th Avenue-la streetlight 5 naala eriyala, transformer wire vera loose-aa spark aaguthu."
- The orb animates Listening -> Thinking -> Never-Going-Silent Narration ("Checking Zone 08 Ward 103 and splitting agencies..."), classifies Urgency & Sentiment (`P1 Critical Safety` due to "spark", `P2 High Escalation` for chronic/false-closure cases, or `P3 Standard`), and resolves Chennai Zone 08, Ward 103, Vth Avenue (Road ID 76370) across GCC PGRS (1913) and TANGEDCO (1912).

Step 2 (Clarify ONLY When Needed — Missing Slot or Multi-Ward Ambiguity):
- If key slots are missing ("saakkadai overflow aaguthu" without location) or an area spans multiple wards ("Velachery main road-la pothole"), the agent pauses dispatch and asks one brief spoken question backed by clickable voice/touch pills: "Velachery spans multiple Wards. Which landmark is closest: Vijayanagar Bus Stand (Ward 178) or Phoenix Marketcity (Ward 175)?" Once answered, it locks Zone 13 -> Ward/Depot 178 across CMWSSB (strict 200-char remark cap) and GCC Roads.

Step 3 (Mandatory HITL Final Clarity Check — Approve Before Dispatch):
- Before unlocking any send/dispatch action, the agent pauses at a Human-in-the-Loop confirmation card displaying: (a) Plain-language issue summary, (b) Detected Urgency & Sentiment badge (e.g. P1 Critical Safety or P2 Chronic Escalation), (c) Resolved District, Zone, Ward, Road ID, and portal access strategy (e.g. GCC Open Anonymous Web vs. TANGEDCO OTP bypass via WhatsApp), plus landmark confirmation pills.
- Citizen chooses "Approve & Prepare Dispatch" or "Speak / Type a Change" (e.g. "Add Pole 42" or "Switch to Anna Arch").

Step 4 (Post-Approval Dispatch, Emergency Prioritization, Photo Stamp & 1100 Escalation):
- Only after HITL approval does the agent unlock final tools: conversational Tamil TTS confirmation (ta-IN) so elders verify by ear, P1 Emergency Dial ("1912" prioritized at top for sparking wires), 1-Tap Official WhatsApp queues (GCC +91-9445061913, CMWSSB +91-8144930308, TWAD +91-9499991916, TANGEDCO 9498794987) or direct email (cmcell@tn.gov.in / 1100 for falsely closed complaints like "#GCC-20491 fix pannama close pannitanga"), an interactive Tap-to-Mark <1MB JPEG photo stamper (overlaying Ward, Road ID, coordinates), and a collapsed-by-default portal field-copy drawer.

Noise, accents, mixed languages and misheard input:
1. Street Noise & Backchannel Filtering: Semantic VAD with a backchannel allowlist treats "ok", "mm-hmm", "seri", "aama" and bystander chatter as non-turns, while explicit "Talk to interrupt" cues ("stop", "wait", "niruthunga") immediately stop TTS output (<150ms) to accept corrections.
2. Tanglish & Dialect Normalization: Phonetic matcher maps code-mixed and Tamil Unicode variants ("eriyala/light podala", "saakkadai", "thanni varala/kudineer", "kuppai") to canonical agencies without repeating input.
3. Cut-off Speech & Ambiguity Recovery: Retains turn-by-turn conversation state so late additions ("Door 14") update drafts cleanly, and HITL clarity review prevents misrouted complaints before dispatch.

Enough detail to build:
Build a single-file, sunlit responsive web app with an HTML5 Canvas 3-layer AcousticOrb state machine (`idle`, `listening`, `thinking`, `clarifying`, `hitl_review`, `approved_dispatch`, `critical`), plain Wispr Flow input, dynamic clarifier pills, P1/P2/P3 sentiment router, HITL approval gate locking post-approval Tamil TTS / WhatsApp / <1MB photo stamper, `English | தமிழ்` toggle, `A+ Text` accessibility scaling, and `2G Lite` mode—backed offline by TN ArcGIS Ward/Road schemas.
```

---

## Activity 03 — Impact (`Locked until Activity 02 submitted`)
- **Task:** *"Describe who benefits if your idea works, what changes for them, and how you'd know."*
- **Drafting checklist once unlocked:**
  - **Who benefits:** Tamil Nadu residents (especially elders, working professionals, and Tanglish/Tamil speakers across cities & towns)
  - **What changes:** Minutes-long/hours-long multi-portal form hunting drops to <60s; zero "wrong department" rejections from GCC/TANGEDCO/CMWSSB mix-ups; higher successful reopening when tickets are closed prematurely
  - **How you'd know:** Time from voice input to portal-ready fields (`<45s`), % of multi-issue complaints accurately split, reduction in misrouted/wrong-ward filings, and reopened/resolved escalation rate
