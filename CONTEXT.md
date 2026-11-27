# CONTEXT — NammaKural (*நம்ம குரல்*)

Updated: `2026-11-27 21:40 IST` · Branch: `main` · Stack: FastAPI (`backend/` + `api/index.py` Vercel `bom1`) + Pluggable Bharat State Packs (`state_packs/`) + 6-State FSM + RapidFuzz + Redis/Memory `SessionStore` + Sarvam `saaras:v4`/`bulbul:v2` & `edge-tts` + Vite/React/TS SPA (`frontend/`: `/`, `/debug`, `/traces`, `/telemetry`)

## Now
- **Round 2 Architecture & React SPA Shipped (`main`):** Merged `feat/v4-specs-003-004-memory`, decluttered scratch/zip files, added `backend/session_store.py` (Redis + TTL memory + HMAC tokens), `backend/sarvam_realtime.py`, `backend/portal_bridge.py` (`NK-PREVIEW-*` GCC dry-run validator, zero outbound gov requests), `api/index.py` + `vercel.json` (`bom1`), `RapidFuzz` landmark ranking, and Vite/React/TS frontend (`/` Voice Agent, `/debug`, `/traces`, `/telemetry`).
- **Verified Main Baseline (`21:40 IST`):** `npm run build` (`frontend/`) -> `0` TS/Vite errors; `pytest -v` -> `83 passed`; `analytics/eval_gate.py` -> `31/31 passed (100%)`; `analytics/analyze_logs.py` -> `0 PII leaks across 1054 records`; `impeccable detect --json index.html` -> `[]`.
- **Remaining for Final Submit (`30 Nov`):** (1) Set `SARVAM_API_KEY` + `REDIS_URL` in Vercel env & deploy, (2) Live Tamil Nadu handset TTFA & SMS OTP verification, (3) `<=3m` YouTube demo video, (4) 4-section PDF Pitch Deck, (5) Scaler Round 2 submission.

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
