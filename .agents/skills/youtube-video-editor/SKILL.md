---
name: youtube-video-editor
description: Plan, script, and programmatically build YouTube demo videos and Shorts (<= 3 minutes) using Remotion (React) or HeyGen HyperFrames (HTML/GSAP). Use when producing NammaKural's hackathon demo video, kinetic Tamil/English captions, or architecture reveals.
---
# youtube-video-editor

Produce a tight, retention-engineered <= 3-minute YouTube demo video for NammaKural using Remotion or HeyGen HyperFrames.

## When to Use

- Scripting, editing, or captioning the mandatory <= 3-minute hackathon YouTube demo (public or unlisted)
- Building animated title cards, kinetic bilingual subtitles, or 3-tier architecture reveals in HyperFrames or Remotion

## Steps

1. Follow the strict 3-minute hackathon beat sheet (target `2:45–2:55`):
   - `0:00–0:20` **Hook & Problem:** Contrast a cluttered civic portal form with an elderly/blind citizen tapping NammaKural's giant tactile orb and speaking Tanglish.
   - `0:20–1:25` **Live End-to-End Mobile-First Flow:** Speak Tanglish TNEB/GCC issue -> interrupt mid-sentence (`"niruthunga"`) -> multi-ward disambiguation & mid-call repair (`"illa Anna Arch"`) -> Clarity Popup -> edit/confirm (`"உறுதி"` twice) -> formal petition receipt.
   - `1:25–2:05` **Safety, Privacy & Accessibility:** Show P1 live-wire emergency override (`1912`), Pre-LLM PII firewall scrubbing a dummy ID before logs, and high-contrast / screen-reader ergonomics.
   - `2:05–2:45` **3-Tier Resilience & Zero-Key Docker:** Show `docker compose up` booting on CPU with zero keys (Engine Pill: `Offline FSM`), plus local Gemma-4 E2B (~450ms) and Bharat State Packs (`tn`, `ka`, `in_central`).
   - `2:45–2:55` **Close:** Summary + public GitHub repo URL.
2. Engine & Lint Discipline:
   - **HyperFrames:** Follow `motion-doctrine` (continuous motion, GPU-safe `x`/`y`/`scale`/`opacity` transforms only) and run `npx hyperframes lint` + `npx hyperframes check`.
   - **Remotion:** Deterministic `useCurrentFrame()` / `interpolate()` / `spring()`; zero `Date.now()` or unseeded `Math.random()`.
3. Audio & Captions:
   - Normalize audio to `-14 LUFS`.
   - Burn high-contrast English + Tamil captions in the bottom safe zone so muted judges still follow 100% of the Tanglish dialogue.

## Gotchas

- Never exceed 3:00.
- Always show the mobile viewport (`390x844`) prominently to prove mobile-first accessibility.
