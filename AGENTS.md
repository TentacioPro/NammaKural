# AGENTS.md — `D:\NammaKural` (Scaler × Wispr Flow: Build for Bharat)

Mission: Build **`NammaKural`** (*நம்ம குரல்* — "Our Voice"): a Tanglish-first civic Voice Agent, GIS landmark-to-ward resolver, sentiment/urgency router, HITL clarity gate, and filing bridge for Tamil Nadu civic portals, with Wispr Flow as the voice intake layer.

## Timeline (Verified `2026-11-27`)
- **Round 1 (`Activity 01 → 02 → 03`):** Closes **29 Nov 2026, 11:59 pm** (`Activity 01`: Complete · `Activity 02`: Prompt `80–800 words` due · `Activity 03`: Impact unlocks next).
- **Round 2 (`27–30 Nov 2026`):** Unlocks once Round 1 passes; **`Submit your build: 30 Nov`**.
- **Shortlist & Finale:** Results `2 Dec 2026` · Campus Finale `13 Dec 2026`.

## Non-Negotiable Invariants
- **I1 Public schemas only:** Never automate government logins, OTPs, or CAPTCHAs. Use verified open web schemas, official WhatsApp queues, helplines (`1913`, `1916`, `1912`, `1100`, `1967`), or direct official emails (`cmcell@tn.gov.in`, `support@tnpds.com`).
- **I2 Mandatory HITL before dispatch:** Voice Agent must present a Final Clarity Check (`hitl_review`) showing resolved Ward, Agencies, and Sentiment/Urgency tier before unlocking dispatch tools.
- **I3 Ask only when needed:** Never show an upfront multi-field form wall; ask follow-up questions only when issue, location, or multi-ward landmark disambiguation is missing.
- **I4 No secrets or personal PII:** Never commit phone numbers, email IDs, API keys, OTPs, consumer numbers, or private user transcripts. Sample fixtures use synthetic ticket IDs and public landmarks only.
- **I5 Workspace isolation:** Keep `D:\NammaKural` isolated from `D:\ContentStudio` and `D:\learning\learning-tracker`.
- **I6 Verified quality bar:** Never report UI/code complete without running `impeccable detect --json index.html` (`[]`) and headless Playwright verification (`0` console/page errors, `0` horizontal overflow at `1440px`/`768px`/`390px`).
- **I7 Anti-reference UI rule:** Never mirror bureaucratic TN portal layouts (no cascading Bootstrap dropdown walls, no hexagonal clip-art splash screens, no floating social sidebars, no 1-second timeout traps).

## Spec-Driven MD Filesystem (Adapted from `agent-engine` & `md-upkeep`)
- **Session start:** Read [`CONTEXT.md`](CONTEXT.md) (`## Now`), [`TODO.md`](TODO.md), and only the tail of [`LOG.md`](LOG.md). Navigate specs via [`specs/INDEX.md`](specs/INDEX.md).
- **Keep live docs thin:** `CONTEXT.md ## Now` stays `<=25` lines; archive completed logs only if files exceed `120` lines (`CONTEXT.md`) or `150` lines (`TODO.md`). Do not create empty/stale archive bloat during the 72h sprint.
- **Tick format:** `- [x] ~~task~~ (YYYY-MM-DD, agent)`. Never rewrite past lines in `LOG.md`; append new dated one-line work entries.
- **Task specs:** Use [`specs/_TEMPLATE.md`](specs/_TEMPLATE.md) for every Round 2 subsystem (`allowed_paths`, `Non-goals`, `Invariants`, red-first acceptance tests).

## Key References
- [`DESIGN.md`](DESIGN.md) — Visual grammar & Foundry Voice Orb specs
- [`docs/architecture/VOICE_AGENT_ARCHITECTURE.md`](docs/architecture/VOICE_AGENT_ARCHITECTURE.md) — Full Voice AI stack, Tanglish/accent NLU, VAD, telemetry & self-improvement research
- [`docs/TN_CIVIC_PORTALS.md`](docs/TN_CIVIC_PORTALS.md) — Live DOM inspection & WhatsApp/OTP boundaries across 6 TN portals
- [`docs/ROUND1_SUBMISSIONS.md`](docs/ROUND1_SUBMISSIONS.md) — Submitted Activity 01 & ready Activity 02 prompt (`657 words`)
