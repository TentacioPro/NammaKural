---
name: tamil-voice-agent-architect
description: Design, build, debug, and test NammaKural, a local-first full-stack Tamil and Tanglish civic voice agent with a 3-tier auto-detect engine (Offline CPU -> Cloud API -> Local GPU). Use when working on backend/agent_workflow.py, backend/nlu.py, backend/state.py, backend/llm_bridge.py, backend/tts_service.py, state_packs/, SmallWebRTC/coturn, or docker-compose.yml.
---
# tamil-voice-agent-architect

Architect and maintain NammaKural's `Code > LLM` Tamil/Tanglish voice pipeline so it runs effortlessly on any judge's CPU-only laptop (`docker compose up`, zero keys), scales via optional Cloud APIs, and runs sovereignly on a local consumer GPU (Dell G15 RTX 3050 4GB/6GB + 32GB RAM).

## When to Use

- Implementing or debugging the 3-Tier Auto-Detect Engine (`Offline CPU -> Cloud API -> Local Gemma-4 E2B`)
- Fixing Tamil TTS prosody (`display_text` vs. `tts_text` Tamil Unicode split + `rate="+6%"`) or Tanglish STT ingestion (`saaras:v4` `codemix` / browser `ta-IN`)
- Modifying the 6-state FSM (`GREET -> DISAMBIGUATE -> CONFIRM_CLARITY -> COOLDOWN_AND_OTP -> HITL_SEAL -> DISPATCH`)
- Enforcing Pre-LLM PII/Aadhaar firewall, DPDP 2023 consent gates, P0/P1 safety overrides, or Bharat State Packs (`state_packs/*.json`)

## Steps

1. Enforce the 3-Tier Auto-Detect Engine in `backend/llm_bridge.py` (never bottleneck to a local GPU):
   - **Tier 1 (Default — Zero Keys, CPU-Only):** `deterministic-tanglish-v1` upgraded with warm colloquial Tamil Unicode replies + Browser WebSpeech (`ta-IN`) + `edge-tts`/Browser TTS.
   - **Tier 2 (Optional `.env` Cloud API):** Any OpenAI-compatible endpoint via `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` (Groq, OpenRouter, Gemini) + optional `SARVAM_API_KEY` (`saaras:v4`, `mode="codemix"` + top-50 TN landmark keyterms).
   - **Tier 3 (Local GPU — Dell G15 Demo / Finale):** Local **Gemma 4 E2B Q4_K_M** (`reasoning_effort: "none"`, ~180-token compacted state) via Unsloth (`:8888`) or Ollama (`:11434`), keeping `docker-compose.yml` strictly CPU-safe (no NVIDIA runtime requirements in default compose).
   - Expose active mode cleanly in `/api/health` (`engine_mode`: `offline_fsm` | `cloud_api` | `local_gpu`) so the UI displays an honest Engine Pill.
2. Eliminate robotic/accented Tamil TTS by splitting `display_text` vs. `tts_text`:
   - Never send Romanized Tanglish (`"Unga complaint sollunga"`) to `ta-IN-PallaviNeural`.
   - Emit `display_text` (Tanglish/bilingual for screen) and `tts_text` (strictly colloquial *Kodunthamizh* in Tamil Unicode script, e.g., `"உங்க ஏரியாவுல கரண்ட் கட் ஆயிடுச்சா?"`) with `rate="+6%"` in `edge_tts.Communicate`.
   - Maintain the `en-IN -> ta-IN` guard whenever Tamil Unicode appears.
3. Enforce `Code > LLM` invariants on every turn:
   - Run `scrub_pii_and_aadhaar()` and DPDP consent checks BEFORE any LLM call or JSONL log write.
   - Run `classify_semantic_vad()` to ignore backchannels (`seri`, `aama`, `mm-hmm`, `சரி`, `ஆமா`) and honor barge-in (`stop`, `wait`, `niruthunga`, `நிறுத்து`).
   - Prefer Bharat-Safe models (`gemma-4`, `nemotron`, `phi-4`, `sarvam`, `llama`); explicitly exclude `qwen` and `deepseek`.
   - Keep `P0` (life safety: fire/medical/gas -> `112`/`108`/`101`/`1906`) and `P1` (live wire/spark -> `1912`) deterministic and cooldown-exempt.

## Gotchas

- Never add GPU/NVIDIA device reservations to the default `docker-compose.yml`; judges run on CPU-only laptops.
- Never allow single-breath double confirmation (`"aama uruthi"`); require two distinct VAD turns or Clarity Popup OK + one spoken confirmation.
- For optional live hosting, inject cloud API keys only via server environment variables — keep the public GitHub repo 100% key-free.
