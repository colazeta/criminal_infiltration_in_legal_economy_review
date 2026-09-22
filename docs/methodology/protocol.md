# Living literature review protocol

**Protocol version:** 1.3  
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

Scheduled living surveillance uses **Parallel Search as the default discovery provider**.
Exa is optional only when it is positively available and materially useful for recall or
verification. A completed v3 batch records one final provider; any incomplete optional
provider attempt remains diagnostic provenance and is never reinterpreted as a zero-result
search. W1-W7 adaptive depth, durable query checkpoints, identity resolution and intake
rules are unchanged. Consensus remains excluded.

Retrieval preserves the exact strategy, source/platform, date, result occurrence
and failure status. Screening never overwrites decision history. A current
decision may be changed only by adding a superseding decision in a reviewed PR.

## Selection and coding

The [eligibility codebook](eligibility.md) is the sole decision vocabulary.
Title keywords can prioritise; they cannot establish eligibility. Abstract or
full text is examined whenever the four-part construct test cannot be answered
with confidence. Codes require an evidence locator and controlled taxonomy.

No record is currently published. Candidate metadata and screening outcomes
remain outside the public archive until independent publication approval is
complete. This empty public state is not a claim that no relevant literature
exists, and the project makes no claim of complete searching, final saturation
or quantitative synthesis.

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

### 2026-09-09 — Exa-limit fallback

Protocol 1.2 authorised Parallel Search as a failover for a documented Exa provider limit
in living surveillance. This remains historical provenance for runs executed under that
contract.

### 2026-09-22 — Parallel-Search-first scheduled surveillance

Protocol 1.3 makes Parallel Search the default scheduled W1-W7 provider and makes Exa
optional when positively available and materially useful. It does not change scientific
scope, the four-part eligibility construct, canonical-identity rules, formal E1-E3
expansion or saturation criteria. Earlier runs retain their original provider provenance
and require no reassessment because the amendment changes surveillance operations, not
screening or coding.

Material changes to scope, eligibility, sources, selection, coding or stop rules
increment the protocol version, update `CHANGELOG.md`, and state whether earlier
records require reassessment. Amendments are never applied silently.
