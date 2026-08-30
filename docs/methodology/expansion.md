# Literature expansion strategy

## Purpose

The aim is not to collect the largest possible pile of records. It is to expand
the corpus across terminology, disciplines, sectors, countries and citation
networks while retaining a reproducible account of what was searched, what was
found and why a work did or did not progress.

The strategy combines:

1. **known-item calibration**, so searches can retrieve benchmark works;
2. **concept-family searching**, so the review is not tied to the exact phrase
   “criminal infiltration”;
3. **semantic gap searching**, to find differently worded research;
4. **backward and forward citation searching**, to traverse the scholarly graph;
5. **coverage-gap analysis**, to target under-represented sectors, mechanisms,
   methods and geographies;
6. **living surveillance**, to identify new work after each formal cycle.

PRISMA 2020, PRISMA-S and PRISMA-LSR guide reporting and update transparency.
They do not by themselves prove that a search is complete.

## The coverage model

Every search family draws from several concept blocks. Blocks are adapted to
each source; one generic Boolean string must never be copied across providers.

| Block | Question | Illustrative language, not a fixed query |
|---|---|---|
| Criminal interest | Who benefits or exercises influence? | organised crime, mafia, criminal group/network, illicit actor, mafia-type association |
| Relational mechanism | What connects the actor to the legal economy? | infiltration, control, capture, ownership, participation, influence, embeddedness, collusion, front company |
| Legal-economy target | Where does the relationship operate? | company, firm, business, market, sector, procurement, supply chain, professional service, public contract |
| Organisational position | Through which role or asset? | shareholder, beneficial owner, director, manager, employee, intermediary, subcontractor, concession holder |
| Consequence or indicator | What is observed? | market distortion, procurement allocation, governance change, network position, firm performance, violence or corruption as an enabling mechanism |
| Geography and terminology | Which local vocabulary may hide the construct? | mafia penetration, criminal entrepreneurship, economic conditioning, territorial transplantation and equivalent non-English terms |

Money laundering, corruption, facilitation, passive investment and ordinary
corporate offending are near neighbours. They are searched when useful for
recall, but remain ineligible unless the relational infiltration test is met.

## Search workstreams

Each E1 execution covers the workstreams below or records why one is not
applicable. A workstream is a coverage objective, not a single query.

| ID | Workstream | Main blind spot addressed |
|---|---|---|
| W1 | Direct infiltration construct | Papers using the review's central vocabulary |
| W2 | Ownership, control and governance | Research describing the relationship without using “infiltration” |
| W3 | Markets, procurement and sectors | Sector-specific studies hidden in specialist literatures |
| W4 | Territorial expansion and embeddedness | Mafia transplantation, migration and durable local presence |
| W5 | Methods, data and indicators | Network, judicial, company, interview and mixed-method evidence |
| W6 | Geography and language | Local concepts and non-English titles/abstracts |
| W7 | Recent research and changed terminology | New publications and emerging labels since the previous coverage date |

## What each source is for

Sources overlap intentionally. Agreement is useful; unique retrievals expose
coverage gaps. Only providers authorised in
[`docs/governance/sources.md`](../governance/sources.md) may be used.

| Source | Primary role | It must not be used to do |
|---|---|---|
| Scite | Primary scholarly discovery, citation context and access/retraction signals | Decide eligibility from a result or citation label |
| OpenAlex | Reproducible structured/full-text search, author/topic expansion and citation metadata | Supply final metadata without verification |
| Exa Search | Natural-language semantic search for terminology and disciplinary blind spots | Replace a logged database search or silently fetch returned domains |
| Crossref | DOI resolution and bibliographic verification | Establish relevance from metadata alone |
| Semantic Scholar | Independent paper search and citation/reference graph | Override identity conflicts automatically |
| OpenCitations | Open DOI-based backward/forward citation links | Be treated as a complete citation graph |
| Unpaywall | Locate lawful open-access versions | Treat access status as screening evidence |

Scopus, Web of Science, ProQuest, Google Scholar or institutional catalogues may
be added only through the reviewed source-authorisation procedure. A manual
portal search is logged just as carefully as an API execution.

## Phase A: calibrate before expanding

1. Create a **positive benchmark set** of independently verified relevant works.
2. Create a **near-neighbour set** covering laundering, corruption, passive
   investment and corporate crime that should not pass without relational
   evidence.
3. Test each main query family against the positive benchmarks available in that
   source.
4. Revise a query that misses a benchmark for an explainable terminology reason;
   do not add every benchmark title as a hidden shortcut.
5. Record benchmark hits/misses and any source-indexing limitation in the cycle
   issue.

Calibration checks sensitivity and conceptual drift. It is not a statistical
estimate of total recall.

## Phase B: run E1 database and scholarly searches

For every source/query combination, record:

- cycle and execution ID;
- source, platform and access mode;
- exact source-specific query or natural-language prompt;
- filters, coverage dates, sort order, pagination and result cap;
- request date and repository commit used for deduplication;
- returned occurrences, unique candidates and errors;
- raw snapshot or verification artifact and checksum when retained.

Retrieve all results within the declared query/filter when the interface permits
it. If a provider imposes a cap, record it and examine overlap and the tail of the
ranking before claiming that the query was exhausted. Never describe “top 20” as
complete retrieval.

### Recommended first-pass division

- **Scite:** run all seven workstreams as scholarly searches.
- **OpenAlex:** run reproducible concept-family searches and structured filters;
  keep the OpenAlex work ID alongside any DOI.
- **Exa:** run distinct natural-language descriptions for W2, W4, W5 and W6,
  using the research-paper/publication category. Its purpose is semantic
  difference, not synonym repetition.
- **Crossref:** verify identifiers and manifestations after candidate discovery.

## Phase C: reconcile identity without losing provenance

Preserve every discovery occurrence before deduplication. Resolve candidates in
this order:

1. exact normalised DOI;
2. exact OpenAlex, Semantic Scholar or other stable scholarly identifier;
3. exact normalised title plus year;
4. approximate title similarity as a **possible duplicate flag only**.

Different DOI manifestations may belong to one canonical work. A DOI/title
collision is a metadata conflict and stops automatic reconciliation. Every
source/query that found the work remains a separate discovery event.

## Phase D: traverse the citation graph

After E1 candidate screening, define the citation frontier explicitly.

- **E2 backward search:** inspect references of eligible frontier works.
- **E3 forward search:** inspect works that cite eligible frontier works.
- Use at least two available citation providers when practical; record provider
  disagreement rather than silently taking the union as complete.
- Newly eligible works join the next frontier. A work already traversed at the
  same version does not need to be traversed again unless its citation graph or
  publication state changed.
- Targeted author, project, journal-special-issue and institutional searches may
  supplement E1 when the graph exposes a clear gap; they are separately logged.

The frontier, retrieval dates and failed identifiers belong in the review-cycle
issue. Unresolved citation failures make the cycle incomplete.

## Phase E: screen and code

1. Apply mechanical checks: scholarly type, stable identity and minimally usable
   bibliographic metadata.
2. Screen title/abstract against the four-part eligibility test.
3. Retrieve and examine full text when the abstract cannot support the decision.
4. Record an evidence locator and versioned decision; title words alone never
   establish eligibility.
5. Apply controlled codes only for information supported by examined evidence.
6. Keep ambiguous records pending. Do not force them into an included/excluded
   binary merely to close the cycle.

Where two people screen, retain individual assessments and adjudication. In all
cases, publication requires an independent curator decision after screening.

## Phase F: measure coverage and choose the next search

After each complete cycle, report:

| Measure | What it answers |
|---|---|
| Benchmark retrieval | Did the query families find known relevant works indexed by the source? |
| Source/query marginal yield | Which source or query added candidates and eligible works not found elsewhere? |
| Source overlap | Are sources repeating the same records or covering distinct literatures? |
| Candidate novelty rate | How quickly is the unique candidate pool still growing? |
| Screening yield | How often do newly screened unique works become eligible? |
| Eligible increment | How much did the eligible corpus grow? |
| New controlled codes | Did a new theme, sector, mechanism, method, geography or outcome appear? |
| Failure inventory | Could unavailable sources or unresolved identities conceal material work? |

Use the controlled-code coverage table to select the next workstream. A cell with
little evidence is a reason to investigate, not proof that no literature exists.

## Formal cycle and surveillance cadence

### Formal expansion cycle

A complete assessable cycle contains:

1. one reconciled E1 update covering the declared workstreams;
2. one backward search over the declared frontier;
3. one forward search over the declared frontier;
4. screening of all new unique candidates;
5. no unresolved retrieval failure that could materially affect the result.

Run a formal cycle for each planned corpus update and after a material change to
scope, sources or query design.

### Living surveillance

When scheduled capacity is available, the Work automation runs every two weeks:

- Scite is the primary scholarly channel;
- Exa is an independent semantic gap channel;
- GitHub receives at most one idempotent, deduplicated intake issue;
- no file, registry, branch, PR, eligibility or publication state is changed.

Surveillance leads enter the next formal cycle. A surveillance run is not an E1–E3
cycle and cannot support saturation.

## Stop rule

The exact rule remains in [`saturation.md`](saturation.md). Reviewer consideration
is possible only after three consecutive complete cycles with eligible increment
below 2%, screening yield below 2%, no new controlled code and no unresolved
retrieval failure. The automated output is only `REVIEW REQUIRED`; a person makes
and documents any stop decision. Living surveillance continues afterward.

## Definition of done for the first expansion

- [ ] Positive and near-neighbour benchmark sets are frozen and documented.
- [ ] W1–W7 have an explicit source/query plan or a stated non-applicability.
- [ ] Scite, OpenAlex and Exa E1 searches are completed and reconciled.
- [ ] DOI/identifier metadata are verified through approved sources.
- [ ] Backward and forward citation searches cover the declared frontier.
- [ ] All new unique candidates have a current screening state.
- [ ] Provider failures, caps and inaccessible records are visible.
- [ ] Cycle metrics and source/query marginal yield are computed.
- [ ] Any publication proposal is a separate human-reviewed curator change.

## Reporting references

- [PRISMA 2020 checklist](https://www.prisma-statement.org/prisma-2020-checklist)
- [PRISMA 2020 flow diagram](https://www.prisma-statement.org/prisma-2020-flow-diagram)
- [PRISMA-S search-reporting extension](https://www.prisma-statement.org/prisma-search)
- [PRISMA-LSR living-review extension](https://www.prisma-statement.org/lsr)
- [OpenAlex API reference](https://help.openalex.org/api/)
- [Crossref REST API documentation](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
- [Semantic Scholar Academic Graph API](https://www.semanticscholar.org/product/api)
- [OpenCitations Index API](https://api.opencitations.net/index)
- [Exa research-publication search](https://exa.ai/blog/publications-search)
