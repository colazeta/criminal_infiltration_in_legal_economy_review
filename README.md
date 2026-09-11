# Criminal Infiltration Literature Archive

A searchable, governed archive of scholarly work on **criminal infiltration in
the legal economy**.

- [Public archive](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/)
- [Daily research statistics](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/stats.html)
- [Curator desk](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/curate.html)
- [Start here: repository index](INDEX.md)
- [Guida rapida in italiano](docs/GUIDA_RAPIDA_IT.md)
- [Documentation index](docs/README.md)
- [How to contribute](CONTRIBUTING.md)

The repository's sole active subject scope is **criminal infiltration in the legal
economy**. It does not maintain a separate AML or economic/financial-crime
collection. Money laundering, corruption, facilitation and other adjacent
phenomena are relevant only when they satisfy the governed infiltration boundary.

The repository's primary product is the public publication index. The review
protocol, screening history and controlled update process make that index
traceable. It is a **living curated evidence map**, not a claim that the
literature is already complete or saturated.

## What becomes public

A work appears on the site only when all publication gates pass:

1. it is an included canonical work in `data/registry/papers.csv`;
2. it has a verified primary identifier and at least one discovery event;
3. it has exactly one current `eligible_core` or `eligible_contextual` decision;
4. `data/registry/publications.csv` explicitly marks it `published` and contains
   an approved relevance note;
5. its topic belongs to the controlled taxonomy;
6. the validators find no identity, schema or public-field conflict.

Candidate intake, reviewer notes, rejected works and legacy retrieval files are
not read by the public archive builder. Automated discovery can create an intake
issue; it cannot publish a work. A work that is `not_eligible` under the
criminal-infiltration test remains outside the active project rather than being
routed to a separate AML collection.

## Repository map

| Path | Purpose |
|---|---|
| `INDEX.md` | Plain-language routes for readers, reviewers and maintainers |
| `data/registry/` | Canonical works, identifiers, decisions and publication state |
| `data/curation/` | Materialised review queue and append-only candidate decisions |
| `data/legacy/` | Retired evidence retained only for audit |
| `docs/methodology/` | Protocol, eligibility, discovery, saturation and reporting |
| `docs/governance/` | Data contract and authorised sources/connectors |
| `docs/operations/` | Automation and release runbooks |
| `scripts/` | Deterministic build, saturation report and validators |
| `tests/` | Negative publication-gate and cycle-grouping tests |
| `site/` | Static public interface and deterministic data exports |

Historical secondary-collection fields and files can remain where required for
backward compatibility, reproducibility or audit. They are not an active
editorial destination and are not exposed as a separate subject section.

## Expanding the literature

The [plain-language operational guide in Italian](docs/methodology/expansion.md)
describes the search loop. The
[technical reference in English](docs/methodology/expansion-reference.md) keeps
the provider rules, metrics and audit fields needed for reproducibility.
Discovery should broaden terminology and geography while preserving the same
criminal-infiltration eligibility boundary.

Automation may create one deduplicated intake issue and one aggregate metrics
comment per daily batch. It cannot assign canonical IDs, decide eligibility,
edit registries, declare saturation or publish papers. The
[daily-metrics guide](docs/operations/daily-metrics.md) explains the public
statistics contract.

A validated positive intake batch prepares a separate pull request that adds its
candidates to `data/curation/review_queue.csv`. After human merge, each new row
receives an individual review record. Intake assessment, screening, canonical
promotion and publication remain distinct gates.

## Correcting the archive

Repository owners can use the [curator workspace](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/curate.html)
to open an isolated console and authenticate with the repository GitHub App once
its backend is configured. Candidate actions update only the editorial queue;
canonical promotion and publication remain separate reviewed changes. The
curator no longer offers an AML secondary-collection route.

## Publishing the website

GitHub Pages is configured to use the pinned workflow in
`.github/workflows/archive.yml`. A reviewed merge to `main` runs quality checks,
builds `site/` and deploys the public archive. See the
[GitHub Pages guide](docs/operations/github-pages.md) for troubleshooting.

## Build locally

Requires Python 3.11+ and Node for JavaScript syntax checks.

```bash
python3 scripts/validation/validate_repository.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/build_archive.py
python3 scripts/build_secondary_collections.py
python3 scripts/curation/build_curator_stats.py
python3 scripts/curation/build_curator_options.py
python3 scripts/validation/validate_archive.py
python3 scripts/validation/validate_site.py
node --check site/app.js
node --check site/aml.js
node --check site/stats.js
node --check site/curator.js
node --check site/curator-config.js
node --check curator-app/src/index.js
node --check curator-app/src/worker.js
node --test curator-app/test/*.test.js
python3 -m http.server 8000 --directory site
```

The retained `aml.js`/secondary-collection build paths are compatibility and
validation surfaces only; the active site has no AML collection. The historical
`/aml.html` URL redirects to the main archive.

## Scientific boundary

Criminal infiltration requires an analytically identifiable criminal interest,
a legal-economy target, sustained access/participation/influence/control or
embeddedness, and substantive analysis of that relationship. Money laundering,
corruption, facilitation, passive investment and corporate offending are not
treated as infiltration without that relational evidence.

Adjacent scholarly work that does not meet this rule is outside the active
review. The complete rule is in [the eligibility codebook](docs/methodology/eligibility.md).
The repository does not redistribute full text; it publishes curated metadata,
classifications, provenance and lawful external links.

## Version and citation

The current archive release metadata are in
`data/registry/archive_versions.csv`, `CITATION.cff` and `CHANGELOG.md`.
Historical releases and legacy snapshots remain available for audit and are not
rewritten when the active editorial scope changes.

## Active archive reset — 2026-09-08

Release 0.3.0 starts the active archive from zero under OA-1. Previous data and
decisions are retained in `data/legacy/pre-oa-reset-2026-09-08/` and the preserved
Git branch. Old issue/ledger data do not populate the active cycle. See
`docs/operations/archive-reset.md` for the exact scope and rollback procedure.
