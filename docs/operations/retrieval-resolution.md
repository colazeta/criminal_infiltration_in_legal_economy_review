# Paper retrieval resolution

Every curator candidate must pass through a mechanical retrieval-resolution stage. This stage is separate from eligibility screening and publication.

## Coverage contract

`data/curation/retrieval_coverage.csv` contains exactly one row for every row in `data/curation/review_queue.csv`, in the same order. A candidate may be unresolved, but it may not be unprocessed or silently absent from the retrieval ledger.

The coverage guarantee is therefore **100% process coverage**, not a claim that 100% of scholarly works have legally accessible full text online.

The first complete backfill on 2026-09-02 resolved a usable URL for all 68 then-open curator candidates: 47 direct full-text locations, 19 landing pages, one open-access landing page and one original source link; no candidate remained unresolved. These figures describe that run and are not a permanent performance guarantee.

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

### Curator-verified full-text locator bridge

Targeted reading retrieval can establish a full-text manifestation that the bulk resolver did not discover. To prevent that verified locator from remaining only in the reading-support layer, `scripts/retrieval/apply_verified_reading_locators.py` synchronises a deliberately narrow subset of `reading_aid_overrides.json` into the retrieval ledger after the normal resolver pass.

The bridge accepts only an existing candidate whose override is `full_text_intro`, whose final source is HTTPS and whose note explicitly records `Evidence basis: full_text`. It does not infer open-access rights from availability, does not create candidates, and does not decide eligibility or canonical identity. When retrieval coverage already has a full-text location, that existing primary location is preserved and the curator-verified locator is added as corroborating provenance rather than silently replacing it.

This bridge exists to keep the curator action, access classification and persisted retrieval projection consistent with an already verified reading source. Other reading-aid kinds, including summaries and metadata warnings, do not change retrieval status.

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
- whenever verified reading-aid locators change;
- whenever the resolver, verified-locator bridge or workflow changes;
- weekly, so older rows can be refreshed;
- manually on demand.

The workflow resolves the complete queue, applies the verified full-text locator bridge, validates one-row-per-candidate coverage and the bridge invariants, and runs the governed repository tests before attempting any write-back.

The preferred write-back is an auditable pull request. Some repository configurations disable pull-request creation by `GITHUB_TOKEN`; when that policy applies, the workflow may fast-forward the already validated mechanical commit directly to `main` **only if `main` has not moved since resolution began**. It never force-pushes. If both PR creation and the guarded fast-forward are blocked, the validated branch is retained and the workflow reports the persistence limitation without discarding the resolved data.

The daily intake workflow also runs the resolver before its staging PR is opened. Therefore new candidates enter the curator with a retrieval attempt already recorded.

## Curator issue synchronisation

`materialize-curation.yml` runs `scripts/retrieval/sync_issue_retrieval.py` after candidate issue materialisation. Each issue receives a `Retrieval coverage — mechanical` section with the best URL, full-text/OA/landing alternatives, resolver source, match confidence and check date.

This section is explicitly non-editorial. It cannot establish eligibility, exclusion, duplicate status, canonical identity or publication approval.

## Curator URL precedence

The secure curator exposes the persisted retrieval record through an authenticated `/api/retrieval` endpoint. The article action follows the same preference order as the resolver:

- when a persisted direct full-text URL exists, the primary action becomes **Apri full text**;
- otherwise an open-access location becomes **Apri copia OA**;
- otherwise the persisted best landing/DOI/source URL becomes **Apri articolo**.

Live OpenAlex/Crossref enrichment remains useful for abstracts and fresh bibliographic checks, but it must not silently overwrite a better URL already established by the persistent retrieval ledger.

The public GitHub Pages surface still has no curator API origin or credentials; only the isolated authenticated Worker can request the persisted retrieval projection.

## Optional service credentials

The resolver works without additional secrets by using discovery links, Crossref and the available OpenAlex allowance. For sustained production use:

- `OPENALEX_API_KEY` may be configured to increase OpenAlex API allowance;
- `UNPAYWALL_EMAIL` may be configured to activate Unpaywall resolution.

The first 68-record backfill reached zero unresolved candidates without either optional credential configured. The pipeline remains valid when either optional secret is absent; the ledger records the resulting provider limitation instead of silently skipping the candidate.
