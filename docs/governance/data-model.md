# Archive data model and publication contract

## Layers

| Layer | Purpose | Read by public builder |
|---|---|---|
| `data/registry/` | Governed source of truth | Yes, fixed allowlist only |
| `data/legacy/` | Retired pilot evidence | Never |
| GitHub intake issues | Candidate staging and search logs | Never |
| `site/data/` | Deterministic derived export | Output only |

## Registries

- `papers.csv`: canonical work-level bibliography and state.
- `work_identifiers.csv`: verified primary and alternate identifiers or manifestations.
- `discovery_events.csv`: every occurrence and its retrieval provenance.
- `screening_decisions.csv`: versioned decisions; one current row per included work.
- `publications.csv`: explicit public-release status and approved annotations.
- `taxonomy.csv` / `paper_codes.csv`: controlled labels and evidence-backed codes.
- `editorial_summary.csv`: public-safe aggregate queue counts only.
- `execution_metrics.csv`: E1–E3 component metrics grouped by cycle.
- `archive_versions.csv`: corpus/protocol/schema version and coverage dates.

## Full publication gate

For a `published` manifest row, the builder requires:

1. canonical status `seed_included` or `review_included`;
2. complete minimum bibliography;
3. a verified primary DOI consistent across work and identifier registries;
4. at least one discovery event;
5. exactly one current decision;
6. current decision `eligible_core` or `eligible_contextual`;
7. approved, nonblank public relevance annotation;
8. a topic in the controlled taxonomy.

Any inconsistent `published` row fails the build. `withheld` rows remain absent.
A non-public work is never promoted by inference.

## Public allowlist

Only citation fields, verified DOI link, decision/tier, screening stage, approved
topic, relevance note, sanitised source basis and release metadata may appear.
The builder uses a closed field allowlist. Reviewer identity, internal notes,
queries, evidence quotes, candidate records and full text are forbidden.
The machine-readable contract is `schema/public-archive.schema.json`.

## Identity

`papers.doi` is the denormalised primary DOI for simple export. Its value must
equal the one verified primary DOI in `work_identifiers.csv`. Alternative DOI
manifestations remain separate rows linked to the same work.

## Determinism

The build uses no network, timestamp or raw/editorial input. Unknown fields stay
blank/null. Records sort by year descending, normalised title and stable ID.
