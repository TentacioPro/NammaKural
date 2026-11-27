# TODO — NammaKural

Legend: `[ ]` open, `[x]` done (`- [x] ~~task~~ (YYYY-MM-DD, agent)`), `[~]` awaiting owner action. Context: [`CONTEXT.md`](CONTEXT.md).

## Objective: Round 1 Portal Submissions (`Cleared`)
- [x] ~~Cleared Round 1 (`Activity 01`, `02`, `03`) & verified live DOM schemas/OTP gates across 6 TN portals in `docs/TN_CIVIC_PORTALS.md` & `docs/ROUND1_SUBMISSIONS.md`~~ (2026-11-27, owner+antigravity)

## Objective: Round 2 Working Prototype (`Submit by 30 Nov 23:59 IST`)
- [x] ~~Build zero-key FastAPI backend (`backend/main.py`, `nlu.py`, `state.py`, `state_packs.py`, `agent_workflow.py`, `llm_bridge.py`, `tts_service.py`, `logger.py`) + `Dockerfile` + `docker-compose.yml` + `turnserver.conf`~~ (2026-11-27, antigravity)
- [x] ~~Deliver sunlit open-canvas Voice Agent UI (`index.html`: River-Ripple Orb, Call/Mute/Cut, 11 neural voices + Test Voice, Tanglish/தமிழ்/EN persona switch, GPS/attach/OTP/24h cooldown/Dual-Confirm HITL, Logs + Past Conversations modals)~~ (2026-11-27, antigravity)
- [x] ~~Fix Unsloth Gemma-4 `reasoning_effort=none` latency (`<0.5s` LLM), `Prabhat` Tamil `NoAudioReceived` fallback, synchronous gesture audio unlock & structured telemetry (`pytest 13 passed`, `impeccable []`, `0` Playwright errors/overflow)~~ (2026-11-27, antigravity)
- [ ] Verify end-to-end live mic STT (Tamil/Tanglish WebSpeech + `/api/stt`), natural back-and-forth turns, and barge-in with human voice in Chromium/Edge
- [ ] Start Docker Desktop and run fresh-clone smoke check `docker compose up --build` (FastAPI `8000` + `coturn` `3478`)
- [ ] Build 4-section PDF Pitch Deck (`Problem+Solution`, `Who/How Many`, `Dependencies/Fallback`, `Launch Plan`) via `open-design` / HTML->PDF
- [ ] Record <=3 minute unlisted/public YouTube demo video (live Tanglish/Tamil voice call -> Ward lookup -> Dual-Confirm HITL -> Portal card)
- [ ] Final single submission on Scaler Round 2 portal (GitHub + YouTube + PDF + optional live link) before `30 Nov 23:59`

## Objective: Voice Quality, Dialect Accuracy & Eval Hardening (`Specs 001–005`)
- [x] ~~`001-foundry-orb-ui`: Minimal Foundry Voice Orb canvas, call timer, `Talk to interrupt`, mute/cut, runtime attach, GPS modal & HITL seal in `index.html`~~ (2026-11-27, antigravity)
- [ ] `002-hybrid-voice-gateway`: Swap in optional `google-adk` `LiveRequestQueue` + Sarvam `Saaras`/`Bulbul` production adapters behind `backend/` interface per [`specs/002-hybrid-voice-gateway/SPEC.md`](specs/002-hybrid-voice-gateway/SPEC.md)
- [ ] `003-accent-tanglish-nlu`: Expand & benchmark 25+ regional dialect complaints (Chennai/Madurai/Kongu/Tirunelveli) to `>=95%` routing accuracy per [`specs/003-accent-tanglish-nlu/SPEC.md`](specs/003-accent-tanglish-nlu/SPEC.md)
- [ ] `004-vad-turn-taking`: Add backchannel allowlist (`seri`/`aama`/`mm-hmm`) vs 3-word barge-in classifier (`enhanced-turn-detection.json` semantics) per [`specs/004-vad-turn-taking/SPEC.md`](specs/004-vad-turn-taking/SPEC.md)
- [ ] `005-telemetry-self-improve`: Export OpenTelemetry spans + HITL correction-diff feedback loop & fault-injection evals per [`specs/005-telemetry-self-improve/SPEC.md`](specs/005-telemetry-self-improve/SPEC.md)
