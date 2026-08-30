# Criminal Infiltration Literature Archive

A searchable, governed archive of scholarly work on **criminal infiltration in
the legal economy**.

- [Public archive](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/)
- [Live preview](https://criminal-infiltration-archive.colazeta.chatgpt.site)
- [Methodology index](docs/README.md)
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
| `data/registry/` | Canonical works, identifiers, decisions and publication state |
| `data/legacy/` | Retired pilot evidence retained only for audit |
| `docs/methodology/` | Protocol, eligibility, discovery, saturation and reporting |
| `docs/governance/` | Data contract and authorised sources/connectors |
| `docs/operations/` | Automation and release runbooks |
| `scripts/` | Deterministic build, saturation report and validators |
| `tests/` | Negative publication-gate and cycle-grouping tests |
| `site/` | Static public interface and deterministic data exports |

## Build locally

Requires Python 3.11+ and Node only for the JavaScript syntax check.

```bash
python3 scripts/validation/validate_repository.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/build_archive.py
python3 scripts/validation/validate_archive.py
python3 scripts/validation/validate_site.py
node --check site/app.js
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
