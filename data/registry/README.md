# Registry index

These CSV files are the governed source of truth. Every change is reviewed and
validated; no search automation writes here directly.

| File | One row represents |
|---|---|
| `papers.csv` | A canonical scholarly work |
| `work_identifiers.csv` | One verified identifier or manifestation for a work |
| `discovery_events.csv` | One occurrence in a search/seed/citation execution |
| `screening_decisions.csv` | One historical or current screening decision |
| `publications.csv` | One versioned public-release state and annotation |
| `taxonomy.csv` | One controlled code definition |
| `paper_codes.csv` | One versioned evidence-backed code applied to a work |
| `exclusion_reasons.csv` | One controlled screening-exclusion reason |
| `work_relations.csv` | One curator-confirmed link between related work records |
| `editorial_summary.csv` | One aggregate public-safe queue snapshot |
| `execution_metrics.csv` | One E0 or E1/E2/E3 execution metric row |
| `archive_versions.csv` | One versioned corpus release state |

Daily Work surveillance is not written here and is not an E1–E3 execution. Its
aggregate run telemetry is stored in
[GitHub issue #30](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/30)
and documented in
[`docs/operations/daily-metrics.md`](../../docs/operations/daily-metrics.md).

Primary/foreign keys and enumerations are enforced by
`scripts/validation/validate_archive.py`. See
`docs/governance/data-model.md` for the publication gate.

`publications.csv` preserves every released, corrected or withheld state. Each
row has a unique `publication_id` and a per-work `publication_version`; later
rows point to their immediate predecessor through
`supersedes_publication_id`. Exactly one row per represented work is current,
and only that row controls the current public export.

Routine curator changes should be prepared through the
[curator desk](../../docs/operations/curation.md), rather than by editing several
CSV files independently. The workflow preserves the earlier decision and
publication rows before it prepares a visible change.
