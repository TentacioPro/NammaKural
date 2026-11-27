# Privacy, Data Consent & Regulatory Compliance — NammaKural

> Legal & governance analysis for deploying an AI civic voice agent in India under the **Digital Personal Data Protection (DPDP) Act, 2023**, the **Aadhaar Act, 2016** (UIDAI AUA/KUA guidelines), **NIC `MeghRaj` / MeitY Cloud directives**, and **Tamil Nadu public grievance portal rules**.

---

## 1. DPDP Act, 2023 Roles & Voice Data Classification

When a citizen reports a street problem by voice, the platform captures **audio streams**, **voice characteristics**, **ASR transcripts**, **GPS/street landmarks**, and **mobile numbers**.

| DPDP Concept | NammaKural Civic Mapping | Legal Obligation |
|---|---|---|
| **Data Fiduciary** | Municipal Corporation / State Department (e.g., GCC, CMWSSB, TANGEDCO) deploying the service | Determines purpose & means; carries primary compliance liability (up to **`₹250 crore`** penalty for failure to maintain reasonable security safeguards). |
| **Data Processor** | NammaKural AI software vendor / cloud GPU operator | Processes audio/text strictly under fiduciary instructions; zero independent commercial reuse. |
| **Voiceprints & Recordings** | Acoustic waveform = uniquely identifying biometric/personal data; transcripts + GPS = digital personal data | Cannot be silently scraped, hoarded indefinitely, or shipped to overseas APIs whose free tiers reserve training rights (e.g., Free-tier hosted AI APIs). |
| **Lawful Basis** | **Consent** (private/hackathon pilot) or **"Certain Legitimate Uses"** (State statutory welfare/civic functions) | Even under State legitimate-use exemptions, **notice, purpose limitation, security safeguards, and breach reporting remain mandatory**. |

---

## 2. Five Mandatory Legal & Ethical Safeguards

1. **Pre-Call Bilingual Notice & Explicit Consent (DPDP Sections 5–6):**
   - Before voice capture activates, the agent must inform the citizen in Tamil & English:
     - Interaction is handled by an AI civic assistant.
     - Audio/text is used **strictly** to route & verify their street grievance.
     - Human helpline (`1913` / `1916` / `1912` / `1100`) & Consent Withdrawal remain accessible without penalty.
2. **Purpose Limitation & Anti-Surveillance Boundary:**
   - Citizen street complaints (audio, photos, GPS) cannot be repurposed for municipal surveillance, voter/demographic profiling, or unrelated AI model training unless explicitly opted-in after full PII stripping.
3. **Data Minimization & Live PII Masking (`backend/state.py`):**
   - Citizens naturally blurt out house numbers, family names, or consumer/phone numbers mid-speech.
   - Telemetry spans MUST apply live regex/NER PII redaction (`[REDACTED_NUM]`, `[REDACTED_EMAIL]`) before storing evaluation or self-improvement logs.
4. **Storage Limitation & Post-Resolution Purge:**
   - DPDP mandates **erasure once the specified purpose is no longer served**.
   - Audio buffers should remain **ephemeral in RAM** during the call; post-dispatch logs purge raw transcripts/photos automatically once the grievance reaches closure + statutory audit window.
5. **Section 13 Privacy Grievance Officer & DPBI Breach Notice:**
   - Ironically, a civic grievance agent must **also** expose a privacy grievance channel (Section 13 DPO contact) so citizens can request deletion/correction or complain about AI data handling before escalating to the **Data Protection Board of India (DPBI)**.

---

## 3. UIDAI Aadhaar Act (2016) & Why NammaKural Uses Mobile OTP + DigiLocker Instead

- **Strict Storage Prohibition:** Under UIDAI regulations, **Authentication User Agencies (AUAs)** and **e-KYC User Agencies (KUAs)** are strictly prohibited from storing raw Aadhaar numbers collected during input.
- **Mandatory Aadhaar Data Vault (ADV):** Any permitted Aadhaar/UID token retention must reside in an isolated **HSM-backed AES-256 Aadhaar Data Vault** hosted strictly **on-premises** or inside a **MeitY-empaneled Government Community Cloud (GCC)**.
- **NammaKural Architectural Decision (Invariant I2/I4):**
  - Never prompt for, log, or transmit raw 12-digit Aadhaar numbers.
  - Enforce **Citizen Mobile OTP** (with **24h Ward × Department Cooldown** and **WhatsApp SIM binding**) for public/hackathon builds, cleanly upgrading to official **DigiLocker / API Setu** tokenized verification inside municipal production deployments.

---

## 4. Sovereign Hosting & Government Portal Boundary Compliance

| Boundary Risk | Uncompliant Shortcut (Blocked) | NammaKural Compliant Solution |
|---|---|---|
| **Audio Leaving Sovereign Jurisdiction** | Sending citizen calls to overseas free-tier APIs that retain audio to train global models | **Local / India-Region Deployment:** Self-hosted Unsloth/vLLM or Mumbai/Hyderabad sovereign instances; production state rollout on **NIC `MeghRaj` GI Cloud** / MeitY-empaneled cloud. |
| **Automated CAPTCHA / Govt Login Bypass** | Headless scripts auto-solving CAPTCHAs or holding citizen OTPs to force-submit `CMWSSB`/`TANGEDCO`/`1100` web forms | **Public Schema Bridge (Invariant I1):** Route directly via open web schemas (`GCC PGRS`), verified official WhatsApp queues, helplines, official emails (`cmcell@tn.gov.in`), or authenticated **e-Sevai booth operator assist**. |
| **Hallucinated / Fraudulent Official Filings** | Autonomous LLM submitting complaints to government desks on ambiguous voice input (`Code < LLM`) | **Mandatory Dual-Confirm HITL Gate:** Citizen verifies OTP + confirms twice in Tamil (`"உறுதி, உறுதி"`) or taps Clarity Modal **OK** + `"உறுதி"` before any dispatch tool unlocks. |
