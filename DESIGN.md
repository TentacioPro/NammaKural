# Design System — NammaKural (*நம்ம குரல்*)

<!-- impeccable:design-schema 1 -->

## Visual World & Thesis
**Sunlit Voice-First Civic Companion (Azure Foundry Voice Live Minimalism × Tamil Wayfinding Clarity).**
Inspired directly by `microsoft/voice-agent` (`samples/foundry_voice_webrtc` + Foundry Agent Preview runtime canvas) and `TentacioPro/azure-voice-live-agent` (`AcousticOrb.tsx`), NammaKural replaces static government form walls with one calm light canvas dominated by a reactive acoustic orb, short conversational clarification only when required, urgency-aware triage, and a clean Human-in-the-Loop (HITL) approval gate.

## Color Tokens (`index.html`)
- `--bg-page`: `#F7FAFC` (Sunlit Cool Surface — daylight high-visibility background)
- `--bg-surface`: `#FFFFFF` (Orb Stage, HITL Clarity Card, Outcome Card)
- `--bg-subtle`: `#F0F4F8` / `--bg-mint`: `#E9F7F2` / `--bg-warm`: `#FFF8EC`
- `--ink`: `#0F172A` · `--ink-2`: `#334155` · `--ink-3`: `#5B687A` (Contrast `>= 5.5:1`)
- `--accent`: `#C23B1A` (Chola Vermilion — P1 hazard highlight & focus rings)
- `--teal`: `#0B6B5C` / `--teal-dark`: `#074A40` (HITL approval, verified Ward badges, speaking state)
- `--whatsapp`: `#15803D` (1-Tap Official WhatsApp / Email / Dial actions)
- `--amber`: `#9A5B00` (Clarification / P2 chronic escalation state)

## Typography
- **Latin UI:** `DM Sans` (`400`, `500`, `600`, `700`) with `A+ Text` root scaling (`112.5%`).
- **Tamil Script (*தமிழ்*):** `Anek Tamil` (`500`, `600`, `700`) for balanced legibility alongside Latin Tanglish.
- **Road IDs, Helplines & Timers:** `JetBrains Mono` (`font-variant-numeric: tabular-nums`).

## Voice Agent State Visuals (`AcousticOrb`)
- `idle`: Soft slate harmonic rings (`amp 2.5`)
- `listening`: Active emerald rings (`amp 8.5`, speed `0.036`)
- `thinking`: Amber orbital sweep (`amp 6.5`, speed `0.055`)
- `clarifying`: Warm amber ring + inline disambiguation pills (visible ONLY when a slot/ward is ambiguous)
- `hitl_review` (`critical` override if P1 hazard): Shows `#hitlCard` summary + Urgent/Sentiment pill; keeps `#dispatchSection` locked
- `approved_dispatch`: Green/teal calm glow; unlocks 1-tap WhatsApp / Emergency Dial `1912` / `<1 MB` Tap-to-Mark JPEG stamper / collapsible portal fields

## Round 2 Visual Polish Target (Microsoft Foundry Orb Reference)
- Keep initial `idle` canvas ultra-clean: centered undulating orb + concise state text (`Speaking...` / `Listening...` / `Talk to interrupt` hint) + compact bottom call strip (`Mic | Language/Captions | Waveform/Timer | End/Clear`) + top `+ New` action.
- Preserve strict `2G Lite Mode` (`data-lite="true"` disables ambient radial gradients and canvas animation frames) and `0` horizontal overflow down to `320px–390px`.
