# Public paper-sheet enrichment

Owner instruction, 13 September 2026: enrichment must be visible in the paper
sheets, not merely saved in a ledger or reported as a higher record count.
This is provisional-register UI maintenance, not approval of scientific results.

## Public contract

The existing double-click and keyboard-accessible `Apri scheda` button keep the
1990s-style dialog. It displays current registered bibliography and, separately,
source-supported reading aids, abstract-availability sources, retrieval metadata,
resolver DOI and dated access assessments. A resolver DOI never replaces the
registered DOI. A full-text locator does not establish open access.

The current ledgers do not retain original abstract bodies. Consequently an
abstract-bearing record offers its source and a clearly labelled paraphrase when
one has been recorded. `verified_abstract_source` is labelled as a synopsis of
the abstract, not the original abstract; preliminary synopses and metadata
warnings retain their different labels. No original text is invented or silently
substituted. Reviewer notes, evidence quotations, provider errors and private
scientific proposals are not public fields.

`site/paper-support.json` is a generated, closed release artifact. It reuses
CandidateRecord identity and existing abstract/access/provenance concepts mapped
in `ontology/modules/public-paper-support.json`. The runtime validator and field
allowlists live in `scripts/curation/build_paper_support.py`. The established
worker-facing `site/data/paper-register.json` contract does not change.

The supplementary artifact is deliberately not a separately edited or committed
ledger. It is rebuilt by the default `build_curator_stats.py` invocation in both
selected-paper preparation and every Pages release. The temporary `--output`
mode used for comparing committed `site/data` exports remains unchanged. Tests
verify the supplementary artifact is deterministic against the source ledgers;
the release verifier compares its actual HTTP-served content and both renderer
assets. Existing committed-export, scientific and privacy gates are retained.

## Source-to-sheet path

1. Existing enrichment writes the candidate-bound ledgers and reading aids.
2. The normal release builder joins exact candidate IDs, preferring the existing
   reading-aid override over the baseline, and projects only permitted fields.
3. Bibliography snapshots prevent a browser from joining different releases.
4. Every sheet opening requests support using `cache: no-store`. A timeout,
   missing artifact or generation mismatch is an update-verification error,
   never evidence that the abstract does not exist. Late responses cannot
   overwrite another open sheet.
5. The existing post-deployment `verify_published_register.py` also checks
   enriched support field by field and verifies the HTTP bytes of
   `paper-register.js` and `paper-sheet-support.js`. The receipt contains
   `paper_sheet_support` counts and renderer hashes. A stale synopsis fails even
   when the candidate count is unchanged.

No new scheduler, canonicalisation, source retrieval or scientific decision is
introduced. An enrichment still held in an unmerged PR is not publicly delivered.

## Regression checks

Run the full mandatory `AGENTS.md` block. The focused tests are:

```
python3 -m unittest tests.test_public_paper_support
node --test curator-app/test/public-paper-sheet.test.js
node --check site/paper-register.js
node --check site/paper-sheet-support.js
```

The tests cover actual override propagation, registry identity, deterministic
builds, source allowlists, private-field exclusion, same-count stale content,
DOM text rendering, cache refresh, failed requests, mixed releases, late
responses and DOI conflict labelling. After merge, a passing source/PR check is
insufficient: inspect the current deployment receipt and the displayed sheet.
