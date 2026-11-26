---
id: 002
title: Hybrid Voice Gateway (ADK + Sarvam / Gemini / Azure)
status: proposed
effort: high
allowed_paths:
  - backend/**
  - docs/architecture/VOICE_AGENT_ARCHITECTURE.md
---
# 002 Hybrid Voice Gateway (ADK + Sarvam / Gemini / Azure)

## Goal
Implement a thin Python `google-adk` bidirectional gateway (`Runner.run_live()` + `LiveRequestQueue`) inspired by `microsoft/voice-agent/samples/adk_voice_agent` that swaps cleanly between:
1. Primary TN Accent Path (Cascaded): **Sarvam `Saaras` (codemix STT)** -> **Deterministic Ward/Urgency Engine + Fast LLM** -> **Sarvam `Bulbul` (`ta-IN` TTS)**.
2. Realtime S2S Fallback Path: **Gemini Live** or **Azure VoiceLive** behind a shared `BaseLlm` adapter.
3. Desktop Intake Mode: Direct text/Tanglish transcript ingestion from **Wispr Flow**.

## Non-goals
- No heavy LangChain abstraction layers or multi-database memory brokers during Round 2.
- No portal automation bots (login/OTP/CAPTCHA remain untouched per `I1`).

## Interfaces
- `create_voice_provider(mode: "sarvam_cascade" | "gemini_live" | "azure_voicelive") -> BaseLlm`
- Streaming WS events: `client.audio` / `client.text` -> `agent.state` / `agent.clarify` / `agent.hitl_card` / `agent.dispatch_ready`

## Invariants touched
- `I1` (Public schemas only), `I2` (HITL gate before dispatch), `I4` (No secrets or PII logged).

## Tempting but wrong
- Letting an ungrounded S2S model invent Ward numbers, Road IDs, or TANGEDCO complaint numbers instead of calling deterministic lookup tools.

## Acceptance tests
- Provider swap unit tests verify identical `hitl_card` JSON schema across `sarvam_cascade` and `gemini_live` adapters using synthetic fixtures.
