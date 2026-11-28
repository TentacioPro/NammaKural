---
id: 011
title: Tamil Nadu public civic source register and change review
status: done
effort: medium
allowed_paths:
  - data/civic/
  - docs/architecture/CIVIC_DRAFTER_PRODUCT_FIT.md
  - ops/audit_civic_catalog.py
  - specs/
  - tests/test_civic_catalog_audit.py
  - LOG.md
  - research/civic/
---
# 011 Tamil Nadu public civic source register and change review

## Goal

Maintain official evidence for a grievance draft tied to the chosen channel. Discover statewide jurisdictions and service families, record observable field rules and channels, and make public-source changes reviewable.

## Non-goals

Submitting test complaints, signing in to government portals, entering OTPs, handling CAPTCHA, messaging bots or agencies, treating service application inventory as a grievance schema, and publishing changes to the live drafting path automatically.

## Data and coverage

[Tamil Nadu public catalog](../../data/civic/tn_public_catalog.json) records 38 district homepages, 24 registered source pages and 16 route or service-family records from a first-pass review. A district homepage is a discovery item. A district grievance help page establishes only the entry point it advertises. The separate [e-Sevai index](../../data/civic/tn_esevai_service_index.json) stores 122 unique service codes from two official published tables. It establishes neither current service availability nor the fields for those applications.

| Evidence state | Meaning |
|---|---|
| Visible controls | Public page shows field labels or validation hints. Conditional and server validation rules may still be unknown. |
| Gate only | The public login controls were visible. Post-login fields were left unknown. |
| Channel documented | The agency publicly confirms a contact channel or filing instructions. Draft suggestions are marked separately from required form fields. |
| Previous inspection unrevalidated | The repository contains earlier research. This pass could not reconfirm its exact field contract. |
| Inventory only or discovered | An official index, manual or landing page exists. Its workflow remains uninspected. |

`required: null` means unknown. A visible text counter, placeholder, or marked label documents what the page shows, with no assertion about backend acceptance. A verified draft contract additionally needs reviewed conditional rules, exact vocabularies and codes where supplied, accepted types and document limits, localization, and evidence of channel ownership. Federal and state directories provide distinct means of finding candidates. Use district portals, LGD identifiers, department service codes and published ward or street data to determine the coverage denominator. [Official district directory](https://lokbhavan.tn.gov.in/districts-of-tamil-nadu/) · [Local Government Directory](https://panchayat.gov.in/lgd/) · [e-Sevai inventory](https://www.tnesevai.tn.gov.in/citizen/EsevaiServiceList.html)

## Interfaces

From the repository root, validate the data and run a public check with the local Python environment.

```powershell
.\.venv\Scripts\python.exe ops/audit_civic_catalog.py --validate
.\.venv\Scripts\python.exe ops/audit_civic_catalog.py --output scratch/civic-audit/first.json
.\.venv\Scripts\python.exe ops/audit_civic_catalog.py --baseline scratch/civic-audit/first.json --output scratch/civic-audit/current.json
```

Use repeated `--source` arguments to check a subset. The audit reads robots policies first, makes only HTTPS GET requests to registered sources, and flags redirects for review. It records status, missing markers, visible control and option counts, and separate fingerprints of fields, contact signals, and visible text. Returned markup is parsed without executing scripts. It retains neither HTML nor contact values scraped from pages. JavaScript-rendered form rules, WhatsApp conversation steps, and delivery on phone or email need a separate review. A text-only change is a signal for review, not proof the channel contract changed.

The first snapshot supplies an initial comparison point. Subsequent runs produce a review queue without mutating the catalog. A reviewer reopens the official source, updates the affected field or channel with its evidence, and advances the reviewed baseline. Run it in a periodic task once a review owner and cadence are decided. This change creates no schedule.

## Invariants touched

I1 and I4. Use public evidence only. Keep citizen-only fields and credentials out of the agent’s collected dataset. Collect the minimum necessary factual detail after choosing the channel.

## Tempting but wrong

Declaring a district covered because its homepage resolved, copying a legacy form limit to the active portal, measuring a caller’s readiness against a hidden form, or equating static HTML with a tested field contract.

## Acceptance tests

- Catalog keeps GCC variants separate and distinguishes verified surface evidence from missing rules.
- Field or contact changes appear in the review queue without retaining unapproved values.
- Redirects, prohibited pages and failed sources produce a status without automatic navigation or publication.
