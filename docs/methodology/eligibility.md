# Eligibility codebook

## Four-part core test

All four must be supported for `eligible_core`:

1. an analytically identifiable criminal actor or interest;
2. a firm, profession, asset, procurement process, market, sector or governance
   arrangement in the legal economy;
3. sustained access, participation, influence, control or organisational
   embeddedness;
4. substantive analysis of that relationship, not an incidental mention.

## Current decisions

- `eligible_core`: the infiltration relationship is central and supported.
- `eligible_contextual`: an explicit, necessary conceptual, comparative or
  methodological contribution, but not direct infiltration evidence.
- `maybe_full_text_needed`: available evidence is insufficient.
- `not_eligible`: the conceptual boundary is not met.
- `duplicate`: another representation of a canonical work.
- `not_academic`: outside the scholarly-source scope.
- `not_retrievable`: evidence needed for screening could not be obtained.

Provenance (seed, database, backward, forward), eligibility (the decision above)
and analytic tier (core/contextual) are separate dimensions.

## Adjacent phenomena

Passive investment, one-off laundering, isolated corruption/collusion,
professional facilitation, generic corporate crime, shell-company use or
organised-crime violence do not constitute infiltration without the sustained
legal-economy relationship. They may be contextual only with a specific,
documented contribution.

## Broader AML collection

Core eligibility and broader subject relevance are separate judgements. A
scholarly work may receive `not_eligible` under the four-part infiltration test
and still be explicitly routed to the governed `broader_aml` collection when it
substantively concerns money laundering or economic/financial crime.

That routing:

- does not change the `not_eligible` decision or its controlled exclusion code;
- requires a separate, record-specific explanation of the broader relevance;
- does not count toward the core or contextual corpus, review yields or
  saturation;
- does not make the candidate public. Canonical metadata verification and a
  versioned secondary-publication approval remain necessary.

## Exclusion reason codes

The machine-readable controlled list is
[`data/registry/exclusion_reasons.csv`](../../data/registry/exclusion_reasons.csv).
The codes below must match it exactly:

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

Every current non-eligible decision needs one primary code and a record-specific
comment.

## Evidence rules

- A DOI verifies an identifier, not the entire citation.
- Missing data remain blank/null; never infer them for display.
- Title text may triage but cannot decide eligibility.
- Mechanism, sector, geography, actor, method, data-source and outcome codes need
  an abstract/full-text evidence locator.
- Multiple identifiers/manifestations map to one work; DOI equality is neither a
  necessary nor sufficient test of work identity.
