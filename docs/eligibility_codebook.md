# Eligibility Codebook

## Core test

Use four questions in order:

1. Is a criminal interest or actor analytically identifiable?
2. Is there a target in the legal economy?
3. Is there evidence of sustained access, participation, influence, control or
   organisational embeddedness?
4. Is that relationship substantively analysed rather than merely mentioned?

A confident **yes** to all four supports `eligible_core`. Uncertainty about
questions 2–4 requires abstract or full-text review; it does not support automatic
inclusion.

## Current decision categories

- `eligible_core`: the infiltration relationship is central and supported by the
  evidence examined.
- `eligible_contextual`: the work is not direct infiltration evidence but makes an
  explicit and necessary conceptual, comparative or methodological contribution.
- `maybe_full_text_needed`: title/abstract evidence is insufficient for a final
  decision.
- `not_eligible`: the work does not meet the conceptual boundary.
- `duplicate`: the source record is another representation of an existing work.
- `not_academic`: the item is outside the scholarly-source scope.
- `not_retrievable`: the evidence required for screening could not be obtained.

`eligible_core` and `eligible_contextual` describe analytic relevance. Seed,
database discovery and snowballing describe provenance. These dimensions must
never be stored as substitutes for one another.

## Adjacent phenomena

The following do not constitute criminal infiltration without further evidence:

- passive holding of legal assets;
- laundering proceeds through a company or market;
- one-off corruption or collusion;
- professional facilitation of an isolated offence;
- generic corporate crime by an otherwise legal company;
- use of a shell company without organisational presence in legal activity;
- organised-crime violence without a legal-economy relationship.

Such work may be `eligible_contextual` only when the record contains a specific,
documented reason for its contribution to the infiltration construct or method.

## Standard exclusion reason codes

- `TOPIC_OFF_SCOPE`
- `NO_CRIMINAL_ACTOR_OR_INTEREST`
- `NO_LEGAL_ECONOMY_LINK`
- `NO_INFILTRATION_RELATION`
- `MENTION_ONLY_NOT_ANALYTICAL`
- `ADJACENT_PHENOMENON_ONLY`
- `CRIME_DOMAIN_MISMATCH`
- `DOCUMENT_TYPE_EXCLUDED`
- `LANGUAGE_EXCLUDED`
- `DUPLICATE_RECORD`
- `NOT_ACADEMIC_SOURCE`
- `FULL_TEXT_UNAVAILABLE`

Every non-eligible current decision requires one primary reason code and a short
record-specific comment.

## Evidence and coding rules

- Title keywords can prioritise screening but cannot determine eligibility.
- A valid DOI establishes an identifier, not complete or correct metadata.
- Codes for mechanism, sector, geography, actor, method, data source and outcome
  require abstract or full-text support.
- Missing information remains blank or null; it is never inferred for display.
- When one work has several identifiers or manifestations, retain one canonical
  work and link the aliases rather than selecting by DOI alone.
