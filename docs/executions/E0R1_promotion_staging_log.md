# E0R1 Promotion Staging Log

- Clean pre-E0 records staged: 4
- E0R1 promoted records considered: 9
- Final staged records after deduplication: 13

## Duplicates removed or flagged
- No duplicates detected between clean pre-E0 and E0R1 promoted records.

## Strata covered
- conceptual_theoretical
- laundering_legal_business
- mafia_legal_business
- methodological
- money_laundering_legal_economy
- procurement_market_capture
- sectoral_infiltration

## Remaining gaps
- Ownership/corporate-control still sparse in promotable set.
- Sectoral infiltration coverage remains limited and should be expanded beyond few contextual records.
- Criminal firms/entrepreneurship still underrepresented among promotable records.

## Why this is staging and not official import
This file is a controlled staging layer combining prior clean records and E0R1 promotable outputs, pending final manual validation and balance checks before writing to official `data/raw/e0_seed_candidates.csv`.

## Next step before official E0 population
Conduct final human validation on staged rows (especially contextual entries), then import only approved rows into official seed CSV and continue targeted identifier-first retrieval for uncovered strata.
