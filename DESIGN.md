# NammaKural voice interface

<!-- impeccable:design-schema 1 -->

NammaKural opens with a voice control and a conversation column. Citizens can report a problem in Tamil, Tanglish, or English and supply a location, correction, or attachment when the agent needs it. Review and dispatch actions appear as the conversation progresses.

## Color and type

| Role | Value |
|---|---|
| Daylight canvas | #FFFFFF |
| Dark canvas | #0B1220 |
| Primary action and idle orb | #1E3A8A |
| Listening | #047857 |
| Checking | #D97706 with dark text |
| Paused and urgent | #B91C1C with white text |

Tamil and English labels have equal weight. Use Noto Sans Tamil when installed and native sans-serif fallbacks for offline rendering. Keep line height at 1.6 and use tabular digits for timers and official identifiers. Focus rings are 3 px and have theme-specific colors.

## Layout and controls

- Below 640 px, a single Type / Photo toggle reveals typing, attachment, location, and voice options. From 640 px, these controls are visible.
- At 768 px and above, the orb and call dock sit left of the transcript and inline complaint review.
- The native 176 px orb uses color, an icon, Tamil and English text, and short audio cues. Listening animation respects the browser’s reduced-motion setting and 2G mode.
- Call, Pause or Resume, and End are 56 px tall. Secondary interactive targets are at least 44 px tall.
- The engine pill reflects API health. The polite voice notice describes browser speech fallback when the optional transcription key is absent.

## Conversation and approval

The transcript updates in a polite live region. Emergency dial guidance and complaint review announcements use assertive live regions. Opening inline review moves focus to its heading and leaves the microphone running. Escape and Close return focus to the review trigger.

After OTP verification, citizens can say the confirmation in two separate spoken turns, or approve the reviewed details and speak it once. Emergency numbers are directly dialable. After filing approval, the citizen chooses the official dispatch action.

Use the workflow’s display text in the transcript and its Tamil speech text for playback. The shell and basic demo flow also run from a local file.
