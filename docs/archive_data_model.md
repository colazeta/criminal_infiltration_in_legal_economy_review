# Public Archive Data Contract

## Source of truth

The public build reads canonical registries in `data/registry/`. It never reads
draft candidate files to create publication cards and never performs live API
retrieval.

## Publication gate

A work is publishable only when all conditions hold:

1. `papers.csv` contains a unique `paper_id` with canonical status
   `seed_included` or `review_included`;
2. required bibliographic fields are present;
3. at least one `discovery_events.csv` row refers to the work;
4. exactly one `screening_decisions.csv` row is marked `is_current=true`;
5. the current decision is `eligible_core` or `eligible_contextual`;
6. the public record contains a specific relevance reason;
7. no duplicate DOI or normalised title/year collision exists.

## State dimensions

Keep these dimensions separate:

| Dimension | Examples | Meaning |
|---|---|---|
| Discovery role | seed, database, backward, forward | How the work was found |
| Screening decision | eligible, pending, excluded, duplicate | Whether it enters the corpus |
| Analytic tier | core, contextual | Its relationship to the construct |
| Coding dimensions | mechanism, sector, method, geography | What the work contributes |

## Public fields

The generated JSON/CSV may expose:

- stable public record ID;
- title, authors, year, venue and document type;
- verified DOI and lawful external link;
- core/contextual decision;
- public relevance reason;
- controlled topic labels and future evidence codes;
- non-personal provenance and source snapshot.

It must not expose reviewer identity, internal comments, evidence quotations,
raw queries, excluded-record metadata, secrets or copyrighted full text.

## Work and identifier identity

The current CSV model uses one primary DOI field. Before large-scale E1 import,
add a work-identifier table that supports one canonical work to many identifiers
or manifestations. DOI uniqueness is necessary but not sufficient for work-level
deduplication.

## Deterministic build

`scripts/build_archive.py` produces `site/data/archive.json` and
`site/data/archive.csv`. The output:

- is ordered deterministically;
- contains no build-time timestamp;
- makes no network request;
- preserves unknown fields as blank/null;
- includes no non-canonical bibliographic records.

Continuous integration rebuilds and validates the export before deployment.
