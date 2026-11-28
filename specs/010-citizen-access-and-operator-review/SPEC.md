---
id: 010
title: Citizen OTP access, channel checklists and operator review
status: done
effort: high
allowed_paths:
  - backend/
  - frontend/src/
  - tests/
  - analytics/golden_cases.jsonl
  - specs/
  - .env.example
  - Dockerfile
  - docker-compose.yml
  - LOG.md
---
# 010 Citizen OTP access, channel checklists and operator review

## Goal

Give signed-in citizens a focused intake flow and private request history. Show operators the latest case outcomes, per-turn failures, and repeatable eval results.

## Non-goals

UIDAI authentication, Aadhaar capture, government portal automation, background email or WhatsApp dispatch, verifying outside complaint references, and a hosted Phoenix or LangSmith replacement.

## Interfaces

- Set `NK_SUPABASE_URL` and `NK_SUPABASE_PUBLIC_KEY` for a project with phone OTP and an SMS provider. Set `NK_AUTH_REQUIRED=1` to fail closed before configuration. Vercel requires sign-in by default. The local zero-key demo is available without a provider and with `NK_AUTH_REQUIRED=0`. [Supabase phone sign-in](https://supabase.com/docs/guides/auth/phone-login)
- The sign-in cookie is server-issued and HttpOnly. `NK_OPERATOR_IDS` lists approved account UUIDs. A server-transcribed Confirm is needed for authenticated filing handoff.
- `/api/requests` stores citizen-saved drafts by account in local SQLite. An external reference is citizen-reported. Use a backend with persistent storage and mount `logs/` across Docker recreations. The SQLite store is unsuitable for ephemeral serverless instances.
- `/api/civic/channels` lists citizen-accessible channels and information, including fields that citizens enter directly in government portals.
- `/api/ops/evaluate` runs deterministic text cases. Correlated trace events expose allowlisted workflow metadata, not citizen text or coordinates.

## Invariants touched

I1 citizen-led channel handoff, I2 verified mobile and spoken confirmation, I3 one question for a missing fact, I4 private account data, I6 build and browser gates.

## Tempting but wrong

Treating mobile verification as Aadhaar identity proof, counting references as agency-verified submissions, or treating offline evaluation latency as live call latency.

## Acceptance tests

- Anonymous access is blocked in required mode. A citizen cannot retrieve or modify another citizen's draft or request record.
- Under authenticated intake, road flooding asks whether the road can be used. Chennai Metro Water asks for missing duration.
- Protected views show aggregate call outcomes and redacted turn stages, and run the golden cases without calling a paid model.

## References

- UIDAI describes registered-mobile OTP as part of the authorized Aadhaar authentication ecosystem. The pilot verifies possession of a mobile number using a separate provider. [UIDAI rules](https://uidai.gov.in/images/The_Aadhaar_Authentication_and_Offline_Verifications_Regulations_2021-_Clean_copy-30122025.pdf)
- Public grievance routes come from agency pages and the project’s inspected schemas. The channel directory distinguishes public browsing and helplines from citizen verification in the chosen portal. [GCC](https://gccservices.in/pgr/) · [Chennai Metro Water](https://cms-cmwssb.tn.gov.in/) · [TWAD PUNAL](https://www.punal.tn.gov.in/index.html) · [TNPDCL](https://ccms.tangedco.org/tangedco-public/) · [CM Helpline](https://cmhelpline.tnega.org/portal/en/kb/articles/about-us) · [TNPDS](https://www.nfsa.gov.in/State/TN) · [Inspected schemas](../../docs/TN_CIVIC_PORTALS.md)
