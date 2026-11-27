# Deployment Options, Unit Economics & Inference Engineering — NammaKural

> Deep research grounded in verified cloud GPU, SaaS voice AI, Indian CPaaS telephony pricing, and modern LLM inference optimization (`vLLM`, quantization, VAD duty-cycling, prompt/audio caching) across **`10,000`** and **`50 Lakh (5,000,000)`** citizen users.

---

## 1. Call Profile Assumptions (Tamil Nadu Civic Grievance Calls)

Unlike 30-second transactional OTP bots, real citizen calls involve background traffic noise, accent corrections, multi-ward clarifications, and HITL read-back:
- **Average call duration (`Baseline`):** `3 minutes` (~`50%` active citizen/agent speech via Silero VAD gating, ~`600–800` agent characters spoken).
- **Heavy call duration (`Worst Case`):** `8 minutes` (dialect mishearing, multi-landmark correction loop *"illa Anna Arch pakkam"*, photo/bill explanation, Tamil read-back).
- **Conversion reference:** `1 USD ≈ ₹85` (exact published USD and INR quotes shown side-by-side).

---

## 2. Published Component & Platform Unit Pricing

| Layer / Provider | Pricing Model | Verified Published Rate | Key Caveat for Civic Scale |
|---|---|---|---|
| **Sarvam `Saaras` / `Saarika` STT** | Audio minute | **`₹0.49 / min`** (excl. GST); *Sarvam Dictate:* `₹0.50 / min` | Purpose-built for code-mixed Indian languages & street speech |
| **Sarvam `Bulbul` TTS** | Generated character | **v4 Flash:** `₹20 / 10,000 chars` (`~₹2.00 / 1k chars`) · **v3:** `₹3.00 / 1k chars` | Short, crisp Tamil prompts keep per-call chars low (`~600–800 chars`) |
| **Sarvam Voice Agents (Packaged)** | Active interaction minute | **`₹3.50 / min`** pay-as-you-go (`~₹3.00 / min` volume tier) | Bundles STT + LLM + TTS; higher margin than DIY modular |
| **Gemini 2.5 Flash Live Native Audio** | Multimodal audio + text tokens | **Audio In:** `$3.00 / 1M tok` (~`$0.0045/min`) · **Audio Out:** `$12.00 / 1M tok` (~`$0.018/min`) · **Text In/Out:** `$0.50 / $2.00 / 1M tok` | Conversational history resends grow audio-token bills on 8-min calls; Free tier allows model-improvement data logging |
| **OpenAI `gpt-4o-mini-realtime`** | Multimodal audio + text tokens | **Audio In:** `~$10 / 1M tok` · **Audio Out:** `~$20 / 1M tok` · **Est. Audio Call:** `~$0.015–$0.021 / min` | Context amplification + prompt caching dynamics raise multi-turn 8-min spend |
| **ElevenLabs Conversational AI** | Platform minute + external LLM + telco | **`$0.08–$0.10 / min`** platform fee (`~₹6.80–₹8.50/min`) **+ LLM + SIP** | Prohibitive at 50L scale; weak zero-key/offline civic auditability |
| **Exotel (India PSTN)** | Prepaid INR credits (60s pulse) | **Inbound:** `₹0.30–₹0.50/min` · **Outbound:** `₹0.80–₹1.00/min` · DID rental `~₹1,000/mo` | Native TRAI compliance + low-latency `<50ms` AgentStream |
| **Plivo (India PSTN/SIP)** | USD pay-as-you-go | **`₹0.38–₹0.65 / min`** India domestic routes | Lower carrier margin; strict TRAI/DLT compliance required |
| **Twilio (India)** | USD pay-as-you-go | **Inbound Toll-Free:** `₹0.35–₹0.80/min` · **Outbound:** `₹1.20–₹1.50/min` · DID `~₹600/mo` | Restricted local-to-local DID routing in India |

---

## 3. Infrastructure Hosting Pricing (Compute & GPU Options)

| Platform | Hardware / Spec | Verified Hourly Rate | Monthly Cost (`24×7` 1 Instance) | Best Architectural Fit |
|---|---|---|---|---|
| **Google Cloud Run (L4 GPU)** | `1× NVIDIA L4 (24 GB VRAM)`, min `4 vCPU + 16 GiB RAM` | **`$0.67–$0.71/hr`** (GPU component) + vCPU/RAM | `~$550–$650/mo` if 24×7 (**`$0` idle scale-to-zero**) | Burst hackathon / pilot traffic without paying idle GPU cost |
| **AWS EC2 `g6.xlarge`** | `1× NVIDIA L4 (24 GB)`, `4 vCPU`, `16 GiB RAM` | **`$0.80–$0.98/hr`** On-Demand (vs older `g5.xlarge` A10G at `~$1.01/hr`) | `~$585–$715/mo` | VPC-isolated municipal pilot |
| **RunPod Secure Cloud (L4)** | `1× NVIDIA L4 (24 GB)` | **`~$0.59/hr`** (`~$0.44/hr` Community; `~$0.75/hr` serverless) | `~$430/mo` | Dedicated vLLM small-model cluster (`Gemma-4-E2B` / `Qwen3-ASR`) |
| **RunPod Secure Cloud (H100)** | `1× NVIDIA H100 (80 GB PCIe/SXM5)` | **`~$2.89–$2.99/hr`** (`~$1.99/hr` Community; `$4.39–$5.39/hr` serverless) | `~$2,110/mo` | High-concurrency continuous batching at state/city scale |
| **NIC GI Cloud (`MeghRaj`) / MeitY Empaneled GCC** | Sovereign Govt IaaS/PaaS (National Data Centres) | Govt tender / MeitY rate card | State procurement budget | **Mandatory production path** for UIDAI/ADV-linked ULB/TNeGA integration |

---

## 4. End-to-End Cost Comparison: `10,000` Users vs `50 Lakh` (`5M`) Users

*Assumes WebRTC/browser transport (`₹0` telecom leg; add `₹0.30–₹0.50/min` inbound if offering Exotel `1913`/`1100` PSTN dial-in).*

| Architecture | `10k Users × 3 min` (`30,000 min`) | `10k Users × 8 min` (`80,000 min`) | `50 Lakh Users × 3 min` (`15M min`) | `50 Lakh Users × 8 min` (`40M min`) |
|---|---|---|---|---|
| **ElevenLabs + External LLM** | **₹2.04L – ₹2.55L+** | **₹5.44L – ₹6.80L+** | **₹10.2 Cr – ₹12.75 Cr+** | **₹27.2 Cr – ₹34.0 Cr+** |
| **Sarvam Packaged Voice Agent (`₹3–₹3.5/min`)** | **₹90,000 – ₹1,05,000** | **₹2,40,000 – ₹2,80,000** | **₹4.50 Cr – ₹5.25 Cr** | **₹12.0 Cr – ₹14.0 Cr** |
| **Gemini 2.5 Flash Live Native Audio** | **~₹28,700 – ₹51,000** | **~₹76,500 – ₹1.36L+** | **~₹1.43 Cr – ₹2.55 Cr** | **~₹3.83 Cr – ₹6.80 Cr+** |
| **Modular Sandwich + Inference Optimization** *(VAD 50% duty cycle + CDN static TTS 40% cache + compacted state + text LLM)* | **~₹12,000 – ₹22,000** | **~₹32,000 – ₹58,000** | **~₹60L – ₹1.10 Cr** | **~₹1.60 Cr – ₹2.93 Cr** |
| **Self-Hosted vLLM (`H100`/`L4`) Cluster** *(At sustained high utilization + Edge VAD + Cached TTS)* | **~₹5,000 – ₹12,000** *(scale-to-zero L4)* | **~₹14,000 – ₹30,000** | **~₹18L – ₹45L** *(reserved multi-GPU batch throughput)* | **~₹45L – ₹1.15 Cr** |

> **Cost Pile-Up Reality Check:** If you naively stream raw un-gated audio into a cloud Speech-to-Speech API with 8-minute growing conversation history at **50 lakh citizens**, audio + context tokens compound to **₹4–₹13+ Crore**. Converting the pipeline into a **VAD-gated Modular Sandwich + State-Compacted Self-Hosted / Hybrid Cluster** compresses cost by **`65%–85%`** while eliminating foreign vendor lock-in.

---

## 5. Inference Engineering Techniques That Save Latency & Cost

| Technique | Mechanism | Practical Savings / Effect on NammaKural |
|---|---|---|
| **1. Automatic Prefix Caching (`vLLM` RadixAttention)** | Hash-caches the KV states of static system prompts, workflow node rules, and Pydantic tool schemas across turns & concurrent callers. | Cuts **Time-to-First-Token (`TTFT`)** by skipping full prefill recomputation on every turn — critical for 8-min calls with 6+ turns. |
| **2. Continuous Batching (Iteration-Level Scheduling)** | Inserts new citizen transcripts and evicts completed replies at every decoding step rather than waiting for an entire static batch to finish. | Prevents one long bilingual explanation from stalling 15 short disambiguation turns (`"Anna Arch or Tower Park?"`). |
| **3. Quantization (`FP8` Weights + `FP8/INT4` KV Cache)** | Shrinks model weights (`Q4_K_M` / `AWQ` / `FP8`) and compresses the KV cache (token decoding is memory-bandwidth bound). | Fits `Gemma-4-E2B` + `Qwen3-ASR` comfortably on a single `24 GB L4` GPU (`$0.59–$0.71/hr`), boosting concurrent callers per GPU `2–3×`. |
| **4. Speculative Decoding / Asymmetric Routing** | A tiny draft/router model (`1.7B–2B`) drafts tokens or handles routine slot confirmation (`"ok seri"` / ward lookup), reserving larger reasoning models only for ambiguous complaints. | Drops **Inter-Token Latency (`ITL`)** and prevents wasting expensive H100 cycles on simple `"Got Ward 103"` confirmations. |
| **5. Edge VAD Duty-Cycling + CDN Static Audio Cache** | Silero VAD drops silence/noise before STT (`~45–55%` audio reduction); standard Tamil greetings, OTP prompts & HITL confirmation cues play from CDN `.opus` files (`0` TTS cost). | Saves **~50%** of STT/bandwidth cost and **~40%** of TTS character synthesis cost + gives `<100ms` audio start on standard prompts. |
| **6. State Compaction Instead of Raw History Replay** | Replaces 8 minutes of noisy multi-turn transcripts with `{fsm_state, filled_slots, last_2_turns}` (`~180 tokens` fixed window). | Prevents quadratic token cost blowup in long noisy repair conversations. |
