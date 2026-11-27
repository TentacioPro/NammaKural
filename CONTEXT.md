# CONTEXT — NammaKural (*நம்ம குரல்*)

Updated: `2026-11-27 06:28 IST` · Repo: `D:\NammaKural` · Stack: FastAPI (`backend/`) + Pluggable Bharat State Packs (`state_packs/`) + 6-State Tool-Calling Workflow + Unsloth/Zero-Key Fallback + Self-Owned WebRTC `coturn` + Open-Canvas UI (`index.html`)

## Now
- **Round 1 Cleared (`3 of 3`):** Activity 01, 02, and 03 passed; **Round 2 Build Live** (**Submit by `30 Nov, 11:59 pm`** · Theme: *Public infrastructure and civic services*).
- **Intermediate Architecture Complete:** Added declarative Bharat **State Packs** (`state_packs/tn.json`, `ka.json`, `in_central.json` via Pydantic `backend/state_packs.py`), **6-State Tool-Calling Workflow FSM** (`backend/agent_workflow.py`) supporting Bharat-safe LLMs (`Gemma-4-E2B`, `Nemotron`, `Phi-4`, `Sarvam`) + zero-key parity, **Verhoeff Aadhaar & PII Pre-LLM Firewall** + **DPDP 2023 Consent Shield** (`backend/state.py` + `index.html`), and **Self-Owned WebRTC + `coturn` TURN signaling/config** (`docker-compose.yml`, `turnserver.conf`, `/api/rtc/*`).
- **Last Gate (`2026-11-27 06:28 IST`):** `pytest -q` -> `12 passed` (8 API + 4 multi-turn behavioral/guardrail/Aadhaar/state-pack tests); `impeccable detect --json index.html` -> `[]`; `docker compose config --quiet` ok; Playwright (`file://` + live HTTP `1440px`/`768px`/`390px`) -> `0` console/page/network errors, `0` horizontal overflow.
- **Remaining for Final Submit (`30 Nov`):** (1) Test `docker compose up --build` with Docker Desktop started, (2) Record <=3m YouTube demo video, (3) Build PDF Pitch Deck (4 required text sections via `open-design` / HTML->PDF), (4) Submit on Scaler portal.
- **Next Build Phase (Round 2 `27–30 Nov`, submit `30 Nov`):** Wire live audio/Tanglish backend per [`specs/INDEX.md`](specs/INDEX.md) and [`docs/architecture/VOICE_AGENT_ARCHITECTURE.md`](docs/architecture/VOICE_AGENT_ARCHITECTURE.md).

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
