# Saturation Metrics

## Metrics per execution

- `candidate_novelty_rate = new_unique_candidates / unique_candidates_before`
- `eligible_increment_rate = new_eligible / eligible_before`
- `eligible_share_added_on_updated_total = new_eligible / eligible_after`
- `screening_yield = new_eligible / unique_candidates_screened`
- counts of newly observed mechanism, sector, method, geography and outcome codes.

When a denominator is zero, record `NA` and report the absolute count. Do not
replace an undefined rate with zero.

## Assessment unit

E0 is excluded. A saturation assessment cycle must include the planned database
update plus completed backward and forward snowballing over the eligible frontier,
with all new unique candidates screened.

## Cautious stop rule

Saturation may be considered only after **three consecutive completed cycles**
where all conditions hold:

- `eligible_increment_rate < 2%`;
- `screening_yield < 2%`;
- no new mechanism, sector, method, geography or outcome codes are added;
- no unresolved retrieval failure could plausibly conceal a material source of
  records.

The decision remains a documented reviewer judgement. Report per-cycle counts and
rates; never infer saturation from a single execution or E0.
