---
id: 007
title: Universal WCAG 2.2 AA+ Civic Voice UI & Engine Mode Pill
status: proposed
effort: medium
allowed_paths:
  - index.html
  - DESIGN.md
---
# 007 Universal WCAG 2.2 AA+ Civic Voice UI & Engine Mode Pill

## Goal
Upgrade `index.html` and `DESIGN.md` to a universally accessible (WCAG 2.2 AA+), mobile-first civic voice interface for blind, elderly, motor-impaired, and non-literate citizens, stripping all third-party/Wispr Flow visual DNA and surfacing an honest runtime Engine Mode Pill from `GET /api/health`.

## Non-goals
- Do NOT edit `backend/*.py` or `docker-compose.yml`.
- Do NOT add npm/Vite build steps—keep `index.html` self-contained and working on both `http://127.0.0.1:8000` and `file://`.

## Interfaces
- Header Engine Mode Pill reads `engine_mode` from `GET /api/health` and displays `Mode: Offline FSM (No Key Set)` / `Mode: Local Gemma-4` / `Mode: Cloud API`.
- Tactile State Orb (`>= 140x140px` `<button>`): conveys Idle (`#1E3A8A` + Mic + `பேசுங்க / Speak`), Listening (`#047857` + Ring + `கேட்கிறேன் / Listening`), Thinking (`#D97706` + Pulse + `சரிபார்க்கிறேன் / Checking`), and Paused/Urgent (`#B91C1C` + Pause/Alert + `நிறுத்தப்பட்டது / Paused`) via Color + Icon + Bilingual Label + Web Audio Earcon chime.
- 3-Button Pill Dock (`>= 56px` height, `>= 4.5:1` contrast): `பேசு / Call`, `நிறுத்து / Pause`, `முடி / End`.
- Mobile (`< 640px`): collapse secondary controls behind 1 toggle (`⌨️ Type / 📷 Photo (Optional)`); Tablet/Web (`>= 768px`): 2-column split (Orb+Dock left, Live Transcript + Clarity Popup right).
- Canvas: Paper White (`#FFFFFF`) with 1-tap High-Contrast Dark Mode (`#0B1220`) toggle; zero `"wispr"` strings in DOM/CSS/comments; `aria-live="polite"` for transcripts and `aria-live="assertive"` for Clarity Popups & P0/P1 alerts; never mute mic when Clarity Popup opens.
- Speak `tts_text` (falling back to `reply`) for audio playback while rendering `display_text` (or `reply`) in the transcript.

## Invariants touched
- `I3` (No upfront multi-field form wall)
- `I6` (`impeccable detect --json index.html` -> `[]` + Playwright `0` console errors, `0` horizontal overflow at `1440px`/`768px`/`390px`)
- `I7` (Anti-reference UI rule — no bureaucratic dropdown walls or Wispr branding)

## Tempting but wrong
- Leaving `"wispr"` in CSS custom properties, comments, or placeholders.
- Muting the microphone when the Clarity Popup opens (blocks spoken `"உறுதி"` confirmation).
- Breaking `file://` preview by requiring backend-only assets to render the shell.

## Acceptance tests
- `impeccable detect --json index.html` returns `[]`.
- Playwright check at `390x844`, `768x1024`, `1440x900` passes with `0` console/page errors, `0` horizontal overflow, `>= 44px` touch targets, and `0` occurrences of `"wispr"` in DOM text/attributes.
