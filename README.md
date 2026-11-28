# NammaKural · நம்ம குரல்

NammaKural is a Tamil and Tanglish civic grievance intake and drafting app for Tamil Nadu, built for **Scaler × Wispr Flow: Build for Bharat**. A resident can describe an incident by voice or text, clarify its location, optionally share a browser GPS fix, and review a draft for the appropriate public channel. The resident completes any agency verification and submits through that channel.

This README describes the `voice/streaming-latency-v1` branch. The default app is the React Voice Studio served by FastAPI after a frontend build. The deterministic workflow runs on a CPU without API keys. Real SMS sign-in, cloud speech, and external tracing each require configuration.

## Contents

- [Run locally](#run-locally)
- [What the resident can do](#what-the-resident-can-do)
- [How a turn moves through the system](#how-a-turn-moves-through-the-system)
- [Public channels and statewide research](#public-channels-and-statewide-research)
- [Telemetry, traces, and evaluation](#telemetry-traces-and-evaluation)
- [Repository map](#repository-map)
- [Current limits and continuation](#current-limits-and-continuation)

## Run locally

- **One command.** With Docker running, use the command below and open [Voice Studio](http://localhost:8000). The Docker build compiles React and bundles it with FastAPI. Compose publishes port 8000 and stores runtime files under `/app/logs` in a named volume. The base service runs on a CPU and works without keys. [Dockerfile](Dockerfile) · [Compose](docker-compose.yml)

  ```bash
  docker compose up --build
  ```

- **Without Docker.** Use Python 3.11 and Node.js 22 to match the Docker build. From the repo root, create and activate a Python virtual environment, then run the following. Open [the app](http://localhost:8000) and check [API health](http://localhost:8000/api/health). When the SPA build is absent, FastAPI falls back to the original single-page prototype. [Python dependencies](requirements.txt) · [Frontend scripts](frontend/package.json) · [FastAPI entry point](backend/main.py)

  ```bash
  python -m pip install -r requirements.txt
  npm --prefix frontend ci
  npm --prefix frontend run build
  python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
  ```

- **Frontend development.** Keep FastAPI on port 8000 and run `npm --prefix frontend run dev` in a second terminal. Open the URL printed by Vite. Its proxy forwards API, WebSocket, and static asset requests to the local backend. [Vite proxy](frontend/vite.config.ts)
- **Engine options.** Typed intake works with the deterministic `offline_fsm` engine. Browser speech recognition and device or Edge voices depend on browser and network support. Configure `SARVAM_API_KEY` for the Saaras and Bulbul speech paths. For optional conversational generation, configure an OpenAI-compatible endpoint using `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`, or use a supported local Ollama or Unsloth Studio model. Emergency triage and handoff checks run in code. [Settings template](.env.example) · [Engine selection](backend/llm_bridge.py) · [Speech synthesis](backend/tts_service.py)
- **Optional account gate.** Configure a Supabase project with phone sign-in and an SMS provider, then set `NK_SUPABASE_URL` and `NK_SUPABASE_PUBLIC_KEY`. A configured provider enables the gate. Set `NK_AUTH_REQUIRED=1` to require sign-in even if configuration is missing, and use `NK_OPERATOR_IDS` for approved account UUIDs. The Vercel configuration defaults to requiring sign-in. Keep credentials outside Git. [Account access](backend/citizen_accounts.py) · [Settings template](.env.example)
- **Hosted entry points.** The [Vercel ASGI entry point](api/index.py) imports the same FastAPI app. Hosted request history needs persistent storage. The current SQLite history is intended for a backend with a persistent disk or volume. The default Compose service is sufficient for the browser flow. The TURN profile and [experimental voice stack](docker-compose.voice.yml) are separate options. [Vercel config](vercel.json) · [Deployment notes](docs/architecture/DEPLOYMENT_AND_ECONOMICS.md)

## What the resident can do

- **Describe the issue naturally.** Voice and text use the same session draft. A resident can start with a description such as “Velachery bus stand pakkathula mazhaikku appuram road full water,” then add a street, correct the issue type, or switch to typing for a hard-to-pronounce landmark. [Voice Studio](frontend/src/pages/VoiceAgentPage.tsx) · [Intake spec](specs/009-grievance-intake-and-call-telemetry/SPEC.md)
- **Clarify only what is needed.** The workflow retains known facts and asks for missing ones. A correction can switch a pipe-fault interpretation to road flooding. Focused signed-in intake can ask whether a flooded road is passable or how long a Chennai Metro Water problem has lasted. Life-safety cases receive emergency guidance. [Workflow](backend/agent_workflow.py) · [Classification and urgency](backend/nlu.py)
- **Confirm the incident location.** A place can come from a spoken or typed street or landmark. With consent, the browser can send a one-time GPS fix and its accuracy to the same draft. The resolver uses local state-pack evidence. Unsupported places stay unresolved, and a GPS fix does not silently replace a conflicting or verified place. [State-pack loader](backend/state_packs.py) · [Geographic data](state_packs/) · [Location tests](tests/test_grievance_intake.py)
- **Review a channel-specific draft.** The summary shows the issue, incident location, destination, known facts, and pending checks. A citizen may use the channel directory to see public web, phone, email, or WhatsApp options where documented and which fields must be entered directly with the agency. GCC has a dry-run preview packet. A preview ID identifies the draft inside NammaKural. [Draft and preview builder](backend/portal_bridge.py) · [Channel definitions](backend/civic_channels.py)
- **Approve before handoff.** The workflow keeps dispatch preparation behind human confirmation and applies the applicable mobile verification and ward/agency cooldown checks. Signed-in handoff requires server-transcribed spoken confirmation. The demo seal exercises the review without authorizing filing or starting a filing cooldown. The citizen opens the agency channel and completes any portal login, OTP, or CAPTCHA there. [Confirmation and cooldown](backend/state.py) · [Handoff API](backend/main.py)
- **Save and revisit requests.** A signed-in user can save a draft to **My requests** and add a reference received after filing. Account ownership is checked by the server, and external references are citizen-reported. The session draft and saved account history have separate lifetimes. Mobile OTP verifies possession of a phone number through the configured provider. [Citizen screens](frontend/src/pages/CitizenPages.tsx) · [Request storage](backend/citizen_accounts.py)

## How a turn moves through the system

1. **The React client collects input.** With Sarvam configured, the browser records a speech turn and sends it to `POST /api/stt`. Where supported, it can use browser speech recognition. Text and consented location inputs bypass transcription. The browser attaches opaque call and turn IDs to supported requests. [Voice Studio](frontend/src/pages/VoiceAgentPage.tsx) · [Client instrumentation](frontend/src/callTelemetry.ts)
2. **FastAPI invokes the civic workflow.** `POST /api/workflow/turn` processes the input and `GET /api/workflow/draft` retrieves the draft for an available session. The LangGraph workflow checks safety and turn-taking, updates grievance facts, resolves issue and place, chooses a response, and finalizes the structured output. Conversation state can use the local session fallback or configured Redis where supported. [API](backend/main.py) · [Workflow graph](backend/agent_workflow.py) · [Session store](backend/session_store.py)
3. **Deterministic code applies civic rules.** Tamil/Tanglish normalization, urgency tiers, landmark matching, clarification, and confirmation drive the outcome. An optional LLM helps produce conversational replies. The draft builder uses the runtime channel checklist and preserves unresolved checks for review. [NLU](backend/nlu.py) · [Draft builder](backend/portal_bridge.py) · [Live channel checklists](backend/civic_channels.py)
4. **The browser renders the response and plays speech.** The response carries display text and spoken text separately. The client can request streamed audio from `POST /api/tts/stream` and use the configured fallbacks. It records playback timing when measurable. The main React flow uses these HTTP endpoints. Separate WebSocket, RTC, and LiveKit entry points and an async Voice V1 scaffold live alongside it. [TTS service](backend/tts_service.py) · [Realtime adapter](backend/sarvam_realtime.py) · [Voice V1 status](VOICE_V1_REQUIREMENTS_STATUS.md)
5. **The citizen reviews and keeps the result.** The same workflow draft can remain available after the call ends, subject to session availability. Authenticated saves use `/api/requests`. The operator views use redacted outcomes and events from a separate telemetry read path. [Account API](backend/citizen_accounts.py) · [Call telemetry API](backend/call_telemetry.py)

## Public channels and statewide research

- **Live directory.** `/channels` and `GET /api/civic/channels` use the in-code registry for the supported civic routes. It includes Greater Chennai civic services, Chennai Metro Water, TWAD PUNAL, electricity, the CM Helpline and ration services, with guidance about the fields residents complete themselves. [Runtime registry](backend/civic_channels.py) · [Earlier portal inspections](docs/TN_CIVIC_PORTALS.md)
- **Research catalog.** The first pass records **16 routes or service families, 24 official source pages, and 38 district homepages**. Where a public form exposed its controls, the catalog records the observed IDs, field hints and limits. It distinguishes visible controls, login gates, documented channels, older observations, and discovery items. Unknown required fields stay unknown. [Tamil Nadu public catalog](data/civic/tn_public_catalog.json) · [Evidence definitions](specs/011-public-civic-catalog/SPEC.md)
- **Service inventory.** The separate e-Sevai index contains **122 published service codes** compiled from two official lists. It supports discovery and gives researchers source labels. Current service availability and exact application requirements require further confirmation. [e-Sevai index](data/civic/tn_esevai_service_index.json)
- **Repeatable public audit.** The audit validates the register, checks robots policies, fetches registered public pages by HTTPS GET, records fingerprints and visible-control signals, and flags changes for human review. The two archived runs preserve these observations. The audit runs on demand and the research catalog is separate from the live drafting rules. [Audit implementation](ops/audit_civic_catalog.py) · [First snapshot](research/civic/2026-11-28/sources/first-audit.json) · [Second snapshot](research/civic/2026-11-28/sources/second-audit.json)

  ```bash
  python ops/audit_civic_catalog.py --validate
  python ops/audit_civic_catalog.py --baseline research/civic/2026-11-28/sources/second-audit.json --output scratch/civic-audit/current.json
  ```

## Telemetry, traces, and evaluation

- **Telemetry (`/telemetry`).** Review call outcomes, usage and latency cohorts, sample sizes, build identity when available, and a selected call. The page refreshes from `GET /api/telemetry/runs` every five seconds when live refresh is enabled. Browser measurements are sent to `POST /api/telemetry/browser`. [Telemetry page](frontend/src/pages/TelemetryPage.tsx) · [Call aggregation](backend/call_telemetry.py)
- **Traces (`/traces`).** Inspect redacted correlated turn events for available stages and outcomes. Joining relies on opaque call and turn IDs. Older records commonly lack those IDs, so historical aggregates retain their own measurement labels and cannot be reconstructed into complete traces. [Traces page](frontend/src/pages/TracesPage.tsx) · [Structured logger](backend/logger.py)
- **Latency interpretation.** Post-transcript timing starts at transcript submission and ends at browser playback start. The speech-stop-to-playback estimate is a separate, conditional browser measurement. Where instrumentation exists, endpoint wait, recognition, workflow, synthesis and playback help explain the overall result. The archived live conversation covered 13 exchanges over roughly 175 seconds of observed activity and measured **828 ms median post-transcript playback**. Earlier samples lacked reliable build attribution. [Archived measurement notes](research/civic/2026-11-28/telemetry/README.md)
- **Debug (`/debug`).** Run deterministic text cases through `POST /api/ops/evaluate` and inspect the results. This measures behavior such as issue routing, clarification, urgency, and correction. The cases do not call a paid model and their latency is separate from live voice. [Debug page](frontend/src/pages/DebugPage.tsx) · [Golden fixtures](analytics/golden_cases.jsonl) · [Eval runner](analytics/eval_gate.py)
- **External tracing.** The operator pages are built into NammaKural. Phoenix is separate and requires a running collector plus `OTEL_EXPORTER_OTLP_ENDPOINT` or `PHOENIX_COLLECTOR_ENDPOINT` for the applicable exports. The default Compose service does not start Phoenix. [OTLP exporter](backend/telemetry.py) · [Phoenix evaluation utility](analytics/phoenix_eval.py)
- **Shareable evidence.** The research handoff includes **2,129 redacted historical events** and synthetic cases for the observed intake defects. Routine local logs and account storage under `logs/` are private. The export uses an allowlist for timing, usage, and workflow labels. Private transcripts, coordinates, identity data, and credentials stay out of the shared data. [Telemetry archive](research/civic/2026-11-28/telemetry/) · [Export utility](ops/export_cloud_telemetry.py)
- **Verification baseline.** The archived implementation passed **139 pytest tests and 33 golden cases**. The frontend build and responsive Chromium checks were also run during branch development. Install Playwright and its browser before running the full suite locally. Use an offline demo environment for repeatable evals. [Tests](tests/) · [Evaluation spec](specs/008-tdd-eval-gate-and-analytics/SPEC.md) · [Work log](LOG.md)

  ```bash
  python -m pip install playwright
  python -m playwright install chromium
  python -m pytest -q
  python analytics/eval_gate.py --golden analytics/golden_cases.jsonl
  npm --prefix frontend run build
  ```

## Repository map

| If you want to… | Start here | Then follow |
| --- | --- | --- |
| Understand what shipped and what is open | [Current context](CONTEXT.md) | [Specs index](specs/INDEX.md), [task list](TODO.md), [work log](LOG.md) |
| Change citizen or operator screens | [React routes](frontend/src/App.tsx) | [Page components](frontend/src/pages/), [styles](frontend/src/styles.css), [design guide](DESIGN.md) |
| Inspect the original UI | [Legacy prototype](index.html) | [Orb spec](specs/001-foundry-orb-ui/SPEC.md), [legacy accessibility spec](specs/007-universal-a11y-civic-ui/SPEC.md) |
| Trace a complaint from input to draft | [FastAPI entry point](backend/main.py) | [Workflow](backend/agent_workflow.py), [NLU](backend/nlu.py), [state packs](state_packs/), [portal bridge](backend/portal_bridge.py) |
| Change sign-in, approval or saved history | [Citizen accounts](backend/citizen_accounts.py) | [Confirmation state](backend/state.py), [citizen access spec](specs/010-citizen-access-and-operator-review/SPEC.md) |
| Change the public channel guidance | [Live channel definitions](backend/civic_channels.py) | [Public catalog](data/civic/tn_public_catalog.json), [portal evidence](docs/TN_CIVIC_PORTALS.md), [catalog audit](ops/audit_civic_catalog.py) |
| Investigate audio or voice transport | [Voice architecture](docs/architecture/VOICE_AGENT_ARCHITECTURE.md) | [Speech service](backend/tts_service.py), [realtime adapter](backend/sarvam_realtime.py), [Voice V1 scaffold](VOICE_V1_SCAFFOLD.md) |
| Measure a change or reproduce a failure | [Golden cases](analytics/golden_cases.jsonl) | [Tests](tests/), [log analytics](analytics/analyze_logs.py), [telemetry archive](research/civic/2026-11-28/telemetry/) |
| Deploy or review operating constraints | [Compose](docker-compose.yml) | [Settings template](.env.example), [deployment and economics](docs/architecture/DEPLOYMENT_AND_ECONOMICS.md), [privacy and consent](docs/architecture/PRIVACY_REGULATORY_AND_CONSENT.md) |
| Resume the research on a cloud agent | [Cloud handoff](research/civic/2026-11-28/README.md) | [Decisions](research/civic/2026-11-28/DECISIONS.md), [subagent handoff](research/civic/2026-11-28/SUBAGENT_HANDOFF.md), [repo instructions](AGENTS.md) |
| Understand the hackathon and product origins | [Round 1 submissions](docs/ROUND1_SUBMISSIONS.md) | [Product brief](PRODUCT.md), [design guide](DESIGN.md) |

## Current limits and continuation

- **Statewide discovery and draft readiness are different measurements.** The catalog has district discovery links and public evidence. Ward geometry, conditional or authenticated field rules, and exact downstream acceptance still need locality- and channel-specific validation. The runtime registry is the current drafting input.
- **Multiple independent issues remain open.** The archived mixed grievance replay produced one electricity draft. Preserving the water and drainage issues as separate drafts is an outstanding workflow case. [Decision record](research/civic/2026-11-28/DECISIONS.md)
- **Public-source maintenance is manual after the audit.** The tool produces review candidates, and a reviewer must verify a change before updating the registry. The research handoff records both snapshots and their provenance. [Catalog spec](specs/011-public-civic-catalog/SPEC.md) · [Source snapshots](research/civic/2026-11-28/sources/)
- **Product fit is an open evaluation.** General assistants and text-first intake are credible baselines. The proposed comparison measures usable drafts for the correct verified channel, critical field errors, time, and citizen effort with matched inputs. The research memo preserves the proposed protocol and the evidence gathered so far. [Civic drafter product fit](docs/architecture/CIVIC_DRAFTER_PRODUCT_FIT.md)
- **Cloud handoff.** Start with the dated handoff for the original research brief, source audit snapshots, evaluation findings, implementation limits, and redacted data. Use the specs index for acceptance criteria and the work log for the sequence of branch changes. [Cloud handoff](research/civic/2026-11-28/README.md) · [Specs index](specs/INDEX.md) · [Work log](LOG.md)
