# NammaKural · நம்ம குரல்

> **Tanglish-First Civic Voice Agent, Landmark-to-Ward Resolver & Filing Bridge for Tamil Nadu**  
> Built for **Scaler × Wispr Flow: Build for Bharat**

![NammaKural Pure Voice Agent Preview](https://img.shields.io/badge/Voice_First-Wispr_Flow_%2B_Tanglish-0B6B5C) ![TN Portals](https://img.shields.io/badge/Portals_Mapped-6_TN_Agencies-C23B1A) ![Zero Login Automation](https://img.shields.io/badge/Safety-Public_Schemas_Only-15803D)

---

## Why NammaKural?
Filing a civic complaint in Tamil Nadu means navigating **9+ disconnected portals** (`GCC PGRS`, `CMWSSB Metro Water`, `TWAD PUNAL`, `TANGEDCO CCMS`, `Mudhalvarin Mugavari 1100`, `TNPDS`) with English-only cascading dropdowns (`District -> Zone -> Ward -> Department -> Sub-Category`) and surprise OTP/CAPTCHA gates on Page 1.

Citizens stand on the street and speak in mixed **Tanglish, Tamil, and landmarks**—not bureaucratic Ward IDs:
> *"Anna Nagar Tower Park back side 5th Avenue-la streetlight 5 naala eriyala, transformer wire vera loose-aa spark aaguthu."*

**NammaKural** turns that single breath into verified jurisdiction data and safe dispatch actions:
1. **Pure Voice Agent Canvas (No Upfront Form Wall):** Animated 3-layer harmonic `AcousticOrb` (`idle -> listening -> thinking -> clarifying -> hitl_review -> approved_dispatch`), paired with a single Wispr Flow dictation bar and 5 real-photo street scenarios.
2. **Asks ONLY If Needed:** Automatically detects missing issues, missing locations, or ambiguous multi-ward neighborhoods (e.g., asking `"Vijayanagar Bus Stand (Ward 178) or Phoenix Marketcity (Ward 175)?"` for broad *"Velachery"* inputs).
3. **Sentiment & Urgency Triage:** Elevates live electrical/hazard terms (`spark`, `fire`, `shock`) to **`P1 Critical Safety`** (prioritizing `1912` emergency dial) and chronic/falsely-closed tickets (`fix pannama close pannitanga`, `1100`) to **`P2 High Urgency Escalation`**.
4. **Mandatory HITL Final Clarity Check:** Locks dispatch actions behind an explicit **Confirm Before Dispatch** summary (`Approve & Prepare Dispatch` vs. `Speak / Type a Change`).
5. **Dual Exit Ramps & Evidence Stamper:** Unlocks 1-tap Official WhatsApp bots (`GCC +91 94450 61913`, `CMWSSB +91 81449 30308`, `TWAD +91 94999 91916`, `TANGEDCO 94987 94987`), direct email (`cmcell@tn.gov.in`), emergency helplines, `<1 MB` Tap-to-Mark GIS stamped JPEG photos, conversational `ta-IN` Tamil TTS read-back, `A+ Text`, and `2G Lite Mode`.

---

## Verified TN Portal Coverage & Access Matrix

| Portal / Agency | Helpline | Web Login / OTP | Anonymous Web? | Official WhatsApp / Direct Alternative |
|---|---|---|---|---|
| **GCC PGRS** (Streetlight, Roads, SWD, Garbage) | `1913` | Open on Web (No OTP) | Yes (`Share Mobile: No`) | `+91 94450 61913` |
| **CMWSSB** (Metro Water / Sewage) | `1916` | Page-1 CAPTCHA + OTP | No | `+91 81449 30308` (`200-char` cap) |
| **TWAD PUNAL** (37 Districts Drinking Water) | `1916` | Page-1 Mobile OTP | No | `+91 94999 91916` |
| **TANGEDCO CCMS / Minnagam** (Power & Poles) | `1912` | Image CAPTCHA + OTP | No | WhatsApp `94987 94987` |
| **Mudhalvarin Mugavari** (1100 Escalation) | `1100` | Zoho `/signin` OTP | No | `cmcell@tn.gov.in` & Call `1100` |
| **TNPDS** (Ration Shops / Biometric) | `1967` | Card OTP (`/pages/feedback` open) | No (Mobile req.) | `support@tnpds.com` |

*Strict Policy (`I1`): NammaKural never automates logins, OTPs, or CAPTCHAs.*

---

## Quick Start (One Command via Docker — Zero Secret Keys Required)

`NammaKural` boots cleanly with **zero API keys required** (`offline-tanglish-engine` runs locally; optional `SARVAM_API_KEY` or `GEMINI_API_KEY` in `.env` enables live neural streaming).

### Option A: Docker Compose (Recommended for Judges)
```bash
git clone https://github.com/TentacioPro/NammaKural.git
cd NammaKural
docker compose up --build
# Open http://localhost:8000
```

### Option B: Local Python (FastAPI + Uvicorn)
```bash
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
# Run automated tests:
pytest -q
```

---

## Repository Structure (Spec-Driven MD System)
- [`backend/`](backend/) — FastAPI Voice Agent gateway, Tanglish NLU, Semantic VAD, GPS/Landmark GIS resolver, 24h Ward/Agency Cooldown, Mobile OTP, Dual-Confirm HITL Seal & Redacted OTel Telemetry ([`main.py`](backend/main.py), [`nlu.py`](backend/nlu.py), [`state.py`](backend/state.py))
- [`tests/test_api.py`](tests/test_api.py) — Automated API & gate verification tests (`pytest -q`)
- [`Dockerfile`](Dockerfile) & [`docker-compose.yml`](docker-compose.yml) — One-command key-free startup (`port 8000`)
- [`index.html`](index.html) — Self-contained Pure Voice Agent web frontend
- [`assets/`](assets/) — 5 compressed `800×450` TN civic hazard photos (`<95 KB` each)
- [`AGENTS.md`](AGENTS.md) · [`DESIGN.md`](DESIGN.md) · [`CONTEXT.md`](CONTEXT.md) · [`TODO.md`](TODO.md) · [`LOG.md`](LOG.md)
- [`specs/`](specs/INDEX.md) — Spec-driven Round 2 roadmap (`001` Foundry Orb UI -> `005` Telemetry & Self-Improvement)
- [`docs/architecture/VOICE_AGENT_ARCHITECTURE.md`](docs/architecture/VOICE_AGENT_ARCHITECTURE.md) — Deep dive on Cascaded vs. S2S, Google ADK `LiveRequestQueue`, Sarvam `Saaras`/`Bulbul`, Semantic VAD, OTel & HITL eval loops
- [`docs/TN_CIVIC_PORTALS.md`](docs/TN_CIVIC_PORTALS.md) & [`docs/DESIGN_TERMINOLOGY_AND_PORTAL_ACCESS_MATRIX.md`](docs/DESIGN_TERMINOLOGY_AND_PORTAL_ACCESS_MATRIX.md)
- [`docs/ROUND1_SUBMISSIONS.md`](docs/ROUND1_SUBMISSIONS.md) — Round 1 Activity 01/02/03 workspace
- `codex-experiment/` — Isolated archive of earlier Codex experiment files (kept separate from main prototype)
