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
| `paper_codes.csv` | One evidence-backed code applied to a work |
| `editorial_summary.csv` | One aggregate public-safe queue snapshot |
| `execution_metrics.csv` | One E0 or E1/E2/E3 execution metric row |
| `archive_versions.csv` | One versioned corpus release state |

Primary/foreign keys and enumerations are enforced by
`scripts/validation/validate_archive.py`. See
`docs/governance/data-model.md` for the publication gate.

`publications.csv` preserves every released, corrected or withheld state. Each
row has a unique `publication_id` and a per-work `publication_version`; later
rows point to their immediate predecessor through
`supersedes_publication_id`. Exactly one row per represented work is current,
and only that row controls the current public export.
