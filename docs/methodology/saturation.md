# Saturation metrics

## Unit

E0 is excluded. One assessable cycle contains exactly one completed database
update, backward search and forward search, with all new unique candidates
screened and no unresolved retrieval failure.

## Metrics

- `candidate_novelty_rate = new_unique_candidates / unique_candidates_before`
- `eligible_increment_rate = sum(new_eligible) / eligible_before_at_cycle_start`
- `eligible_share_added_on_updated_total = new_eligible / eligible_after`
- `screening_yield = sum(new_eligible) / sum(unique_candidates_screened)`
- new theme, sector, mechanism, method, geography and outcome code counts.

Use `NA` when a denominator is zero. Undefined is not zero.

## Cautious stop rule

Reviewer consideration is permitted only after three consecutive complete
cycles where:

- eligible increment is below 2%;
- screening yield is below 2%;
- no controlled code is new;
- no unresolved retrieval failure could conceal material records.

`scripts/report_saturation.py` groups execution rows by `cycle_id`; incomplete,
failed or invalid cycles break the trailing sequence. E0 is the only execution
that may omit `cycle_id` and be excluded. Any E1, E2, E3 or other review
execution without `cycle_id` makes the report fail closed instead of being
silently discarded. Its strongest output is `REVIEW REQUIRED`, never an
automatic declaration of saturation.

Living surveillance continues after any stop decision because new research can
appear later.
