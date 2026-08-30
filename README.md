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
not read by the site builder. Automated discovery can create an intake issue; it
cannot publish a work.

## Repository map

| Path | Purpose |
|---|---|
| `INDEX.md` | Plain-language routes for readers, reviewers and maintainers |
| `data/registry/` | Canonical works, identifiers, decisions and publication state |
| `data/legacy/` | Retired pilot evidence retained only for audit |
| `docs/methodology/` | Protocol, eligibility, discovery, saturation and reporting |
| `docs/governance/` | Data contract and authorised sources/connectors |
| `docs/operations/` | Automation and release runbooks |
| `scripts/` | Deterministic build, saturation report and validators |
| `tests/` | Negative publication-gate and cycle-grouping tests |
| `site/` | Static public interface and deterministic data exports |

## Expanding the literature

The [plain-language operational guide in Italian](docs/methodology/expansion.md)
describes a six-step loop: test the search, search several sources, join repeated
results, follow references and citations, review each work, and use the gaps to
plan the next round. The
[technical reference in English](docs/methodology/expansion-reference.md) keeps
the provider rules, metrics and audit fields needed for reproducibility.

Automation may create one deduplicated intake issue and one aggregate metrics
comment per daily batch. It cannot assign canonical IDs, decide eligibility,
edit registries, declare saturation or publish papers. The
[daily-metrics guide](docs/operations/daily-metrics.md) explains how successful
zero-result days, partial runs and failures are kept distinct.

## Correcting the archive

Repository owners can use the [curator desk](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/curate.html)
to change a paper's main topic, exclude a reviewed work or join a confirmed
duplicate. The authenticated GitHub workflow validates the instruction and
prepares a visible change while retaining previous decisions and publication
versions. No repository token is placed in the public website.

## Publishing the website

GitHub Pages is already configured to use the pinned workflow in
`.github/workflows/archive.yml`. A reviewed merge to `main` runs quality checks,
builds `site/` and deploys the public archive. See the
[GitHub Pages guide](docs/operations/github-pages.md) for the exact first-release
steps and troubleshooting.

## Build locally

Requires Python 3.11+ and Node only for the JavaScript syntax check.

```bash
python3 scripts/validation/validate_repository.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/build_archive.py
python3 scripts/validation/validate_archive.py
python3 scripts/validation/validate_site.py
node --check site/app.js
node --check site/stats.js
python3 -m http.server 8000 --directory site
```

Open `http://localhost:8000`. No network request is required to build or browse
the archive.

## Scientific boundary

Criminal infiltration requires an analytically identifiable criminal interest,
a legal-economy target, sustained access/participation/influence/control or
embeddedness, and substantive analysis of that relationship. Money laundering,
corruption, facilitation, passive investment and corporate offending are not
treated as infiltration without that relational evidence.

The complete rule is in [the eligibility codebook](docs/methodology/eligibility.md).
The repository does not redistribute full text; it publishes curated metadata,
classifications, provenance and lawful external links.

## Version and citation

The current archive release metadata are in
`data/registry/archive_versions.csv`, `CITATION.cff` and `CHANGELOG.md`.
Release `0.2.0` is a prerelease foundation. A persistent DOI and an open reuse
licence remain explicit release decisions; no rights are silently granted.
