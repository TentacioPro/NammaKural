---
id: 001
title: Foundry Voice Orb Minimal UI
status: active
effort: medium
allowed_paths:
  - index.html
  - DESIGN.md
---
# 001 Foundry Voice Orb Minimal UI

## Goal
Refine the initial idle/listening canvas in `index.html` to match the pure Microsoft Foundry Voice Live aesthetic (`Speaking...`, `Talk to interrupt` barge-in hint, minimal bottom control strip with Mic / Captions / Call Timer / End, top-right `+ New`), while retaining sunlit accessibility (`A+ Text`, `2G Lite`) and the mandatory HITL gate.

## Non-goals
- Do not restore the upfront `Full Form View` or government portal table grids.
- Do not add heavy frontend frameworks or external orb packages that bloat initial load past 2G thresholds.

## Interfaces
- `AcousticOrb` canvas states: `idle | listening | thinking | clarifying | hitl_review | approved_dispatch | speaking | critical`
- Bottom control strip actions: `toggleMic()`, `toggleCaptions()`, `clearSession()`, `speakTamilConfirmation()`

## Invariants touched
- `I2` (HITL gate required before dispatch), `I6` (`impeccable detect` = `[]`, `0` console errors, `0` overflow), `I7` (Anti-reference UI).

## Tempting but wrong
- Putting form inputs above the fold "just in case speech fails" — keep text input compact (`Wispr Flow bar`) and secondary actions behind post-approval disclosure.

## Acceptance tests
- `impeccable detect --json index.html` returns `[]`.
- Playwright checks `idle -> clarifying -> hitl_review -> approved_dispatch` with `0` console errors and `0` overflow at `1440px`, `768px`, and `390px`.
