---
id: 004
title: Street-Noise Semantic VAD & Non-Silent Turn-Taking
status: proposed
effort: medium
allowed_paths:
  - backend/vad/**
  - index.html
---
# 004 Street-Noise Semantic VAD & Non-Silent Turn-Taking

## Goal
Prevent false interruptions from Tamil Nadu street noise (auto-rickshaws, horns, nearby family speech) and eliminate silent "dead air" during GIS/portal lookups using Microsoft `enhanced-turn-detection.json` semantic rules + Google ADK's non-blocking streaming tool pattern (`ResponseScheduling.WHEN_IDLE` / `INTERRUPT`).

## Non-goals
- Do not implement aggressive energy-only VAD cutoffs that cut off elders pausing mid-sentence.

## Interfaces
- `TurnClassifierConfig`: `acknowledgement_phrases` (`mm-hmm`, `seri`, `aama`, `ok`), `interruption_phrases` (`stop`, `wait`, `niruthunga`), `min_interrupt_words: 3`, `end_of_utterance_timeout_ms: 2000`.
- Non-blocking lookup yields an immediate spoken acknowledgement cue before emitting the resolved HITL card.

## Invariants touched
- `I2` (Interruptions must safely reset or amend active HITL summary rather than dispatching stale data).

## Tempting but wrong
- Stopping WebSocket audio frames during silence — ADK `LiveRequestQueue` needs steady low-level ambient audio frames so server VAD stays calibrated.

## Acceptance tests
- Simulated backchannel (`"seri ok"`) during Tamil TTS playback does NOT truncate playback; `"wait anna arch"` (`num_words >= 3` or stop phrase) halts playback within `<150ms` and updates context.
