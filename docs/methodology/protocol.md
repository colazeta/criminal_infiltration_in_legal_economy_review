# Living literature review protocol

**Protocol version:** 1.1  
**Status:** active  
**Product:** living curated evidence map and publication archive

## Aim and questions

The review identifies and organises research on sustained criminal access,
participation, influence, control or embeddedness in the legal economy.

1. How is criminal infiltration defined and distinguished from adjacent crime?
2. Which mechanisms and organisational positions enable it?
3. Which sectors, markets, ownership and governance arrangements are studied?
4. Which methods, indicators and data sources support the inference?
5. Which organisational, market, public-finance and social outcomes are linked?

## Units

- **Work:** one canonical scholarly item.
- **Identifier/manifestation:** a DOI or source record linked to a work.
- **Discovery event:** one occurrence from one execution, query, feed or source work.
- **Screening decision:** a versioned judgement at seed, title/abstract or full-text stage.
- **Publication annotation:** an approved public relevance note and topic.
- **Code:** a controlled analytic classification supported by examined evidence.

## Process

1. E0 creates a high-precision seed nucleus and cannot establish saturation.
2. E1 runs source-specific database or scholarly-search strategies.
3. E2 performs backward citation searching from eligible works.
4. E3 performs forward citation searching from eligible works.
5. New unique works are screened and coded; complete E1–E3 cycles are repeated.
6. Living surveillance continues even after an initial saturation judgement.

Retrieval preserves the exact strategy, source/platform, date, result occurrence
and failure status. Screening never overwrites decision history. A current
decision may be changed only by adding a superseding decision in a reviewed PR.

## Selection and coding

The [eligibility codebook](eligibility.md) is the sole decision vocabulary.
Title keywords can prioritise; they cannot establish eligibility. Abstract or
full text is examined whenever the four-part construct test cannot be answered
with confidence. Codes require an evidence locator and controlled taxonomy.

The present published record is explicitly identified as the initial seed
nucleus. A second canonical seed candidate is withheld pending substantive
evidence screening. Public presence is not a claim of complete searching, final
saturation or quantitative synthesis.

## Public archive

Publication is a separate curated action after canonicalisation and screening.
The builder applies the gate in [the data contract](../governance/data-model.md).
It does not read editorial or legacy data and performs no network request.

## Review management

The maintainer resolves conflicts and approves publication changes. Where more
than one screener participates, individual assessments and adjudication must be
recorded before the consensus decision. Any automation used for retrieval,
deduplication or prioritisation is declared in the execution record.

## Amendments

Material changes to scope, eligibility, sources, selection, coding or stop rules
increment the protocol version, update `CHANGELOG.md`, and state whether earlier
records require reassessment. Amendments are never applied silently.
