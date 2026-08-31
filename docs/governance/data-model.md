# Archive data model and publication contract

## Layers

| Layer | Purpose | Read by public builder |
|---|---|---|
| `data/registry/` | Governed source of truth | Yes, fixed allowlist only |
| `data/curation/` | Materialised candidate queue and append-only curator actions | Never |
| `data/legacy/` | Retired pilot evidence | Never |
| GitHub intake issues | Candidate staging and search logs | Never |
| GitHub metrics ledger | Aggregate daily surveillance telemetry | Safe aggregates only, after validation |
| `site/data/` | Deterministic derived export | Output only |

## Registries

- `papers.csv`: canonical work-level bibliography and state.
- `work_identifiers.csv`: verified primary and alternate identifiers or manifestations.
- `discovery_events.csv`: every occurrence and its retrieval provenance.
- `screening_decisions.csv`: versioned decisions; one current row per included work.
- `publications.csv`: version-preserving publication history, explicit current
  release status and approved annotations.
- `taxonomy.csv` / `paper_codes.csv`: controlled labels and append-only,
  versioned evidence-backed coding decisions.
- `exclusion_reasons.csv`: controlled reason codes used by non-eligible,
  duplicate, non-academic and non-retrievable decisions.
- `work_relations.csv`: explicit curator-confirmed identity relations, including
  the surviving record when a duplicate is merged.
- `editorial_summary.csv`: public-safe aggregate queue counts only.
- `execution_metrics.csv`: E1–E3 component metrics grouped by cycle.
- `archive_versions.csv`: corpus/protocol/schema version and coverage dates.

Daily surveillance does not add a registry row. One aggregate comment per batch
is stored in [GitHub issue #30](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/30).
The deployment validates those comments and derives
`site/data/research-stats.json`. This keeps operational telemetry separate from
the E1–E3 saturation registry and from scientific decisions.

## Candidate curation layer

`data/curation/review_queue.csv` materialises candidates as individually
addressable records without promoting them into the canonical archive. Its
legacy fields preserve what the pilot stated. Daily rows preserve the validated
intake assessment, metadata status, source/query references, duplicate or
conflict notes and required human action. `current_status`,
`current_decision`, controlled reason/topic fields and `last_action_id` describe
the current human-reviewed projection.

`data/curation/actions.csv` is append-only. Each row records the authenticated
GitHub issue, actor, screening stage, decision, reason/topic/duplicate target,
confidence, rationale, evidence locator, date and transition in queue status.
An action may supersede the queue's current projection, but earlier action rows
are never rewritten.

The curation layer is never read by `scripts/build_archive.py` or copied to
`site/data/`. Its candidate metadata and review evidence therefore cannot enter
the public archive export. GitHub candidate issues remain the authenticated
source for the working surface. After GitHub App authentication, the isolated
Worker copy of `curate.html` loads their bounded fields at runtime; it does not
write them into the static artifact or persistent browser storage. The
`colazeta.github.io` source contains only aggregate counts, controlled form
options and a link to the dedicated console, and never receives the session.
An authorised intake issue reaches this layer only through a validated,
reviewable pull request; it is never converted directly into a canonical work.

## Full publication gate

For a current `published` manifest row, the builder requires:

1. canonical status `seed_included` or `review_included`;
2. complete minimum bibliography;
3. a verified primary DOI consistent across work and identifier registries;
4. at least one discovery event;
5. exactly one current decision;
6. current decision `eligible_core` or `eligible_contextual`;
7. approved, nonblank public relevance annotation;
8. a topic in the controlled taxonomy.

Any inconsistent current `published` row fails the build. A current `withheld`
row remains absent even when an earlier historical version was published. A
non-public work is never promoted by inference.

`review_pending` is a canonical, non-publishable state for a bibliographically
resolved work that still lacks sufficient screening evidence.

`review_excluded` is a retained, non-publishable work with a current
evidence-backed exclusion decision. `superseded` retains a former record after
its identifiers and discovery occurrences have been reconciled with the
surviving canonical work. Neither state is deleted from the audit history.

## Publication history

One `publications.csv` row represents one preserved version of the publication
state and its approved annotation. Once a row is superseded, its annotation and
status fields are immutable. The version key is `publication_id`; within a work,
`publication_version` starts at 1 and increases contiguously.

- Every work represented in the manifest has exactly one `is_current=true` row.
- The current row is always the highest version.
- Version 1 leaves `supersedes_publication_id` blank.
- Every later version points to the immediately preceding `publication_id`.
- `version_note` records why the version was created.
- A correction, reclassification or withdrawal appends a row and changes only
  the former row's current marker from `true` to `false`; it never replaces or
  deletes the former annotation.
- `first_published_version` records the archive release in which the work first
  appeared and remains unchanged in all later versions after first publication.

The builder validates the complete chain but derives the current site solely
from the one current row. Historical `published` rows therefore preserve what
was previously released without keeping a superseded work or annotation online.

## Public allowlist

Only citation fields, verified DOI link, decision/tier, screening stage, approved
topic, relevance note, sanitised source basis and release metadata may appear.
The builder uses a closed field allowlist. Reviewer identity, internal notes,
queries, evidence quotes, candidate records and full text are forbidden.
The machine-readable contract is `schema/public-archive.schema.json`.

The statistics export has a separate closed allowlist containing dates, counts,
technical run status, source-level aggregates and whether an intake issue was
created. Candidate
titles, identifiers, queries and reviewer material are forbidden. Its contracts
are `schema/surveillance-run.schema.json` and
`schema/research-stats.schema.json`.

The curator workspace uses another closed aggregate projection containing only
queue totals, open work by lane and legacy/daily origin counts. Its contract is
`schema/curator-stats.schema.json`; bibliographic fields, decisions, evidence,
issue numbers and curator identities are absent.

## Identity

`papers.doi` is the denormalised primary DOI for simple export. Its value must
equal the one verified primary DOI in `work_identifiers.csv`. Alternative DOI
manifestations remain separate rows linked to the same work.

When the curator confirms that two canonical records represent the same work,
the duplicate record becomes `superseded`, a `duplicate_of` relation identifies
the survivor, and identifiers plus discovery occurrences move to the surviving
record. Earlier screening and publication rows remain attached to the retired
record so that its previous state can still be reconstructed. Evidence-backed
coding rows also remain attached to the retired record; they are not rewritten
as if they had originally been assigned to the survivor.

## Curator actions

The [curator workspace](../operations/curation.md) has a candidate lane and a
canonical lane. Candidate decisions update only `data/curation/` and prepare a
pull request; they cannot assign a canonical ID or publish a work. The canonical
lane supports changing the primary topic, excluding a work and merging a
confirmed duplicate. Every instruction is explicit, attributed to the GitHub
actor and validated in a temporary branch. It never deletes decision or
publication history.

A topic change appends a new `paper_codes.csv` version, retires the prior current
row and links the two through `supersedes_coding_id`. Earlier evidence, coder,
date and notes remain unchanged. Exclusion operations accept only codes from
`exclusion_reasons.csv`.

## Determinism

The archive build uses no network, timestamp or raw/editorial input. Unknown
fields stay blank/null. Records sort by year descending, normalised title and
stable ID. Daily statistics are a separate deployment input: GitHub Actions
fetches the public ledger, accepts only authorised and schema-valid aggregate
comments, and fails without replacing the last valid deployment when the ledger
cannot be verified.
