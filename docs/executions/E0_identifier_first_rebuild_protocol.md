# E0 Identifier-First Rebuild Protocol

## Why rebuild E0 with identifier-first discovery
The integrity audit showed that many prior E0 entries were paraphrased titles or topic labels rather than stable bibliographic entities. To prevent contamination of official seed registries, E0 must be rebuilt from verifiable metadata records only.

## Why provisional titles/topic labels are not acceptable
Provisional or generated titles:
- cannot be reliably deduplicated;
- cannot be independently re-fetched from metadata APIs;
- create false positives in scope screening;
- break auditability and reproducibility.

Therefore, a record cannot be treated as a seed candidate unless it has a stable bibliographic identity.

## Minimum evidence for seed-candidate eligibility
A record can enter rebuild candidate tables only if at least one condition holds:
1. DOI is present and resolvable; or
2. OpenAlex ID is present; or
3. Semantic Scholar ID is present; or
4. Stable book/report metadata exists with all of: title, authors/editors, year, publisher/institution, and URL (if available).

## Record classes
- **verified seed record**: stable identifier/metadata + passes scope screening.
- **search lead**: thematic pointer lacking stable paper-level identity.
- **rejected hallucinated/title-like record**: generated/paraphrased/non-resolvable record; cannot enter seed tables.

## Mandatory provenance rule
All future seed candidates must be derived from **raw metadata outputs** obtained from authorised sources (OpenAlex, Crossref, Semantic Scholar, DOI resolver), not from manually generated titles.

## Promotion logic for future rebuild pass
- `core_seed`: verified record + direct legal-economy/infiltration focus in title/abstract/keywords.
- `contextual_seed`: verified record + indispensable conceptual/methodological contribution.
- `candidate_seed`: verified metadata but scope still pending deeper screening.
- `reject`: verified metadata but out of scope.
