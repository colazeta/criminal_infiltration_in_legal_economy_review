# E0 Seed Metadata Verification Log

## Sources queried
Verification used only authorized metadata domains from the allowlist:
- Crossref API (`api.crossref.org`)
- DOI resolver (`doi.org`) when relevant
- OpenAlex and Semantic Scholar were reserved for tie-break/disambiguation, but this pass was dominated by Crossref exact/near-title checks.

## Matching logic
1. Start from provisional title in draft.
2. Query title on Crossref.
3. Accept **high-confidence match** only when title, author identity, and year/venue are consistent.
4. Mark **ambiguous_match** when only near-neighbor records appear.
5. Mark **no_confident_match** when no stable bibliographic identity is found.

## Handling uncertain matches
- If a match was close but not exact, candidate was kept as `candidate_seed` or `unresolved`.
- No DOI was inferred unless confidently verified.
- Broad descriptors (topic labels rather than paper citations) were not promoted.

## Unresolved candidates
The following remain unresolved and should not be promoted yet:
- E0-D005, E0-D006, E0-D030

## Candidates with status changes after verification
- **Promoted confidence**: E0-D001 (core), E0-D002 (contextual), E0-D004 (contextual), E0-D025 (contextual).
- **Downgraded/reject orientation**: E0-D011, E0-D016 due to weak specificity or insufficient legal-economy linkage.

## Safe-to-promote candidates (metadata + scope sufficiently stable)
- `core_seed`: E0-D001
- `contextual_seed`: E0-D002, E0-D004, E0-D025

## Keep outside official seed CSV for now
- All records with `metadata_confidence` low or unresolved in the matrix.
- Any record with `ambiguous_match` unless independently verified through a second authorized source.

## Notes
This pass is intentionally conservative and prioritizes bibliographic integrity over volume. A second targeted disambiguation pass (OpenAlex + Semantic Scholar IDs) is recommended before official promotion.
