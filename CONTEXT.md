# CONTEXT — NammaKural (*நம்ம குரல்*)

Updated: `2026-11-28 15:05 IST` · Branch: `voice/grievance-e2e-flow-v1` · Stack: FastAPI (`backend/` + `api/index.py` Vercel `bom1`) + Pluggable Bharat State Packs (`state_packs/`) + 6-State FSM + RapidFuzz + Redis/Memory `SessionStore` + Sarvam `saaras:v4`/`bulbul:v2` & `edge-tts` + Vite/React/TS SPA (`frontend/`: `/`, `/debug`, `/traces`, `/telemetry`)

## Now
- Active branch: `voice/grievance-e2e-flow-v1`, created from `voice/streaming-latency-v1` at `cffa1f3`. Read the [end-to-end flow/gap map](docs/architecture/END_TO_END_GRIEVANCE_FLOW_GAP_MAP.md) and [28 November cloud handoff](research/civic/2026-11-28/README.md) for scope, source evidence, telemetry, test limits and open decisions.
- Product direction: Tamil/Tanglish grievance intake and channel-specific draft review. Voice, text and consented GPS share the draft. Mobile OTP requires the configured provider. Filing remains citizen-led.
- First-pass [public source register](data/civic/tn_public_catalog.json): 16 routes or service families, 24 source pages and 38 district homepages. The [e-Sevai inventory](data/civic/tn_esevai_service_index.json) has 122 published codes. These are discovery and evidence records, not proof of statewide drafting coverage.
- The public source audit is on demand. The immediate evaluation target is verified usable drafts and citizen effort against general assistants and text-first intake. Controlled tests have not established a winner.
- Runtime checks before the archive: 134 pytest tests, 33 golden cases, responsive Chromium checks and Compose configuration validation. Raw citizen conversations and credentials are local only.

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
