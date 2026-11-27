---
name: nammakural-tdd-evals
description: Write, run, and expand TDD unit tests, behavioral regression gates, Playwright accessibility audits, and JSONL log analytics for NammaKural. Use when adding features, verifying behavioral invariants, analyzing logs/nammakural.jsonl, or running pre-submission quality checks.
---
# nammakural-tdd-evals

Maintain zero-regression quality across NammaKural's voice, NLU, 3-tier engine, privacy, accessibility, and analytics layers using TDD and automated behavioral gates.

## When to Use

- Adding any feature or bug fix (Red -> Green -> Refactor)
- Running `pytest -v`, `tests/test_behavioral_matrix.py`, `tests/test_a11y_playwright.py`, and `analytics/eval_gate.py`
- Inspecting P50/P95 latencies, FSM funnel, and PII firewall stats via `analytics/analyze_logs.py`

## Steps

1. Verify all 6 testing perspectives on every change:
   - **Functional:** 6-state FSM, slot extraction, dual-script NLU, Bharat State Packs, OTP/HITL seals.
   - **Latency/Perf:** Turn latency P95, TTS cache hits, zero-key cold start.
   - **Acoustic/Dialect:** Backchannels (`seri`/`aama`), barge-in (`stop`/`niruthunga`), multi-ward disambiguation, mid-call repair, Tamil Unicode `tts_text` purity.
   - **Accessibility (A11y):** Contrast >= 4.5:1, touch targets >= 44px, `aria-live`, keyboard focus, zero `"wispr"` leftovers.
   - **Security/Privacy:** Pre-LLM PII/Aadhaar firewall, DPDP consent withdrawal, 24h cooldown anti-spam.
   - **Resilience/Failure:** 3-Tier Auto-Detect fallback (`Cloud API -> Local GPU -> Offline CPU`), CPU-only `docker compose up`, `en-IN -> ta-IN` TTS guard.
2. Run the full verification gate before every commit:
   - `pytest -v`
   - `pytest tests/test_a11y_playwright.py -v`
   - `python analytics/eval_gate.py --golden analytics/golden_cases.jsonl`
   - `python analytics/analyze_logs.py --logs logs/nammakural.jsonl --convs logs/conversations.jsonl`
3. Append every manually discovered voice/Tanglish bug to `analytics/golden_cases.jsonl` immediately so it never regresses.

## Gotchas

- Never use real citizen phone numbers or government IDs in test fixtures; use clearly synthetic dummy strings.
- Never claim a task is complete until the verification commands have been executed fresh and passed.
