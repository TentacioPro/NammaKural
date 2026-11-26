# CONTEXT — NammaKural (*நம்ம குரல்*)

Updated: `2026-11-27 04:19 IST` · Repo: `D:\NammaKural` · Stack: FastAPI (`backend/`) + Docker Compose (`8000`) + Pure Voice Agent (`index.html`)

## Now
- **Round 1 Cleared (`3 of 3`):** Activity 01, 02, and 03 passed; **Round 2 Build Live** (**Submit by `30 Nov, 11:59 pm`** · Theme: *Public infrastructure and civic services*).
- **Round 2 Working App Complete:** Built zero-key FastAPI backend (`backend/main.py`, `nlu.py`, `state.py`) + `Dockerfile` + `docker-compose.yml` (`port 8000`) + full UI (`index.html`: 3-step onboarding micro-guide, GPS modal + spoken fallback, runtime photo/bill upload, Request History + 24h cooldown guard, Mobile OTP `4829`, Dual-Confirm Tamil HITL seal, WhatsApp/1912/<1MB JPEG stamper).
- **Last Gate (`2026-11-27 04:18 IST`):** `pytest -q` -> `6 passed`; `impeccable detect --json index.html` -> `[]`; Playwright over live Uvicorn (`1440px`/`768px`/`390px`) -> `0` console/network errors, `0` overflow across idle, GPS deny, runtime attach, OTP + Clarity Modal `"உறுதி"`, double-spoken `"உறுதி, உறுதி"`, & Request History. `docker compose config --quiet` ok.
- **Remaining for Final Submit (`30 Nov`):** (1) Test `docker compose up --build` with Docker Desktop started, (2) Record <=3m YouTube demo video, (3) Build PDF Pitch Deck (4 required text sections via `open-design` / HTML->PDF), (4) Submit on Scaler portal.
- **Next Build Phase (Round 2 `27–30 Nov`, submit `30 Nov`):** Wire live audio/Tanglish backend per [`specs/INDEX.md`](specs/INDEX.md) and [`docs/architecture/VOICE_AGENT_ARCHITECTURE.md`](docs/architecture/VOICE_AGENT_ARCHITECTURE.md).

## Standing Architectural Decisions
- **Voice UI Grammar:** Follow `microsoft/voice-agent` minimal Foundry canvas + `TentacioPro/azure-voice-live-agent` `AcousticOrb` state machine; never render multi-field government form walls upfront.
- **Voice Pipeline Choice:** Use **Hybrid Cascaded / ADK `LiveRequestQueue` (`Sarvam Saaras` codemix STT + deterministic Ward/Schema Router + `Sarvam Bulbul` Tamil TTS)** for production rural Tamil/Tanglish accent accuracy and auditability, with `Google ADK` / `Azure VoiceLive` swappable behind `providers.py`.
- **Portal Ethics & Access:** Public schemas only — only `GCC PGRS` (`gccservices.in/pgr/registercomplaints`) is fully open & anonymous on web; `CMWSSB`, `TWAD PUNAL`, `TANGEDCO`, `CM Cell 1100`, `TNPDS` have page-1 OTP/CAPTCHA gates -> bypass safely via official WhatsApp bots, `1100`/`cmcell@tn.gov.in`, and per-field copy cards.

## Entry Points & Links
- [AGENTS.md](AGENTS.md) · [DESIGN.md](DESIGN.md) · [TODO.md](TODO.md) · [LOG.md](LOG.md)
- [specs/INDEX.md](specs/INDEX.md) · [docs/architecture/VOICE_AGENT_ARCHITECTURE.md](docs/architecture/VOICE_AGENT_ARCHITECTURE.md)
- [docs/TN_CIVIC_PORTALS.md](docs/TN_CIVIC_PORTALS.md) · [docs/DESIGN_TERMINOLOGY_AND_PORTAL_ACCESS_MATRIX.md](docs/DESIGN_TERMINOLOGY_AND_PORTAL_ACCESS_MATRIX.md)
- Archive note: Keep archival snapshots omitted until `CONTEXT.md > 120 lines` or `TODO.md > 150 lines` (trimmed `md-upkeep` mode).
