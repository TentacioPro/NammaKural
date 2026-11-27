---
name: review-pitch-deck
description: Audit a hackathon or investor pitch deck (PDF, Markdown, or HTML slides) for text-first readability, narrative clarity, judge rubric coverage, and visual discipline. Use before exporting or submitting the final pitch deck PDF.
---
# review-pitch-deck

Perform a read-only, judge-lens audit of a pitch deck — specifically calibrated for hackathon judges who **read the words in the PDF, not the pictures**.

## When to Use

- Reviewing a drafted pitch deck outline, HTML deck, or exported PDF before submission
- Checking whether all 4 mandatory hackathon prompts are answered clearly and persuasively in plain text

## Review Checklist

1. **Mandatory 4-Prompt Rubric Coverage (P0 Check):**
   - *Problem & Solution:* Is the human pain crystal clear (blind, elderly, disabled, non-literate TN citizens vs. complex portals) and tied directly to what the prototype actually does?
   - *Who It Is For & Scale:* Are concrete user segments and realistic TAM/SAM numbers stated as text (not vague adjectives like "huge market")?
   - *Dependencies & Cost/Outage Fallbacks:* Are every STT, LLM, TTS, and transport dependency named explicitly — AND does it clearly explain what happens if they get costly or stop working (3-Tier Auto-Detect Engine: Cloud API -> Local RTX 3050 Gemma-4 -> Offline Deterministic FSM + Outbox Queue)?
   - *Launch Plan:* Is there a realistic, step-by-step path to the first 100 real users (RWAs, blind/elderly NGOs, e-Sevai centers) before institutional scale?
2. **Text-First & Silent-Readability Test (P0 Check):**
   - Can a tired judge read the PDF at 11 PM with zero audio narration and understand every claim in <2 minutes?
   - Flag any critical information trapped inside screenshots or tiny diagram labels.
   - Check slide headlines: Flag generic labels (`"Architecture"`, `"Market"`) and suggest assertion headlines (`"3-Tier Engine Eliminates Vendor Lock-In & Runs Offline on a ₹60k GPU"`).
3. **Clarity & Credibility (P1 Check):**
   - Word budget: 40–80 words per slide for send-ahead PDFs; flag dense paragraphs.
   - Fact-check every metric against the actual repo (e.g., `pytest` count, latency ms, hardware specs, State Packs).
   - Visual hygiene: Max 2 brand colors + 1 accent, high text contrast (`>= 4.5:1`), readable font size (`>= 14pt` body).

## Output Format

1. **Rubric Scorecard:** Pass/Weak/Missing for each of the 4 judge prompts + Readability Score (`/10`).
2. **Slide-by-Slide Redlines:** Exact rewrites for weak headlines, vague claims, or missing fallback details.
3. **Verdict:** `READY TO EXPORT PDF` or `REVISE BEFORE EXPORT`.
