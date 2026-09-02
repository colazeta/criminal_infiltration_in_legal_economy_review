# Paper retrieval resolution

Every curator candidate must pass through a mechanical retrieval-resolution stage. This stage is separate from eligibility screening and publication.

## Coverage contract

`data/curation/retrieval_coverage.csv` contains exactly one row for every row in `data/curation/review_queue.csv`, in the same order. A candidate may be unresolved, but it may not be unprocessed or silently absent from the retrieval ledger.

The coverage guarantee is therefore **100% process coverage**, not a claim that 100% of scholarly works have legally accessible full text online.

## Resolution order

The resolver attempts, in priority order:

1. direct full-text links already found during discovery;
2. OpenAlex work and location records, including OA/PDF locations when exposed;
3. Crossref DOI/title resolution, publisher landing URLs and deposited full-text links;
4. Unpaywall `best_oa_location`, including PDF and landing URLs, when `UNPAYWALL_EMAIL` is configured;
5. the DOI resolver URL;
6. the original discovery/source link;
7. an explicit `unresolved` status.

For records without a DOI, title/year matching is deliberately strict. A weak bibliographic match is rejected rather than used as a paper URL.

## Persisted fields

The retrieval ledger records:

- resolution status;
- best URL and URL kind;
- direct full-text URL when found;
- open-access URL when found;
- landing-page URL;
- DOI URL and resolved DOI;
- original source URLs;
- resolver sources;
- match method and confidence;
- last checked date;
- non-fatal upstream notes.

No abstract or full text is persisted by this layer.

## Automation

`.github/workflows/retrieval-resolution.yml` runs:

- whenever the curator queue changes;
- whenever the resolver or its workflow changes;
- weekly, so older rows can be refreshed;
- manually on demand.

The workflow resolves the complete queue, validates one-row-per-candidate coverage, runs repository tests, and writes retrieval changes through an auditable pull request. The PR is automatically merged because retrieval metadata is mechanical and does not constitute an editorial decision.

The daily intake workflow also runs the resolver before its staging PR is opened. Therefore new candidates enter the curator with a retrieval attempt already recorded.

## Curator issue synchronisation

`materialize-curation.yml` runs `scripts/retrieval/sync_issue_retrieval.py` after candidate issue materialisation. Each issue receives a `Retrieval coverage — mechanical` section with the best URL, full-text/OA/landing alternatives, resolver source, match confidence and check date.

This section is explicitly non-editorial. It cannot establish eligibility, exclusion, duplicate status, canonical identity or publication approval.

## Optional service credentials

The resolver works without additional secrets by using discovery links, Crossref and the available OpenAlex allowance. For sustained production use:

- `OPENALEX_API_KEY` may be configured to increase OpenAlex API allowance;
- `UNPAYWALL_EMAIL` may be configured to activate Unpaywall resolution.

The pipeline remains valid when either optional secret is absent; the ledger records the resulting provider limitation instead of silently skipping the candidate.
