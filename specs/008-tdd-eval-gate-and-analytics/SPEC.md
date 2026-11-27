---
id: 008
title: TDD Eval Gate, Playwright A11y Audit & JSONL Log Analytics
status: proposed
effort: small
allowed_paths:
  - analytics/golden_cases.jsonl
  - analytics/eval_gate.py
  - analytics/analyze_logs.py
  - tests/test_a11y_playwright.py
  - tests/test_behavioral_matrix.py
---
# 008 TDD Eval Gate, Playwright A11y Audit & JSONL Log Analytics

## Goal
Provide automated regression gates and telemetry analytics so every commit verifies 12+ golden Tanglish/Tamil civic scenarios, P50/P95 latency & 0-PII-leak invariants on `logs/nammakural.jsonl`, and WCAG 2.2 AA+ responsive layout across `390px`, `768px`, and `1440px`.

## Non-goals
- Do NOT modify `backend/` or `index.html` (read-only verification & offline evals).
- Do NOT include real citizen phone numbers, emails, or Aadhaar numbers in `golden_cases.jsonl`.

## Interfaces
- `python analytics/eval_gate.py --golden analytics/golden_cases.jsonl` -> exits `0` when all golden cases pass against `run_workflow_turn()`.
- `python analytics/analyze_logs.py --logs logs/nammakural.jsonl --convs logs/conversations.jsonl` -> prints P50/P95 latency, FSM state funnel, and PII firewall verification.
- `pytest tests/test_a11y_playwright.py -v` -> starts/connects to app and verifies `390x844`, `768x1024`, `1440x900` viewports, `0` overflow, `0` console errors, Engine Mode Pill, and zero `"wispr"` strings.

## Invariants touched
- `I2` (HITL & anti-spam regression coverage)
- `I4` (Synthetic fixtures only, 0 PII leaks)
- `I6` (Verified Playwright quality bar)

## Tempting but wrong
- Writing Playwright tests that fail to tear down background processes or leave orphan browser sessions.
- Using trivial `assert True` mocks instead of testing real `run_workflow_turn` and live DOM bounding boxes.

## Acceptance tests
- `pytest -v` passes all unit, behavioral, and Playwright A11y tests.
- `python analytics/eval_gate.py --golden analytics/golden_cases.jsonl` exits `0` with `12/12` (or more) passing cases.
- `python analytics/analyze_logs.py --logs logs/nammakural.jsonl --convs logs/conversations.jsonl` exits `0` with clean summary.
