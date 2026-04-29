# Saturation Metrics

## Metrics per execution
- `candidate_novelty_rate = new_unique_candidates / unique_candidates_before`
- `eligible_increment_rate = new_eligible / eligible_before`
- `eligible_share_added_on_updated_total = new_eligible / eligible_after`
- `screening_yield = new_eligible / unique_candidates_screened`
- `new thematic codes` (count newly observed themes)
- `new mechanism codes` (count newly observed mechanisms)
- `new sector codes` (count newly observed sectors)
- `new method codes` (count newly observed methods)

## Baseline handling
If denominators are zero in early executions, record metric as `NA` and report absolute counts.

## Cautious saturation rule
Saturation can be claimed only after at least **two consecutive executions** where:
- `eligible_increment_rate < 2%`
- `screening_yield < 1–2%`
- no new thematic/mechanism/sector/method codes are added.

Set `saturation_status` accordingly and justify in `saturation_comment`.
