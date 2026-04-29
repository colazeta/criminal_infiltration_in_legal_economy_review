# E0 Pre-Import Audit

## Scope
Audit executed on `data/raw/e0_seed_promotion_staging.csv` before official seed import.

## Checks performed
- duplicate DOI
- duplicate normalised title
- missing DOI where expected
- missing authors/year/venue
- weak reason_for_seed_inclusion
- questionable seed_status/seed_category
- contextual imbalance risk

## Decision counts
- import_now: 2
- import_after_metadata_fix: 2
- hold_for_manual_review: 9
- remove_from_import: 0

## Key findings
- Contextual dominance remains high (contextual=11, core=2); justification is required before final import freeze.
- No hard duplicate DOI/title collisions detected in staged set.
- Some records need metadata normalization (e.g., contextual rationale wording consistency).

## Remaining gaps by seed stratum
- conceptual_theoretical: 1 staged records (import_now or fixable)
- mafia_legal_business: 1 staged records (import_now or fixable)
- laundering_legal_business: 2 staged records (import_now or fixable)
- Ownership/corporate-control and criminal firms remain undercovered in promotable subset.

## Is official E0 population defensible now?
Partially defensible. A controlled import of `import_now` records is possible, but full E0 population should wait until metadata fixes and contextual-balance justification are completed.
