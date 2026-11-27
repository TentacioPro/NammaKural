---
name: review-demo-video
description: Review a product demo video script, Remotion/HyperFrames code, or exported MP4 against hackathon submission rules (<= 3 min), audio loudness, bilingual caption legibility, and technical proof. Use before uploading the final YouTube demo.
---
# review-demo-video

Audit a demo video script, programmatic composition (HyperFrames / Remotion), or rendered cut to guarantee maximum judge impact under the strict 3-minute hackathon limit.

## When to Use

- Reviewing the demo script/storyboard before recording
- Auditing HyperFrames (`npx hyperframes lint` / `check`) or Remotion scene code before rendering
- Performing a final pre-upload QA pass on the YouTube MP4

## Review Checklist

1. **Hard Hackathon Constraints (P0 Check):**
   - Total duration strictly `<= 3:00` (target `2:45–2:55`).
   - Shows the **real working product** (not just slides or mockups).
   - Visibility set to **Public** or **Unlisted** (never Private).
2. **Narrative & Technical Proof (P0 Check):**
   - First 20 seconds clearly hook the problem (accessibility barrier for blind/elderly/illiterate citizens).
   - Demonstrates mobile-first (`390px`) responsive UI with zero Wispr Flow branding.
   - Proves real voice interaction: Tanglish input -> barge-in (`"niruthunga"`) -> Clarity Popup / Dual Confirm -> formal ticket receipt.
   - Proves `Code > LLM` safety (P1 live wire or PII redaction) AND zero-key `docker compose up` resilience.
3. **Audio, Captions & Visual Polish (P1 Check):**
   - Voiceover + agent TTS normalized to `-14 LUFS` with no clipping or background hum.
   - Burned high-contrast bilingual captions (Tamil + English) kept inside bottom safe zones so muted judges understand every turn.
   - For HyperFrames/Remotion code: Zero non-deterministic `Date.now()` / unseeded `Math.random()`, GPU-safe transforms only (`x`, `y`, `scale`, `opacity`), and clean `npx hyperframes lint` / `check`.

## Output Format

1. **Timing & Beat Audit:** Flag any slow segment (`> 10s` without visual change) or risk of exceeding `3:00`.
2. **Audio/Caption/Code Findings (`P0` / `P1` / `P2`).**
3. **Verdict:** `READY TO UPLOAD` or `FIX BEFORE RENDER`.
