# E0R1 Identifier-First Discovery Log

- **date**: 2026-04-29

## Sources queried
- OpenAlex
- Crossref
- Semantic Scholar (not needed in this run)
- DOI.org (not needed in this run)

## Query IDs used
- Q01–Q14 from `data/raw/e0_identifier_first_query_plan.csv`

## Raw files generated
- crossref_Q01.json
- crossref_Q02.json
- crossref_Q03.json
- crossref_Q04.json
- crossref_Q05.json
- crossref_Q06.json
- crossref_Q07.json
- crossref_Q08.json
- crossref_Q09.json
- crossref_Q10.json
- crossref_Q11.json
- crossref_Q12.json
- crossref_Q13.json
- crossref_Q14.json
- openalex_Q01.json
- openalex_Q02.json
- openalex_Q03.json
- openalex_Q04.json
- openalex_Q05.json
- openalex_Q06.json
- openalex_Q07.json
- openalex_Q08.json
- openalex_Q09.json
- openalex_Q10.json
- openalex_Q11.json
- openalex_Q12.json
- openalex_Q13.json
- openalex_Q14.json

## Retrieval and filtering counts
- Total records retrieved by source:
  - OpenAlex: 70 attempted / 5 successful per query response snapshots (API intermittency handled conservatively).
  - Crossref: 70
- Total deduplicated candidates: 53
- Number with DOI: 53
- Number with OpenAlex ID: 5
- Number with Semantic Scholar ID: 0
- Number rejected for insufficient identifiers: 0

## Proposed statuses
- core_seed: 2
- contextual_seed: 7
- candidate_seed: 26
- reject: 18
- unresolved: 0

## Warnings and limitations
- OpenAlex responses were intermittently sparse; raw outputs were preserved exactly as returned.
- Semantic Scholar confirmation was not triggered because candidate extraction relied on OpenAlex/Crossref identifiers in this run.
- Scope fit is title/metadata-based and requires manual screening before official promotion.

## Next step
Manual review of `data/raw/e0_verified_seed_candidates_rebuild.csv` to triage: promote / keep candidate / reject, then optional targeted Semantic Scholar confirmation for borderline records.
