# CONTEXT — NammaKural (Scaler × Wispr Flow — Build for Bharat)

Updated: `2026-11-26 17:25 IST` · Repo: `D:\NammaKural` · Dashboard: `https://hackos.scaler.com/wispr/dashboard.html`

## 1. Hackathon Status & Setup
- **Event:** Scaler × Wispr Flow — *Build for Bharat* ("One idea. A voice-first India.").
- **Voice Layer Verified:** Wispr Flow desktop is installed on Windows and already verified on Tamil + Tanglish code-mixed dictation (`2026-11-21`).
- **Round 1 Status:** `0 of 3 complete` — **Activity 01 (Idea)** unlocked (`50–500 words, text only`), **Activity 02 (Prompt)** & **Activity 03 (Impact)** unlock sequentially. Closes **27 Nov** (countdown ends ~midnight `26 Nov`).

## 2. Why `NammaKural` (Evidence & IP Check)
- **Firsthand Problem Observed:** Even a tech-literate office colleague spent hours navigating cascading ward, department, and location dropdowns and poorly designed UI fields just to copy-paste AI-drafted text into a civic grievance portal.
- **Verified Indian Civic Case Studies:**
  1. **Wrong-Department Routing Trap (`CPGRAMS` & Municipal Portals):** Dense central/state/ULB dropdowns make citizens guess jurisdictions (e.g., GCC Electrical vs. TANGEDCO CCMS; GCC SWD vs. CMWSSB), causing weeks-late *"Wrong jurisdiction"* bounces.
  2. **Premature / Stock Closures (`Namma Chennai` PGRS & `Bengaluru Sahaaya`):** Documented complaints/audits of field staff closing unresolved tickets with stock text or generic photos—prompting Bengaluru's **Sahaya 3.0** to push voice filing + regional languages + citizen reopening.
  3. **Language & "Cybercafe Middleman" Divide (`DARPG + Bhashini Samadhan Didi`):** English/formal-text portals force non-English speakers to pay middlemen; *Samadhan Didi* proves institutional demand for voice intake, while Tamil Nadu's 9+ fragmented portals still lack a citizen-side multi-portal router, landmark-to-ward resolver, and field-by-field copy bridge.
- **IP / Name Check (`2026-11-26`):**
  - **`Makkal Kural`** already exists (`tvkapps.com` — Tamil-first grievance/constituency social app) → **avoided**.
  - **`NammaKural`** (*நம்ம குரல்* — "Our Voice") showed no major civic software/patent conflict in web search (note: verify India IP Registry Class 9/42 before any future commercial trademarking).
  - **Differentiation vs. `Makkal Kural` / `Namma Chennai`:** Not another isolated complaint feed—a universal **Tanglish voice-to-portal router, landmark-to-ward resolver, and form bridge** across all existing TN civic sites.

## 3. Core Round 2 Prototype Loop (`27–29 Nov`)
1. **Speak / Dictate (Wispr Flow Tanglish/Tamil/English):** Natural 10s complaint + neighborhood/landmark.
2. **Landmark → District / Zone / Ward Resolver:** Maps spoken area/landmark (or asks 1 quick clarifier if ambiguous) to exact `District → Civic Body → Zone (I–XV) → Ward`.
3. **Multi-Department Splitter:** Splits multi-issue complaints across the right TN portals (e.g., `GCC Electrical` + `TANGEDCO CCMS` or `CMWSSB`).
4. **Field-by-Field Copy Bridge:** Outputs structured fields matching the real TN portal (`Portal URL`, `Helpline`, `Zone/Ward`, `Department`, `Sub-Category`, `Subject`, `Formal English + Tamil Description`, `Missing Info Prompts`) with **1-click Copy** per field.
5. **Anti-Premature-Closure Guard:** Converts a 5s voice update (*"Marked closed, still broken"*) into a formal reopen / **Mudhalvarin Mugavari (`1100`)** escalation draft.

## 4. Reference Docs
- [docs/TN_CIVIC_PORTALS.md](docs/TN_CIVIC_PORTALS.md) — Department-wise Tamil Nadu civic portals, helplines, confusion zones, and form anatomy.
- [docs/ROUND1_SUBMISSIONS.md](docs/ROUND1_SUBMISSIONS.md) — Ready-to-paste Activity 01 draft + Activity 02/03 workspace.
