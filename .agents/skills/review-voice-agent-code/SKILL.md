---
name: review-voice-agent-code
description: Perform a strict, read-only code and architecture review of a voice agent codebase (FastAPI, Pipecat/WebRTC, STT/LLM/TTS, Docker). Use after implementing features or before hackathon submission to catch zero-key Docker traps, GPU lock-in, PII leaks, TTS accent bugs, and FSM regressions.
---
# review-voice-agent-code

Conduct a read-only, severity-ranked code review tailored specifically to voice agents and NammaKural's `Code > LLM` invariants. Do NOT edit files during review — return structured findings (`P0-Blocker`, `P1-Important`, `P2-Minor`) with exact file paths and line numbers.

## When to Use

- Before merging a major change or cutting the final hackathon submission commit
- After an AI coding agent edits `backend/`, `index.html`, or `docker-compose.yml`
- Auditing whether a CPU-only judge machine can boot the repo with zero secret keys

## Review Checklist

1. **Zero-Key & CPU-Only Judge Boot (P0 Check):**
   - Inspect `docker-compose.yml` and `Dockerfile`: Flag any mandatory GPU/NVIDIA runtime, hardcoded `localhost:8888` crash, or missing default env vars.
   - Verify `README.md` clearly alerts judges to the 3 runtime modes (`Offline CPU`, `Optional Cloud API`, `Local GPU Specs`).
   - Verify `/api/health` exposes the active `engine_mode` and the UI displays an honest status pill without crashing when keys are absent.
2. **Voice Pipeline & Tamil/Tanglish Integrity (P0 Check):**
   - Check `backend/tts_service.py` and `backend/agent_workflow.py`: Flag any Romanized Tanglish (`"unga"`, `"sollunga"`) leaking into `tts_text` or any Tamil Unicode hitting `en-IN` voices.
   - Check `backend/llm_bridge.py`: Verify `reasoning_effort: "none"` for Gemma-4, Bharat-Safe model filtering (no `qwen`/`deepseek`), and clean fallback to `deterministic-tanglish-v1`.
   - Check async discipline: Flag any blocking disk I/O or synchronous HTTP call inside the live WebSocket/voice loop.
3. **Safety, Privacy & `Code > LLM` Discipline (P0 Check):**
   - Confirm `scrub_pii_and_aadhaar()` executes BEFORE any LLM call and BEFORE `log_event()` / `save_conversation_turn()`.
   - Confirm `P0`/`P1` safety emergencies bypass cooldowns deterministically.
   - Confirm Dual-Confirm HITL seal cannot be bypassed in a single breath or by LLM hallucination.
4. **Tests & Real Behavior (P1 Check):**
   - Verify tests assert real behavior (not trivial mocks) and cover both happy paths and failure/fallback paths.

## Output Format

1. **Strengths:** 2–3 concrete things done well (with file:line references).
2. **Issues (`P0-Blocker` -> `P1-Important` -> `P2-Minor`):** Exact file:line, root cause, and concrete fix recommendation.
3. **Ship Verdict:** `READY TO SUBMIT` or `BLOCKED (Fix P0s first)`.
