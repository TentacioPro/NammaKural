---
id: 009
title: Grievance intake and call telemetry
status: done
effort: high
allowed_paths:
  - backend/
  - frontend/src/
  - tests/
  - analytics/golden_cases.jsonl
  - specs/
  - LOG.md
---
# 009 Grievance intake and call telemetry

## Goal

Recognize and correct the grievance type, collect the incident location in the same complaint through speech, typing or a citizen-approved GPS fix, and prepare a reviewable draft that survives ending the call. Show call and turn timing with the build, actual signals and sample boundaries.

## Non-goals

Government login automation, automatic filing, arbitrary live geocoding, persistent GPS tracking, and replacing the audio transport.

## Interfaces

- Workflow turns return a grievance draft with issue, incident location, destination and pending checks. A GPS-only turn takes coordinates and accuracy and uses the same consent-scoped session.
- The Chennai Metro Water draft asks for problem duration when missing. The browser can restore the draft for the same tab while the session is available.
- Voice HTTP requests share opaque call and turn UUIDs. A typed telemetry event records browser clock intervals. The history endpoint serves redacted daily cohorts and correlated call timelines.

## Invariants touched

I1 and I2 keep filing with the citizen and require verified OTP, cooldown and spoken confirmation. I3 asks only for missing details. I4 excludes raw transcripts and GPS coordinates from performance telemetry. I6 verifies the browser UI.

## Tempting but wrong

Inferring a ward from a nearby but unrelated GPS fix, treating a grievance draft as submitted, or presenting post-transcript latency as end-to-end.

## Acceptance tests

- Road flooding remains distinct from a pipe leak after a spoken or typed correction.
- An unsupported public landmark remains unresolved and receives the state referral. An explicitly requested GPS fix can resolve supported places and cannot silently override a verified place or a conflicting reported area.
- The local demo code can test distinct spoken confirmation. A demo review never authorizes official filing or starts a dispatch cooldown.
- Historical and correlated metrics retain separate measurement labels, and one turn joins browser and backend events by ID without exposing transcript content.
