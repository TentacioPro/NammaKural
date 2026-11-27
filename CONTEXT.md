# CONTEXT — NammaKural (*நம்ம குரல்*)

Updated: `2026-11-27 11:10 IST` · Commit: `775ad5a` (`origin/main`) · Stack: FastAPI (`backend/`) + Pluggable Bharat State Packs (`state_packs/`) + 6-State Tool-Calling Workflow + Unsloth `gemma-4-E2B` / Zero-Key Parity + 11-Voice Neural TTS (`edge-tts`) + Self-Owned WebRTC `coturn` + Sunlit Open-Canvas UI (`index.html`)

## Now
- **Round 1 Cleared (`3 of 3`):** Activity 01, 02, and 03 passed; **Round 2 Build Live** (**Submit by `30 Nov, 11:59 pm`** · Theme: *Public infrastructure and civic services*).
- **Voice, Latency & Observability Live (`775ad5a`):** Defaulted to native Tamil **`ta-IN-PallaviNeural`**, exposed **11 Tamil/Indian voices** in `#quickVoiceSelect` + **`Test Voice`** button, guarded `en-IN` voices against `NoAudioReceived` on Tamil script, added synchronous gesture audio unlock, dropped Gemma-4 turn latency (`~13s -> ~0.44s` LLM / `~2.0s` full tool loop) via `reasoning_effort="none"`, and wired PII-redacted logs (`logs/nammakural.jsonl`) + disk-hydrated past sessions (`logs/conversations.jsonl`) + Tanglish/தமிழ்/EN persona switching.
- **Core Architecture Complete:** Declarative Bharat **State Packs** (`tn`, `ka`, `in_central`), **6-State Tool-Calling Workflow FSM** (`backend/agent_workflow.py`), **Verhoeff Aadhaar & PII Pre-LLM Firewall** + **DPDP 2023 Consent Shield**, and **Self-Owned WebRTC + `coturn`** (`docker-compose.yml`, `/api/rtc/*`).
- **Last Verified Gate (`11:10 IST`):** `pytest -q` -> `13 passed` (`0.51s`); `impeccable detect --json index.html` -> `[]`; live HTTP `/api/health`, `/api/tts/voices` (`11` voices), and Prabhat Tamil TTS fallback -> `200 OK`; Playwright QA (`1440/768/390px`) -> `0` console/HTTP errors, `0` horizontal overflow.
- **Note on Local Daemon:** Restart `uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload` at session start if testing live browser audio/Unsloth (`127.0.0.1:8888`).
- **Remaining for Final Submit (`30 Nov`):** (1) Interactive browser mic/STT/barge-in/accent QA & `003`–`005` eval polish, (2) `docker compose up --build` fresh-clone smoke check, (3) `<=3m` YouTube demo video, (4) 4-section PDF Pitch Deck, (5) Scaler Round 2 submission.

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
