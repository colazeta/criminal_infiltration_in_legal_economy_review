# Release and preservation runbook

## Trigger

Create a release when the public corpus, a public annotation, protocol, schema or
controlled taxonomy changes. A no-change surveillance run does not require a
release. Refreshing aggregate daily statistics also does not change the archive
version: the deployed statistics retain their own data-through date and ledger
provenance.

## Checklist

1. For every publication-state or public-annotation change, append a versioned
   `publications.csv` row, retire the former current marker and verify the
   supersession chain. Apply the same rule to a secondary collection through
   `secondary_publications.csv`. Never edit a former annotation in place.
2. Update `archive_versions.csv`; retain exactly one current row.
3. Update `CHANGELOG.md`, `CITATION.cff` and `.zenodo.json` consistently.
4. Record corpus/protocol/schema version, release date, search coverage through,
   records added/changed/removed and previous version.
5. Run the complete commands in `AGENTS.md` from a clean checkout.
6. Confirm generated JSON/CSV match a fresh deterministic build and contain only
   current `published` publication rows. Confirm the secondary export contains
   only current `not_eligible` works that remain withheld from the core.
7. Review the public archive, methodology limitations and download files.
8. Follow the [GitHub Pages guide](github-pages.md), merge through review and
   verify the `main` deployment.
9. When configured, archive the release in Zenodo and record the DOI in the
   version registry/CFF.

## Publication-version procedure

When publication status or an approved public field changes:

1. retain the existing row and change only `is_current` from `true` to `false`;
2. append a row with a new unique `publication_id` and the next contiguous
   `publication_version` for that `paper_id`;
3. set `supersedes_publication_id` to the former current row;
4. set the new row `is_current=true` and explain the change in `version_note`;
5. retain the original `first_published_version` after a work has first appeared;
6. rebuild and verify that a current `withheld` row removes the work from the
   current export while its historical `published` row remains in the registry.

Exactly one current row per represented work is mandatory. Zero current rows,
two current rows, version gaps, branches and cross-work supersession all fail
closed.

## Corrections and retractions

Never erase history. Add superseding identifier, decision and publication rows,
explain removals or corrections in the changelog, and preserve stable public IDs
where possible. A retracted or withdrawn work receives a new current `withheld`
publication row, remains absent from the current site and is documented in the
release change log.

## Rights and persistence

The repository currently states all rights reserved because choosing an open
code/data licence is an owner decision with lasting legal effect. Before a 1.0
or Zenodo release, select and document separate licences for repository code and
curated data/annotations, while respecting third-party metadata and full-text
rights. No full text is included in a release.
