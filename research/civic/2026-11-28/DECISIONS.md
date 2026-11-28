# Decisions and current state

## Product direction

Use voice to elicit facts and short clarifications for a citizen-reviewed grievance draft. Use text, maps and attachments when they are more precise. The current application remains a citizen-led drafting and handoff tool. The new register is a research artifact and has not changed production routing.

- **Evidence is part of the draft.** The proposed contract identifies the precise public channel, schema version, source date, jurisdiction evidence, valid field constraints, and silent handling of fields the citizen completes directly.
- **Compare before broadening runtime coverage.** Test NammaKural against general-purpose voice plus browsing, a matched-transcript baseline, a same-schema baseline, and text-first intake. The primary outcome is a valid draft for the correct route. Time and effort matter after critical errors are checked. See the product-fit memo for the proposed gates.
- **Coverage has several levels.** A district homepage is a lead. A public agency directory can confirm a contact. Visible form controls show only the constraints observed. A production contract still requires review of conditional rules and scoped, repeatable evidence.
- **Updates require review.** The on-demand audit compares public-page signals and stores a review queue. No recurring schedule or automatic catalog promotion is installed.

## Work already present in this branch

- Voice, typing and consented GPS update one grievance draft. The branch distinguishes road flooding from a pipe fault and asks about flood passability in focused intake.
- The existing local location resolver uses known landmarks and keeps unverified places pending. It does not provide statewide ward geometries.
- Configurable mobile OTP gates the signed-in application. Accounts own their saved drafts and citizen-reported filing references. Real OTP credentials are not part of the repository. Protected government credentials remain with the citizen.
- Telemetry now distinguishes legacy playback timing and browser estimates of end-of-speech-to-playback. Debug can replay golden cases. Traces show redacted stage and outcome metadata.

## Open work

Choose the first few channel and locality combinations for a measured pilot, have a second reviewer verify them, and connect those reviewed schemas to a deterministic validator. Expand public inventory independently of whether a service is ready for live use. Add focused multi-intent fixtures, especially preserving nonurgent issues when a turn also names an urgent hazard. The offline replay of the mixed example produces one electricity draft, so the other draft types remain a gap.
