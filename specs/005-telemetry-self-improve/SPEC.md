---
id: 005
title: OTel Telemetry, Evals & HITL Self-Improvement Loop
status: proposed
effort: medium
allowed_paths:
  - backend/telemetry/**
  - tests/**
---
# 005 OTel Telemetry, Evals & HITL Self-Improvement Loop

## Goal
Capture OpenTelemetry spans per voice turn (`stt_ms`, `nlu_ms`, `urgency_tier`, `clarify_count`, `hitl_approved`, `hitl_corrected_fields`), grade full conversations using Microsoft Foundry conversation-level rubric + fault-injection controls, and recycle citizen HITL corrections into an anonymized offline test/lexicon improvement loop.

## Non-goals
- Never log raw voice recordings, phone numbers, or addresses containing door numbers (`I4`).
- Never auto-deploy prompt or weight changes without passing the golden regression gate (`offline evals` first).

## Interfaces
- `TraceSpan`: `{ session_id, turn_idx, phase, urgency_tier, resolved_ward, hitl_delta }`
- `EvalCase`: `{ audio_or_text_fixture, expected_agencies, expected_ward, expected_urgency, negative_control }`

## Invariants touched
- `I4` (Zero PII/secrets in traces), `I6` (Verification gate required).

## Tempting but wrong
- Unbounded online self-modification of system prompts in production — use HITL diff collection -> offline golden-set evaluation -> gated release.

## Acceptance tests
- Redacted trace exporter strips phone/email/door patterns before disk/OTel export; evaluation runner catches a deliberately injected wrong-department fault (100% negative control sensitivity).
