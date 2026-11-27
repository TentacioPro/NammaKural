---
name: voice-agent-a11y-ui
description: Build universally accessible (WCAG 2.2 AA+), mobile-first, clutter-free Voice Agent UIs for blind, elderly, disabled, literate, and illiterate users. Use when editing index.html or migrating to React/Vite, redesigning the voice orb and pill dock, removing Wispr Flow branding, adding the runtime Engine Mode Pill, or building pre/mid/post-conversation Clarity Popups.
---
# voice-agent-a11y-ui

Design and implement NammaKural's universally accessible, mobile-first -> tablet -> web Voice UI so blind, elderly, motor-impaired, and non-literate citizens can file grievances effortlessly — and judges immediately see which runtime engine mode is active.

## When to Use

- Stripping third-party branding (Wispr Flow colors, purple-blue orb, hotkey placeholders) in favor of a daylight-readable Civic High-Contrast Palette
- Upgrading the Voice Orb, 3-Button Pill Dock, and mobile-first responsive layout (`390px`, `768px`, `1440px`)
- Adding an honest Engine Mode Pill (`Offline FSM (No Key Set)` / `Local Gemma-4` / `Cloud API`) and graceful `"API key not set — using Browser Voice"` notices
- Building focus-managed Clarity Popups that support pre-, mid-, and post-conversation edits synced live to the agent

## Steps

1. Keep the proven centered layout (Voice Orb + Status + 3-Button Pill Dock), but upgrade every element for universal accessibility:
   - **Canvas:** Paper White (`#FFFFFF`) with a 1-tap High-Contrast Dark Mode (`#0B1220`) toggle. Zero cream/purple Wispr Flow styling.
   - **Tactile State Orb (`>= 140x140px` tappable `<button>`):** Convey state through **Color + Icon + Bilingual Label + Audio Earcon** (never color alone):
     * Idle: Deep Indigo (`#1E3A8A`) + Mic icon + `பேசுங்க / Speak`
     * Listening: Emerald (`#047857`) + Animated Ring (static meter under `prefers-reduced-motion`) + `கேட்கிறேன் / Listening`
     * Thinking: Warm Amber (`#D97706`) + Pulse icon + `சரிபார்க்கிறேன் / Checking`
     * Paused / Urgent: Crimson (`#B91C1C`) + Pause/Alert icon + `நிறுத்தப்பட்டது / Paused`
   - **3-Button Pill Dock (`>= 56px` height, `>= 4.5:1` contrast even inactive):** `பேசு / Call`, `நிறுத்து / Pause`, `முடி / End`.
2. Eliminate mobile clutter (`< 640px`):
   - Collapse all secondary controls (`Type`, `Attach Photo/Bill`, `Check GPS`, `Voice Selector`, `Test Voice`, `+ New`) behind one clean toggle: `⌨️ Type / 📷 Photo (Optional)`.
   - On tablet/desktop (`>= 768px`), render a 2-column split: Orb + Dock on the left; Live Bilingual Transcript + Mid-Call Clarity Popup on the right.
3. Surface Runtime Engine Transparency for Judges:
   - Read `engine_mode` from `GET /api/health` and display a subtle, high-contrast header badge (`Mode: Offline FSM (No Key Set)` / `Local Gemma-4` / `Cloud API`).
   - If a user triggers an optional cloud feature without keys (e.g., Sarvam STT), show a polite inline banner (`"Sarvam key not set — running Browser Voice (ta-IN)"`) without crashing.
4. Enforce Blind & Screen-Reader Ergonomics:
   - Distinct Web Audio earcon chimes (Listening Start, Thinking, Confirmation Ready, Error).
   - `aria-live="polite"` for transcripts, `aria-live="assertive"` for Clarity Popups and P0/P1 safety alerts, visible 3px focus rings, and `Noto Sans Tamil` with `line-height: 1.6`.
   - Never mute the mic when a Clarity Popup opens; allow inline edit OR spoken `"Confirm"` / `"உறுதி"` to resolve the same state.

## Gotchas

- Never leave any `"wispr"` string in DOM text, placeholders, comments, or CSS tokens.
- Verify zero horizontal overflow at `390x844`, `768x1024`, and `1440x900` using Playwright before shipping.
