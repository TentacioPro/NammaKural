---
id: 003
title: Tanglish & Regional TN Accent Normalization
status: proposed
effort: medium
allowed_paths:
  - backend/nlu/**
  - index.html
---
# 003 Tanglish & Regional TN Accent Normalization

## Goal
Convert noisy spoken Tanglish, colloquial Chennai/Madurai/Kongu/Tirunelveli/Trichy Tamil, and Indian English into clean civic intents, resolved landmarks (`District -> Zone -> Ward -> Road ID`), and urgency/sentiment tags without forcing citizens to repeat themselves.

## Non-goals
- Do not build a custom acoustic model from scratch; combine ASR keyterm biasing + phonetic/fuzzy landmark normalization + contextual disambiguation.

## Interfaces
- `normalize_tanglish(utterance: str) -> NormalizedUtterance(intents, urgency_tier, landmarks, missing_slots, ticket_ref)`
- `resolve_ward(area_or_landmark: str) -> WardMatch | AmbiguousCandidates`

## Invariants touched
- `I3` (Ask clarification question ONLY when issue, location, or multi-ward landmark is ambiguous).

## Tempting but wrong
- Relying on exact English substring matches (`"street light"` fails on `"theruvilakku"`, `"light podala"`, `"kambam"`). Always include phonetic/Tanglish stems and Tamil Unicode synonyms.

## Acceptance tests
- Benchmark suite of >=25 synthetic Tanglish/Tamil complaints spanning Chennai, Madurai, and Coimbatore resolves Zone/Ward/Department with >=95% routing precision and triggers clarifier ONLY on intentional multi-ward inputs.
