# Literature Review Protocol

**Protocol version:** 1.0

**Status:** authoritative

**Product:** living curated literature archive and evidence map

## Aim

Identify, assess and organise research on criminal infiltration in the legal
economy through a reproducible, execution-based review. The archive is the
primary public product; articles and other syntheses are downstream outputs.

The review is not restricted to studies using the terms *mafia* or *organised
crime*. It is, however, restricted to a precise organisational relationship
between a criminal interest and an actor, organisation, asset, market or
governance arrangement in the legal economy.

## Conceptual boundary

A study can enter the core corpus only when the available evidence supports all
four elements:

1. **Criminal interest or actor:** a criminal individual, group, network or
   organisation is identifiable analytically.
2. **Legal-economy target:** the study concerns a legal firm, profession,
   ownership structure, procurement process, sector, market or public/private
   governance arrangement.
3. **Relational presence:** the criminal interest obtains or seeks sustained
   access, participation, influence, control or organisational embeddedness.
4. **Analytical centrality:** this relationship is examined, measured or used in
   a substantive inference rather than mentioned incidentally.

Passive investment, a single laundering transaction, one-off facilitation,
transactional corruption, generic corporate offending and the mere use of a
legal entity are not infiltration by themselves. They may enter the contextual
corpus only when their relevance to the infiltration relationship is explicit.

## Research questions

1. How is criminal infiltration conceptualised and distinguished from adjacent
   phenomena?
2. Through which mechanisms and organisational positions do criminal interests
   obtain access, influence, participation or control in the legal economy?
3. Which sectors, ownership structures and governance arrangements are studied?
4. Which empirical methods, indicators and data sources are used, and what
   inferences do they support?
5. Which organisational, market, public-finance and social outcomes are associated
   with infiltration?

Construct–evidence alignment is assessed under RQ4: the purpose is to determine
whether each study's indicators and evidence justify the inference it makes
about infiltration.

## Units of record

- **Work:** a canonical scholarly item, independent of duplicate database records
  or identifier variants.
- **Identifier/manifestation:** DOI or source identifier linked to a work.
- **Discovery event:** one retrieval occurrence for one execution, feed, query or
  source work.
- **Screening decision:** a versioned decision at title/abstract, full-text or
  seed-validation stage.
- **Code:** a controlled analytic classification supported by abstract or
  full-text evidence.

## Discovery workflow

1. **E0 — seed construction:** precision-first manual and identifier-based
   discovery. E0 establishes the starting nucleus and cannot establish saturation.
2. **E1 — database/API discovery:** source-specific searches on authorised feeds.
3. **E2 — backward snowballing:** references of included source works.
4. **E3 — forward snowballing:** works citing included source works.
5. Repeat E1–E3 executions, screen new unique works and update codes and metrics.

Every retrieval must preserve its execution, query, feed, raw response and
failure state. A zero-result response and a failed request are different outcomes.

## Screening workflow

1. Deduplicate source records at work level while retaining every discovery event.
2. Screen title and abstract against the four-part conceptual boundary.
3. Use `maybe_full_text_needed` when evidence is insufficient.
4. Screen full text when required and record a current decision.
5. Apply core/contextual status and analytic codes only after the supporting text
   has been examined.
6. Recheck a documented sample of decisions within reviewer to measure stability;
   record changes as new decisions rather than overwriting history.

The decision vocabulary and exclusion reasons are defined only in
`docs/eligibility_codebook.md`.

## Public archive rule

The site is generated exclusively from canonical registries. A work is public
only if it has an included canonical status, at least one discovery event and
exactly one current eligible decision. Pending, rejected, duplicate and unresolved
records remain in the editorial layer.

## Saturation

Saturation is assessed using the versioned rule in `docs/saturation_metrics.md`.
No E0 metric and no single low-yield execution is sufficient. Until the rule is
met, the public product must be described as a living archive rather than a
complete corpus.

## Reporting

Each execution reports retrieval successes and failures, raw and unique records,
screening decisions, exclusion reasons, additions to the canonical corpus, new
codes, unresolved cases and saturation metrics. The public site reports the
corpus version and source snapshot without exposing internal reviewer notes or
copyrighted full text.
