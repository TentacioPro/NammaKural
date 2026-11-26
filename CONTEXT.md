# CONTEXT — NammaKural (*நம்ம குரல்*)

Updated: `2026-11-27 04:54 IST` · Repo: `D:\NammaKural` · Stack: FastAPI (`backend/`) + Unsloth Studio Local LLM (`gemma-4-E2B-it-Q4_K_M`, zero-key fallback) + Open-Canvas Voice UI (`index.html`)

## Now
- **Round 1 Cleared (`3 of 3`):** Activity 01, 02, and 03 passed; **Round 2 Build Live** (**Submit by `30 Nov, 11:59 pm`** · Theme: *Public infrastructure and civic services*).
- **Round 2 Working App Complete:** Zero-key FastAPI backend (`backend/main.py`, `nlu.py`, `state.py`, `llm_bridge.py`) + `Dockerfile` + `docker-compose.yml` (`8000`) + Open-Canvas Voice UI (`index.html`: `Call`/`Mute`/`Cut`, River-Ripple Orb, proactive greeting, `STT & Model` setup modal, live `#particularsStrip`, GPS + runtime attach, Request History + 24h cooldown, Mobile OTP `4829`, Dual-Confirm HITL seal).
- **Local Unsloth Studio LLM Wired:** Auto-detects running Unsloth Studio on `127.0.0.1:8888` (`gemma-4-E2B-it-Q4_K_M`, `NVIDIA-Nemotron-3.5-Bolt-E4B-GGUF`) via `.env` (`UNSLOTH_API_KEY`, gitignored) while falling back instantaneously to `offline-tanglish-engine` when no local server or secret keys exist (Docker-ready).
- **Last Gate (`2026-11-27 04:54 IST`):** `pytest -q` -> `8 passed`; `impeccable detect --json index.html` -> `[]`; Playwright (`file://` + live HTTP `1440px`/`768px`/`390px`) -> `0` console/page/network errors, `0` horizontal overflow.
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
