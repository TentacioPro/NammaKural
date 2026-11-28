# NammaKural cloud handoff for 28 November 2026

## Start here

1. [Decision record](DECISIONS.md) captures the product question, verified work, and open decisions.
2. [Public source register](../../../data/civic/tn_public_catalog.json) contains evidence states, official URLs, observed controls, 38 district entries, and explicit unknowns. [e-Sevai inventory](../../../data/civic/tn_esevai_service_index.json) records 122 published service codes with labels by source.
3. [Product-fit research](../../../docs/architecture/CIVIC_DRAFTER_PRODUCT_FIT.md) covers general-purpose assistants, the official helpline alternative, and the comparative evaluation.
4. [Subagent handoff](SUBAGENT_HANDOFF.md) records the research task and deliverable. [Original brief](sources/user_brief.txt) preserves the user-supplied hypotheses.
5. [Telemetry guide](telemetry/README.md) explains the shareable event export and how to interpret its timings. [Synthetic review cases](telemetry/synthetic-review-cases.jsonl) preserve the scenarios used to discuss the current limits.

## Source evidence

The source register stores exact public URLs, observed form-control IDs and constraints where available, and candidate contact channels with provenance. [First public audit](sources/first-audit.json) and [second public audit](sources/second-audit.json) preserve the machine observations and the comparison queue produced by the CLI. The register stores fingerprints from public markup in place of republishing full third-party pages. Authenticated rules, dynamic options and message-delivery behavior remain open.

## Continue locally or on a cloud workspace

The branch uses `.env.example` for configuration names. The real `.env`, account and session storage, citizen conversations and unrestricted logs stay local. The CPU-only workflow and golden cases can run without keys. Configure Sarvam and the optional mobile OTP provider only where needed. Do not treat the new civic catalog as a production routing table until its evidence and field validation are wired into draft generation.

- Use `python -m pytest -q` and `python analytics/eval_gate.py --golden analytics/golden_cases.jsonl` for behavior.
- Use `python ops/audit_civic_catalog.py --validate` to validate source references and field keys.
- Use `python ops/audit_civic_catalog.py --baseline research/civic/2026-11-28/sources/second-audit.json --output scratch/civic-audit/current.json` for a fresh public comparison.
