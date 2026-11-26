# CONTEXT — NammaKural (*நம்ம குரல்*)

Updated: `2026-11-27 03:48 IST` · Repo: `D:\NammaKural` · Stack: Pure Light HTML5 Voice Agent (`index.html`) + Specs (`specs/`)

## Now
- **Round 1 Status:** `1 of 3 complete` (**Activity 01 Idea**: submitted & quality check passed; **Activity 02 Prompt**: `657 words` ready in [docs/ROUND1_SUBMISSIONS.md](docs/ROUND1_SUBMISSIONS.md); **Activity 03 Impact**: locked until Activity 02 submitted). Hard R1 deadline: **29 Nov 2026, 11:59 pm**.
- **Prototype State (`index.html`):** Refactored into Pure Voice Agent v2 with `AcousticOrb` harmonic canvas (`azure-voice-live-agent` pattern), turn-by-turn slot clarification (`clarifying`), P1/P2/P3 sentiment/urgency triage, mandatory HITL clarity gate (`#hitlApproveBtn`), post-approval 1-tap WhatsApp/1912/photo stamper, `English | தமிழ்`, `A+ Text`, `2G Lite`.
- **Last Gate:** `impeccable detect --json index.html` -> `[]`; Playwright QA (`1440px`/`768px`/`390px`) -> `0` console errors, `0` failed requests, `0` overflow across `idle -> clarifying -> hitl_review -> approved_dispatch`.
- **Immediate Owner Action:** Paste & submit Activity 02 prompt (`657 words`), then unlock and submit Activity 03 (`Impact`) on Scaler dashboard before `29 Nov 23:59`.
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
