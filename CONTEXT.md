# CONTEXT — NammaKural (*நம்ம குரல்*)

Updated: `2026-11-27 19:25 IST` · Branch: `feat/v4-specs-003-004-memory` · Stack: FastAPI (`backend/`) + Pluggable Bharat State Packs (`state_packs/`) + 6-State FSM + 3-Tier Engine (`offline_fsm` / `cloud_api` / `local_gpu`) + 11-Voice Neural TTS (`edge-tts`, `rate="+6%"`) + Self-Owned WebRTC `coturn` + WCAG 2.2 AA+ Civic Voice UI (`index.html`)

## Now
- **Specs `003–004` branch:** `feat/v4-specs-003-004-memory` adds Tamil-script Tanglish, regional landmark matching, session slot memory, and browser turn cancellation. The workflow retains out-of-fixture locations while asking for ward verification. Verified with 74 pytest tests and 31 golden cases.
- **Round 1 Cleared (`3 of 3`):** Activity 01, 02, and 03 passed; **Round 2 Build Live** (**Submit by `30 Nov, 11:59 pm`** · Theme: *Public infrastructure and civic services*).
- **Specs `006–008` Merged (`main`):** Implemented 3-tier auto-detect engine (`engine_mode` in `/api/health`), `display_text` vs Tamil-Unicode `tts_text` (`rate="+6%"`), Sarvam `saaras:v4` `codemix`, deterministic `P0` life-safety (`112`/`108`/`101`/`1906`), two-turn HITL seal (`seal_verified_turn`), WCAG 2.2 AA+ Paper White / Dark Mode UI with `140x140px` Tactile Orb, Engine Mode Pill & collapsed `<640px` drawer, and `analytics/eval_gate.py` + `analyze_logs.py`.
- **Verified Main Baseline (`17:30 IST`):** `pytest` -> `50 passed`; `analytics/eval_gate.py` -> `17/17 passed`; `analytics/analyze_logs.py` -> `0` PII leaks across `431` records; `impeccable detect --json index.html` -> `[]`; Playwright QA (`390/768/1440px`) -> `0` errors, `0` overflow, `0` `"wispr"` strings.
- **Remaining for Final Submit (`30 Nov`):** (1) Live browser mic STT/barge-in & Unsloth `gemma-4-E2B` voice QA, (2) `docker compose up --build` CPU-only smoke check, (3) `<=3m` YouTube demo video, (4) 4-section PDF Pitch Deck, (5) Scaler Round 2 submission.

## Standing Architectural Decisions
- **Voice UI Grammar:** Follow `microsoft/voice-agent` minimal Foundry canvas + `TentacioPro/azure-voice-live-agent` `AcousticOrb` state machine; never render multi-field government form walls upfront.
- **Voice Pipeline Choice:** Use **Hybrid Cascaded / ADK `LiveRequestQueue` (`Sarvam Saaras` codemix STT + deterministic Ward/Schema Router + `Sarvam Bulbul` Tamil TTS)** for production rural Tamil/Tanglish accent accuracy and auditability, with `Google ADK` / `Azure VoiceLive` swappable behind `providers.py`.
- **Portal Ethics & Access:** Public schemas only — only `GCC PGRS` (`gccservices.in/pgr/registercomplaints`) is fully open & anonymous on web; `CMWSSB`, `TWAD PUNAL`, `TANGEDCO`, `CM Cell 1100`, `TNPDS` have page-1 OTP/CAPTCHA gates -> bypass safely via official WhatsApp bots, `1100`/`cmcell@tn.gov.in`, and per-field copy cards.

## Entry Points & Links
- [AGENTS.md](AGENTS.md) · [DESIGN.md](DESIGN.md) · [TODO.md](TODO.md) · [LOG.md](LOG.md)
- [specs/INDEX.md](specs/INDEX.md) · [docs/architecture/VOICE_AGENT_ARCHITECTURE.md](docs/architecture/VOICE_AGENT_ARCHITECTURE.md)
- [DEPLOYMENT_AND_ECONOMICS.md](docs/architecture/DEPLOYMENT_AND_ECONOMICS.md) · [PRIVACY_REGULATORY_AND_CONSENT.md](docs/architecture/PRIVACY_REGULATORY_AND_CONSENT.md) · [PRODUCTION_RESILIENCE_EVALS_AND_CASE_STUDIES.md](docs/architecture/PRODUCTION_RESILIENCE_EVALS_AND_CASE_STUDIES.md) · [PAN_BHARAT_CIVIC_PORTALS_AND_MODELS.md](docs/architecture/PAN_BHARAT_CIVIC_PORTALS_AND_MODELS.md)
- [docs/TN_CIVIC_PORTALS.md](docs/TN_CIVIC_PORTALS.md) · [docs/DESIGN_TERMINOLOGY_AND_PORTAL_ACCESS_MATRIX.md](docs/DESIGN_TERMINOLOGY_AND_PORTAL_ACCESS_MATRIX.md)
- Archive note: Keep archival snapshots omitted until `CONTEXT.md > 120 lines` or `TODO.md > 150 lines` (trimmed `md-upkeep` mode).
