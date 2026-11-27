---
name: civic-ai-pitch-deck
description: Create text-first, judge-ready PDF pitch decks for NammaKural and civic AI voice products. Use when drafting or updating the hackathon PDF pitch deck, market sizing, 3-tier engine dependency/fallback analysis, or launch plan.
---
# civic-ai-pitch-deck

Build a crisp, text-first PDF pitch deck where every required judge criterion is readable directly as text (never trapped inside screenshots or diagrams).

## When to Use

- Generating the Round 2 hackathon PDF Pitch Deck (deadline Nov 30, 11:59 PM)
- Covering all 4 mandatory judge sections: Problem & Solution, Who It Is For, What It Depends On (Cost/Outage Fallbacks), and Launch Plan

## Steps

1. Write for a judge reading the PDF silently without you presenting (60–80 clear words per slide, assertion-based headlines, zero walls of text).
2. Cover the 4 mandatory hackathon sections explicitly:
   - **Problem & Solution:** Multi-page English/formal-Tamil civic portals, OTPs, and CAPTCHAs exclude blind, elderly, disabled, and non-literate citizens. NammaKural provides a WCAG-accessible Tamil/Tanglish voice intake agent with `Code > LLM` safety, Clarity Popup + double confirmation (`உறுதி` twice), and automatic formal petition routing.
   - **Who It Is For & Scale:** 7+ crore Tamil Nadu citizens (prioritizing elderly, blind/low-vision, motor-impaired, and rural residents) across 6 civic agencies (GCC, CMWSSB, TWAD, TANGEDCO, CM Cell 1100, TNPDS), expandable nationwide via zero-code JSON Bharat State Packs (`tn.json`, `ka.json`, `in_central.json`).
   - **What It Depends On & 3-Tier Fallback Plan:** List every dependency (STT: WebSpeech / Sarvam `saaras:v4`; LLM: 3-Tier Auto-Detect — Offline `deterministic-tanglish-v1` / OpenAI-compatible Cloud API / Local Gemma 4 E2B Q4_K_M on RTX 3050; TTS: `edge-tts` / Browser TTS / Local Piper; Transport: WebRTC + `coturn`). State clearly what happens if any service gets costly or stops working: swap cloud APIs in 1 config line, drop to a ₹60k local consumer GPU at $0 API cost, or continue running offline via the deterministic Tamil FSM + SQLite outbox queue.
   - **Launch Plan:** Phase 1 hyper-local pilot with Chennai RWAs, blind/elderly NGOs, and e-Sevai centers (first 100 real grievances with HITL verification); Phase 2 TNeGA / Municipal API integration and WhatsApp/helpline complement; Phase 3 multi-state expansion via community State Packs.
3. Back every claim with verifiable proof (zero-key `docker compose up`, hardware specs used for local demo: Dell G15 RTX 3050 4GB/6GB + 32GB RAM at ~450ms/turn, Verhoeff PII firewall, automated `pytest` + Playwright A11y suite).

## Gotchas

- Never put core arguments only inside images; every key point must be selectable PDF text.
- Keep the deck tight (8–11 slides) so a judge can read every word in under 2 minutes.
