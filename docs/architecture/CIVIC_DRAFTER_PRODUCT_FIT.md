# NammaKural as a civic intake and drafting agent

Evidence reviewed 28 Nov 2026.

## Positioning

The viable product is a Tamil and Tanglish intake assistant that turns a citizen’s account into a reviewed draft for a specific public grievance channel. It should show which authority owns the issue when the evidence supports that decision, which fields are ready, which facts remain uncertain, and which steps the citizen completes directly. If a general assistant plus the same official sources delivers that outcome with equal effort and accuracy, there is little reason to maintain a separate conversational stack.

### The competition is stronger than the pasted notes suggest

- ChatGPT Live supports natural spoken conversation, web search, and mixed text and images where available. ChatGPT Search can use optional device location. ChatGPT Work’s cloud browser can read pages and enter form data on supported sites, with user participation where sign-in or approval is required. These are credible drafting baselines. Product capabilities vary by account and platform, and their existence establishes no civic accuracy rate. [ChatGPT Voice](https://help.openai.com/en/articles/20001274-chatgpt-voice) · [ChatGPT Search](https://help.openai.com/en/articles/9237897-searching-the-web-with-chatgpt) · [Cloud browser](https://help.openai.com/en/articles/20001280-using-cloud-browser-in-chatgpt)
- Gemini Live supports spoken back-and-forth and interruption, can share screen or camera on supported mobile devices, and can use public Google Maps information. A claim that a general assistant has no practical way to reason about a landmark is too strong. A location result still needs evidence linking it to the responsible ward or agency. [Gemini Live](https://support.google.com/gemini/answer/15274899)
- The state’s CM Helpline already accepts civic grievances in Tamil and English across phone, portal, email, and other channels. It routes complaints and issues acknowledgements. This is a product alternative as well as a fallback. A resident with an unresolved authority may have a shorter path through the official helpline. GCC also advertises direct phone and web intake. [CM Helpline FAQ](https://cmhelpline.tnega.org/portal/en/kb/articles/tamil-nadu-cm-helpline-faqs) · [GCC grievance portal](https://gccservices.in/pgr/home)
- The proposed 90% generic-assistant accuracy, along with the pasted estimates of rejection delay, language-user percentages, and per-call government savings, lacks a measured baseline here. The app already uses an external speech service in its configured path. The statutory text also does not support a general claim that all processing outside India is prohibited. Any deployment assessment must consider applicable rules, notifications, contracts, and the actual data flow. [Current speech path](../../backend/main.py) · [DPDP Act, section 16](https://www.meity.gov.in/static/uploads/2024/02/Digital-Personal-Data-Protection-Act-2023.pdf)

### What the branch can claim

The branch has working checklists and deterministic intake examples, an embedded public landmark catalog, an explicit unresolved-location state, a citizen review flow, and testable call traces. The current draft builder chooses one destination for one grievance intent. The GPS resolver compares against known landmarks. It does not establish statewide ward polygons or citywide street coverage. The isolated Voice V1 path documents its remaining media and PostGIS integration work. The branch does not demonstrate a statewide router, automatic multi-agency splitting, or government receipt verification. [Channel checklists](../../backend/civic_channels.py) · [Draft builder](../../backend/portal_bridge.py) · [Location resolver](../../backend/nlu.py) · [Voice V1 requirements](../../VOICE_V1_REQUIREMENTS_STATUS.md)

An offline replay of the attachment’s synthetic sewage, drinking-water, and sparking-wire example produced one electricity draft with `CRITICAL_SAFETY` urgency. The response prioritized the electrical risk. It produced no separate water or sewage drafts. Use this exact scenario as a benchmark for preserving the other issues after an urgent handoff.

The candidate advantage is a maintained set of channel contracts and jurisdiction evidence, used by a deterministic draft validator. Each contract needs its official source and last review, exact field constraints and conditions where public, citizen-only steps, and a clear unknown when information is behind a gate. A draft should carry the contract version, show fields satisfied from the conversation, and leave uncertain jurisdiction unresolved. Over time, confirmed corrections and failures can improve the contract set and the eval corpus without binding the product to one speech provider. This advantage remains a hypothesis until measured.

## Voice product fit

Voice is a plausible starting point for an incident narrative, local landmarks, onset, effects, and short clarification. The interface can ask one material follow-up at a time, let the citizen interrupt or correct it, and read back the specific issue, location, and destination before review. A static questionnaire that reads every portal field aloud would preserve much of the original burden.

Map choice, GPS consent, photos, precise identifiers, portal-specific attachments, and final review need visible controls and editable text. Account details, passwords, OTPs, and other protected inputs belong in the official channel. Offer a text path from the start and carry draft state across voice, text, and touch. A controlled mobile text-entry study found speech faster in English and Mandarin. It did not evaluate Tamil civic reporting, code-switching, street noise, or task completion, so it motivates testing instead of predicting a result. [Peer-reviewed speech and keyboard study](https://doi.org/10.1145/3161187)

## A fair test before widening coverage

Start with 30–50 paired synthetic scenarios and a small usability pilot with consenting Tamil and Tanglish speakers. Pre-adjudicate the authority, jurisdiction certainty, current channel, required fields, optional fields, and citizen-only fields from the same dated official source set. Include Chennai and non-Chennai cases, adjacent wards, similar landmarks, out-of-coverage places, two simultaneous issues, corrections, street noise, and citizen-gated fields. Keep the adjudicated answers hidden from all systems. Use synthetic identifiers and avoid submitting real complaints.

| Comparison | What it isolates |
|---|---|
| ChatGPT Live or Gemini Live with public research where supported, NammaKural voice, and a competent citizen using the official instructions | The practical end-to-end alternatives. Give each the same incident facts, available map evidence, and time budget. Record product surface and any unavailable tool. |
| Generic assistant and NammaKural with the same reviewed transcript | Whether routing and drafting improve when transcription errors are held constant. |
| Generic assistant supplied the same reviewed schema and source excerpt, versus NammaKural | Whether gains come from maintained data, deterministic checking, fewer citizen corrections, or all three. |
| NammaKural voice-first hybrid versus NammaKural text-first | Whether offering voice lowers effort for the citizens and conditions this product serves. |

Randomize order within the usability pilot and have a reviewer score anonymized drafts without knowing which system generated them. Start timing at the first citizen action and stop at a usable reviewed draft, so research, clarification, transcription repair, and handoff effort count. Practical evaluation criteria follow.

- **Verified usable draft rate.** A draft passes only if the authoritative destination is correct, the jurisdiction is supported at the precision claimed, every observable mandatory field has a valid value or an explicit supported disposition, and all limits and categories match the selected channel. A genuinely unresolved route is counted separately and does not inflate usable-draft rate.
- **Route and field accuracy.** Report routing correctness and mandatory field precision, recall, and exact format validity separately. An acceptable official fallback is scored independently of exact local authority routing. For multi-issue scenarios, score each issue and each destination.
- **Calibrated abstention.** Measure unsupported cases correctly marked unresolved and supported cases unnecessarily blocked. Fabricated official contacts, ward IDs, filing claims, or receipts are critical failures. Record which source version supported each accepted draft.
- **Citizen effort.** Measure median and tail time, turns, retries, manual corrections, and abandonment. Break out the effect of speech errors on civic fields such as place names, counts, times, and negation. Track especially whether voice reduces work without increasing authoritative errors.
- **Operating cost.** Use actual provider usage and invoice rates, plus review and catalog-maintenance time. Report cost per verified usable draft alongside per-call cost. Keep workflow or playback latency distinct from total citizen task time.

A proposed pilot decision rule is zero observed critical failures plus either a 10 percentage-point improvement in verified usable drafts or 25% less median citizen effort at comparable accuracy. These are starting criteria to set before testing, with uncertainty and failures reported alongside any result. If only the data arm wins, make the maintained schema and validator the core product and keep voice as an optional interface. If voice wins in a specific user cohort, invest in that cohort’s real intake conditions before expanding statewide.
