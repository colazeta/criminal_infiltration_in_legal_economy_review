# Release and preservation runbook

## Trigger

Create a release when the public corpus, a public annotation, protocol, schema or
controlled taxonomy changes. A no-change surveillance run does not require a
release.

## Checklist

1. Update `archive_versions.csv`; retain exactly one current row.
2. Update `CHANGELOG.md`, `CITATION.cff` and `.zenodo.json` consistently.
3. Record corpus/protocol/schema version, release date, search coverage through,
   records added/changed/removed and previous version.
4. Run the complete commands in `AGENTS.md` from a clean checkout.
5. Confirm generated JSON/CSV match a fresh deterministic build.
6. Review the public archive, methodology limitations and download files.
7. Merge through review; GitHub Pages deploys only from `main`.
8. When configured, archive the release in Zenodo and record the DOI in the
   version registry/CFF.

## Corrections and retractions

Never erase history. Add superseding identifier/decision/publication rows,
explain removals or corrections in the changelog, and preserve stable public IDs
where possible. A retracted or withdrawn work is withheld from the current site
and documented in the release change log.

## Rights and persistence

The repository currently states all rights reserved because choosing an open
code/data licence is an owner decision with lasting legal effect. Before a 1.0
or Zenodo release, select and document separate licences for repository code and
curated data/annotations, while respecting third-party metadata and full-text
rights. No full text is included in a release.
