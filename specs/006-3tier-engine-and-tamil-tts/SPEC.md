---
id: 006
title: 3-tier auto-detect engine, Tamil TTS split, P0 safety & two-turn HITL
status: proposed
effort: medium
allowed_paths:
  - backend/llm_bridge.py
  - backend/tts_service.py
  - backend/agent_workflow.py
  - backend/nlu.py
  - backend/state.py
  - backend/main.py
  - README.md
  - .env.example
  - tests/test_api.py
  - tests/test_agent_behavior.py
---
# 006 3-Tier Auto-Detect Engine, Tamil TTS Split, P0 Safety & Two-Turn HITL

## Goal
Upgrade NammaKural's backend so any judge can boot `docker compose up` on a CPU-only laptop with zero API keys (`offline_fsm`), optionally plug in any OpenAI-compatible Cloud API (`cloud_api`), or run local `gemma-4-E2B-it-Q4_K_M` (`local_gpu`), while fixing robotic Tanglish TTS prosody by separating `display_text` from Tamil-Unicode `tts_text` (`rate="+6%"`), adding deterministic `P0` life-safety routing (`112`/`108`/`101`/`1906`), upgrading Sarvam STT to `saaras:v4` `codemix`, and blocking single-breath double confirmations.

## Non-goals
- Do NOT edit `index.html` or `DESIGN.md` (covered by Spec `007`).
- Do NOT add NVIDIA/GPU device reservations to `docker-compose.yml`.
- Do NOT commit any real API keys or citizen PII.

## Interfaces
- `GET /api/health` -> adds `"engine_mode": "offline_fsm" | "cloud_api" | "local_gpu"` alongside existing `"voice_mode"`.
- `backend/llm_bridge.py`: Tier 2 Cloud API support via `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` (Bharat-safe model filter excluding `qwen`/`deepseek` still enforced).
- `POST /api/workflow/turn` -> returns `"display_text"`, `"tts_text"` (strictly colloquial Tamil Unicode + numeric/acronym tokens, never Romanized Tanglish), `"reply"` (kept for backward compatibility), `"clauses"`.
- `backend/tts_service.py`: `edge_tts.Communicate(clean_text, voice, rate="+6%")` + existing `en-IN -> ta-IN` Tamil Unicode guard.
- `POST /api/stt`: when `SARVAM_API_KEY` is set, call `https://api.sarvam.ai/speech-to-text` with `model="saaras:v4"` and `mode="codemix"`.
- `backend/nlu.py`: `P0` `LIFE_SAFETY` tier (`fire`, `ambulance`, `gas leak`, `electrocution`, `112`, `108`) deterministic & cooldown-exempt before `P1` `CRITICAL_SAFETY` (`1912`).
- `backend/state.py`: `verify_hitl_seal()` rejects single-breath `"Confirm, Confirm"` in `voice_double` mode unless `distinct_turns >= 2` (defaulting safely so existing 2-turn/modal flows work).

## Invariants touched
- `I1` (Public schemas / helplines only)
- `I2` (Dual-confirm HITL & anti-spam guard)
- `I4` (No secrets or PII in repo/logs)

## Tempting but wrong
- Sending Romanized Tanglish (`"Unga complaint sollunga"`) to `ta-IN-PallaviNeural` (causes English/Hindi-accented phoneme fallback).
- Crashing `/api/health` or `/api/workflow/turn` when `UNSLOTH_API_KEY`, `LLM_API_KEY`, or `SARVAM_API_KEY` are unset.
- Allowing `"aama confirm confirm"` in one breath to bypass `voice_double` HITL.

## Acceptance tests
- `pytest -v` passes all existing 13 tests plus new tests for `engine_mode` (`offline_fsm` / `cloud_api` / `local_gpu`), `display_text` vs `tts_text` Tamil purity, `P0` life-safety override, and single-breath HITL rejection.
- `README.md` top section documents CPU-only zero-key `docker compose up`, optional `.env` Cloud APIs, and Dell G15 local GPU demo specs.
