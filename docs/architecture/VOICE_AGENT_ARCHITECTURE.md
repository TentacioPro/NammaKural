# Voice Agent Architecture Blueprint — NammaKural (*நம்ம குரல்*)

> Synthesized from live inspection of **`microsoft/voice-agent`** (`samples/adk_voice_agent`, `samples/foundry_voice_webrtc`, `samples/foundry_evaluation`), **`Azure-Samples/voicelive-webapp`**, **`TentacioPro/azure-voice-live-agent`**, **Google ADK Bidi-Streaming (`adk.dev/live`)**, **Sarvam AI (`Saaras` + `Bulbul`)**, and **6 live Tamil Nadu civic portals**.

---

## 1. Visual Reference Alignment (`Azure Foundry Voice Live UI`)
The minimalist white-canvas purple-orb screenshot (`virtual-finance-demo-mcp` — `Speaking...`, `Talk to interrupt`, timer/waveform bar, `End`, `+ New chat`) comes from **`microsoft/voice-agent`** (`portal/` runtime + `samples/foundry_voice_webrtc`) and **`Azure-Samples/voicelive-webapp`**:
- **Client runtime pattern (`TentacioPro/azure-voice-live-agent` `AcousticOrb.tsx` & `useVoiceAgent.ts`):** `24 kHz` mono PCM16 capture + WebSocket streaming (`client.audio`) + queued `AudioBufferSourceNode` playback (`gateway.audio`) + immediate `<100ms` audio queue purge on barge-in (`gateway.speech_started`).
- **Our NammaKural UI adaptation (`index.html`):** Light sunlit canvas (`#F7FAFC`), 3-layer harmonic `<canvas>` orb tied directly to `AgentState`, single Wispr Flow dictation surface, dynamic clarification ONLY when needed, mandatory **HITL Final Clarity Check (`#hitlCard`)**, and post-approval 1-tap WhatsApp / Emergency `1912` / `<1 MB` Tap-to-Mark JPEG stamper.

---

## 2. Architecture Choice: Cascaded ("Sandwich") vs. Speech-to-Speech (S2S)

| Criterion | Pure Speech-to-Speech (`Gemini Live` / `gpt-realtime`) | Cascaded Pipeline (`STT -> Router/LLM -> TTS`) | **NammaKural Recommended Hybrid** |
|---|---|---|---|
| **Tamil + Tanglish Code-Switching** | Still drops/hallucinates regional TN street names (`Kuruvikaran`, `saakkadai`) and rapid Tamil/English code-switching in noisy audio | **High accuracy** with **Sarvam `Saaras`** (`codemix` mode) or **Wispr Flow** phonetic transcription + Deepgram keyterms | **Primary:** `Wispr Flow` / `Sarvam Saaras` (`codemix`) -> **Deterministic GIS + Urgency Engine** -> **Sarvam `Bulbul` (`ta-IN`)** |
| **Auditability & HITL Clarity Gate** | Black-box audio-in/audio-out makes exact field diffs harder | Exact text transcripts at every boundary for HITL verification | Full bilingual auditability before unlocking dispatch |
| **Hallucination Control (Ward / Road ID)** | Risk of fabricating Ward numbers when responding natively in audio | Strict separation: LLM extracts slots; deterministic GIS index resolves Zone/Ward/Road ID | Zero hallucinated Ward IDs, Road IDs, or helpline numbers |
| **Latency & Interruptibility** | Sub-400ms turn latency | ~700ms–1.1s unless streamed | ADK `LiveRequestQueue` + streaming tools yield `<300ms` first feedback ("Checking Anna Nagar Ward 103...") |

**Bottom Line:** Use **Hybrid Cascaded-First inside an ADK `Runner.run_live()` streaming harness**. Pure S2S (`Gemini Live` / `Azure VoiceLive`) remains available as a provider flag for multimodal fallback, using the exact `providers.py` (`BaseLlm`) swap pattern in `microsoft/voice-agent/samples/adk_voice_agent`.

---

## 3. Do We Need LangChain, LangGraph, ADK, Deepgram, or LiveKit?

| Tool / Framework | Verdict for `NammaKural` | Exact Role |
|---|---|---|
| **Wispr Flow** | **REQUIRED (Core Input)** | Zero-friction desktop/mobile hotkey dictation tuned for spoken Tanglish/Tamil mixed complaints |
| **Google ADK (`google-adk`)** | **USE (Core Runtime)** | `Runner.run_live()` + `LiveRequestQueue` + `RunConfig(StreamingMode.BIDI)` manages async audio queues, non-blocking tool calls, and `Gemini`/`Azure`/`Sarvam` provider swapping |
| **Sarvam AI (`Saaras` + `Bulbul`)** | **USE for Live Audio Mode** | Best-in-class Indian `codemix` Tanglish ASR (`Saaras`) + expressive natural Tamil TTS (`Bulbul`) tuned for telephony & street audio |
| **Deepgram (Streaming STT)** | **OPTIONAL (Keyterm Backup)** | Fast English-heavy streaming STT with keyterm boosting (`TANGEDCO`, `CMWSSB`, Chennai locality names) if Sarvam quota saturates |
| **LiveKit (WebRTC)** | **ROUND 2 SCALE / MOBILE** | Replaces raw WebSocket PCM on patchy 3G Indian mobile networks using adaptive Opus jitter buffers + echo cancellation (`mic -> WebRTC -> ADK worker`) |
| **LangGraph** | **ONLY IF >6 WORKFLOW NODES** | Avoid unless multi-portal appeal retries/conditional follow-up state becomes complex; a 7-state deterministic FSM (`idle -> listening -> thinking -> clarifying -> hitl_review -> approved_dispatch -> speaking`) is faster and easier to debug |
| **LangChain** | **DO NOT USE** | Adds wrapper bloat and latency without helping speech, Tamil NLU, or deterministic portal schemas |

---

## 4. Clean Separation: Model Layer vs. API / Domain Layer

```text
[1. VOICE & TRANSPORT LAYER (Swappable via ADK BaseLlm / WebRTC)]
    Wispr Flow (Hotkey Text) | Sarvam Saaras (codemix STT) | LiveKit Opus | Gemini Live
                                        |
                                        v
[2. CONVERSATION & VAD ORCHESTRATOR (Google ADK Runner.run_live)]
    Semantic VAD -> Backchannel Filter -> Non-Blocking Progress Cues -> Turn State
                                        |
                                        v
[3. TANGILSH / ACCENT NORMALIZATION LAYER]
    Phonetic Matcher ("saakkadai", "eriyala", "thanni varala") + Top-3 Landmark Fuzzy Match
                                        |
                                        v
[4. DETERMINISTIC API / SCHEMA LAYER (Zero LLM Guessing)]
    - Sentinel Urgency/Sentiment Classifier (P1 Critical Safety | P2 Chronic/1100 | P3 Standard)
    - TN GIS Lookup (Chennai ArcGIS EDPMobile2025 FeatureServer + 38 District Templates)
    - Multi-Agency Splitter (GCC PGRS, CMWSSB 200-char, TWAD, TANGEDCO, 1100, TNPDS)
    - Mandatory HITL Clarity Gate -> Locked until Explicit Citizen Approval
                                        |
                                        v
[5. SAFE DISPATCH BRIDGE (Public Schemas Only — Zero OTP/CAPTCHA Automation)]
    WhatsApp Official Bots | 1913 / 1912 / 1916 / 1100 / 1967 Dial | Tap-to-Mark <1MB JPEG | Portal Copy
```

---

## 5. Solving the Hard Problem: Native Tamil Accents & Dialects -> Complaint

Citizens do not say *"Ward 103 GCC Electrical"*; they say *"Tower Park pinnaadi 5th cross-la light 5 naala eriyala, kambi vera spark aaguthu."* Solving this reliably across Madras, Madurai, Kongu, Tirunelveli, and Trichy speech requires 4 stacked defenses:
1. **ASR Code-Mix Mode + Locality Lexicon Biasing:** Run STT in code-mixed `ta-IN`/`en-IN` mode (`Sarvam Saaras` `codemix` or Wispr Flow user dictionary) seeded with high-frequency civic terms (`TANGEDCO`, `PGRS`, `saakkadai`, `kudineer`, neighborhood names).
2. **Phonetic Stem & Dialect Normalization:** Normalize common Tanglish spelling drifts (`saakkadai`/`sakadai`/`drainage`, `eriyala`/`podala`/`light out`, `thanni`/`kudineer`, `kuppai`/`garbage`) and Tamil Unicode synonyms into canonical civic problem tags.
3. **Top-K Ambiguity Disambiguation Instead of Guessing:** Whenever a broad area spans multiple Wards (e.g., *Velachery* spans Wards `175` & `178`; *Anna Nagar* spans `102` & `103`) and no street landmark was mentioned, the agent **asks one concise clarifying question** with 1-tap voice-or-touch landmark pills.
4. **Spoken Audio Read-Back Before Lock-In (`ta-IN`):** Reads back resolved Ward and agency in plain Tamil so elders and low-literacy users verify comprehension by ear.

---

## 6. Managing Reasoning, "Never-Going-Silent", Tone, VAD & Turn-Taking

### Never-Going-Silent Reasoning (Google ADK Blog Pattern)
- **Decoupled Upstream/Downstream:** `LiveRequestQueue` continuously accepts audio buffers while the consumer streams replies (`adk.dev/live`). Never pause ambient frames during silence or VAD calibration drifts.
- **Non-Blocking Tool Execution:** Long GIS lookups or multi-portal schema formatting yield immediate status narration using ADK response scheduling (`WHEN_IDLE`, `INTERRUPT`, `SILENT`) so citizens never hear >800ms of dead air.

### Addressing the Citizen
- Keep spoken prompts short (`<= 18 words`), polite (`நீங்கள்` / respectful Tamil register), and transparent.
- Mirror urgency naturally: calm reassurance for routine outages (`P3`), respectful urgency for `5+ day` neglect/false closures (`P2`), immediate clear warning (*"Stay clear of the live wire — dialing 1912 priority ready"*) for hazards (`P1`).

### VAD & Street-Noise Turn-Taking (`microsoft/voice-agent/samples/foundry_voice_webrtc/enhanced-turn-detection.json`)
- **Semantic VAD (`auto_truncate: true`, `silence_duration_ms: 500`, `end_of_utterance timeout_ms: 2000`):** Handles natural breathing pauses of elders speaking slowly without cutting them off.
- **Backchannel Immunity:** When the assistant is speaking, short acknowledgements (`"ok"`, `"mm-hmm"`, `"seri"`, `"aama"`, `"right"`) are classified as `not_turn` and do NOT interrupt playback.
- **Nearby Bystander Rejection (`num_words >= 3`):** On noisy Indian streets or crowded homes, side remarks to family members trigger `not_turn`; explicit stop phrases (`"stop"`, `"wait"`, `"niruthunga"`) immediately flush queued audio buffers (`<150ms`).

---

## 7. Telemetry, Observability & Recursive Self-Improvement

1. **Privacy-Safe OpenTelemetry (`OTel`):** Log structured per-turn spans (`session_id`, `turn_idx`, `provider`, `stt_latency_ms`, `urgency_tier`, `clarify_triggered`, `resolved_ward`, `hitl_approved`, `hitl_edited_fields`) cleanly redacted of PII (`no phone numbers, no door numbers, no raw audio`). Visualize via **Arize Phoenix**, **Langfuse**, or **Azure Foundry Traces**.
2. **Conversation-Level Eval & Negative Controls (`microsoft/voice-agent/samples/foundry_evaluation`):** Grade full multi-turn trajectories against an explicit rubric (`slot_accuracy`, `multi_agency_split`, `urgency_escalation`, `clarifier_restraint`) and inject negative controls (deliberate wrong-department prompts) to measure detector sensitivity before deployment.
3. **Closed-Loop Recursive Improvement (Offline-Gated):**
   - Every time a citizen edits the HITL Clarity Check (clicks *"Speak / Type a Change"*, switches landmark pill #1 -> #2, or adds a missing phrase), record an anonymized **`hitl_correction_delta`**.
   - Weekly/batch job clusters frequent missed Tanglish terms or mis-mapped landmarks -> appends synthetic regression cases to `eval_fixtures` -> updates phonetic/landmark tables ONLY after passing `>=95%` regression without breaking existing cases.

---

## 8. Anti-Spam, Citizen Verification, Cooldowns & Real Portal Submission

### Preventing Random Tool Calls & Duplicate Complaints
1. **Deterministic Tool Gating (`Code > LLM`):** Dispatch functions (`whatsapp_dispatch`, `webhook_submit`, `pdf_export`) are unreachable by raw LLM output; only `state.agentPhase === "approved_dispatch"` unlocks them.
2. **Citizen Identity (India Compliance):**
   - **Hackathon / Public Rollout:** **Mobile OTP Verification** (matching TN portals' own caller identity model) — never stores raw Aadhaar numbers (UIDAI raw Aadhaar OTP requires licensed AUA/KUA registration; production municipal integrations hook **DigiLocker / API Setu** cleanly).
   - **Telecom-Bound WhatsApp:** Sending via `wa.me` uses the citizen's own WhatsApp SIM number, which Tamil Nadu grievance bots already rate-limit & track natively.
3. **Request History & Department/Ward Cooldowns:**
   - **Request History Log:** Displays prior grievances, ticket IDs (`#GCC-20491`), resolved Ward, timestamp, and status.
   - **Cooldown Lock (`24h` per Citizen × Ward × Agency):** Blocks accidental duplicate filings for the same Ward & Department during cooldown, offering **"Escalate existing ticket to CM Cell 1100"** instead — overridden only when urgency classifies as **`P1 Critical Safety`** (e.g., live sparking wire) with an explicit audit marker.
4. **Dual-Confirm HITL Gate (`Tamil Native Seal`):**
   - **Voice-Only Path:** Reads back Ward + Agency + Cooldown status in `ta-IN`; citizen must affirm the confirmation keyword **twice** (`"உறுதி, உறுதி"` / `"Confirm, Confirm"`).
   - **Dynamic Modal Path:** Opens a Final Clarity Popup showing complete resolved details; citizen reviews, taps **OK**, and speaks **`"உறுதி"` / `"Confirm"`** once in their native Tamil/Tanglish accent to authorize dispatch.

### Real-World Submission Bridge (How Complaints Actually Reach Portals)
- **Public Citizen Channels (Zero Private Credentials Needed):** Open Web schema (`GCC PGRS`), Citizen WhatsApp bots (`GCC`, `CMWSSB`, `TWAD`, `TANGEDCO`), Direct Official Emails (`cmcell@tn.gov.in`, `support@tnpds.com`), and Helplines (`1913`, `1916`, `1912`, `1100`, `1967`).
- **e-Sevai / Booth Operator Mode & ULB API Path:** Mirrors how Tamil Nadu e-Sevai / CSC operators authenticate once per operator session (biometric/TNeGA ID) and submit verified walk-in citizen petitions cleanly — generating operator-ready structured fields & ready for authenticated TNeGA/Zoho Desk REST webhooks when partnered with a municipal body.

