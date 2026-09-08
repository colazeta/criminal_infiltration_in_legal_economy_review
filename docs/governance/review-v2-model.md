# Review V2: publication ontology and review-specific model

Implementation authorised by the owner after the clean-restart assessment. This
is a versioned technical/semantic contract, not approval of any proposed seed or
any scientific outcome. The existing corpus remains in its legacy namespace
until the operational readiness conditions are satisfied.

The normative profile is `ontology/cile-review-profile.yaml` **0.2.0**. Its private
storage mapping is `ontology/modules/review-v2.json`; every SQL table and column
must map to a declared class and slot. `scripts/ontology/validate_ontology.py`
creates an isolated database, checks the mapping, append-only guards and empty
start state. `scripts/ontology/build_model_browser.py` generates the public
[model browser](../../site/model.html) from the contract; no corpus data enter it.

## Bibliographic model

| Entity | Meaning and boundary |
|---|---|
| ScholarlyWork | Intellectual identity independent of eligibility, publication on this site or possession of a DOI. Articles, chapters, books, working papers, preprints, conference papers, reports and theses can be represented; representation does not settle source-scope eligibility. |
| Expression | A content/language version: preprint, submitted or accepted manuscript, version of record, revision or translation. Its publication date, precision, venue, volume, issue, pages, article number and edition remain version-specific. |
| Manifestation | A concrete PDF, HTML or other embodiment of an Expression. Its locator, acquired content hash, access, licence and retention basis are separate. A URL with a PDF suffix remains locator_only until bytes are acquired. |
| Agent / Contribution | Named person or organisation, ordered authorship/editor/translator roles, publication-specific affiliation and optional source-attested CRediT role. Names are not silently disambiguated. |
| PublicationVenue | Journal, edited book, series, conference or repository, with publisher and optional parent venue. |
| Identifier | DOI, ISBN, ISSN, ORCID, ROR, handle, arXiv, PMID, stable URL or another sourced identifier attached to exactly one entity. No identifier creates scientific inclusion or silently merges two works. |
| DocumentSection | Located, ordered abstract, introduction/background, methods, results, discussion, conclusions, limitations, references, appendices or other section. These are optional observations, not a mandatory IMRaD template imposed on books and theoretical papers. |
| PublicationDeclaration | Source-attested funding, conflicts, ethics, data/code availability, acknowledgement, correction or retraction statement. Missing statements are unknown, not negative declarations. |
| MetadataAssertion | A sourced, timestamped value that may be proposed, verified or disputed; earlier assertions remain. |
| CitationRelation | Directed citing/cited relation with reference locator and verification; related-paper recommendations do not become citations. |

External standards are reused at the level their meanings support. The former
`ScholarlyWork exactMatch IncludedSource` mapping was removed: a bibliography is
not an included corpus. FaBiO/FRBR inform Work–Expression–Manifestation; BIBO
supplies bibliographic properties; PROV-O supplies attribution and derivation;
Web Annotation informs source-targeted spans. Local operational concepts remain
local. The profile does not claim complete FRBR, FaBiO or RDF-store conformance.

References inspected for this implementation:
[FaBiO](https://sparontologies.github.io/fabio/current/fabio.html),
[Schema.org ScholarlyArticle](https://schema.org/ScholarlyArticle),
[W3C PROV-O](https://www.w3.org/TR/prov-o/),
[W3C Web Annotation](https://www.w3.org/TR/annotation-model/).

## Review-specific model

ReviewCandidate carries `review_id`, identity state, stage and record version.
LegacyReference is informational: it cannot suppress a V2 discovery or supply
V2 eligibility. The nine approved topic definitions live in `ontology/vocabularies/topics-v2.json`; they are multi-label and do not recode legacy. The six infiltration relations are non-ordinal, potentially
coexisting relations. Profile 0.1.0 and its former hierarchy are preserved under
`ontology/legacy/0.1.0/`; historical coding rows are not recoded.

EvidenceSource distinguishes author abstract, publisher summary, full text,
excerpt, metadata, triage note and model summary. Private R2 stores the source;
D1 holds its hash, rights basis and locator. A generated note cannot support a
YES/NO criterion. Source offsets refer to the exact preserved string; they are
UTF-16 code-unit offsets, matching browser text selection and JavaScript slicing.

A DecisionProposal contains four separate assessments: criminal actor/interest,
legal-economy object, sustained relationship and substantive analysis. Each has
YES/NO/UNCERTAIN, rationale and verified source-span IDs. Core requires four YES,
resolved work identity and human approval. Missing text remains UNCERTAIN.
Contextual contribution and publication require their own reasons/approvals.

The private proposal is immutable. Only a hash-only manifest leaves private
storage. A human reviews the exact payload in the console and the exact PR head.
The importer verifies the merged PR, repository, human review, head SHA,
protocol and payload hash before atomically recording the receipt, four criteria
and decision. Stale candidate versions abort the batch. Re-import is idempotent;
scientific supersession preserves prior decisions. Publication is a separate
approval table and is never produced by screening import.

The legacy issue-form path remains a legacy contract and prepares a human-review
PR. It is not described as a V2 four-criterion decision. The old regex assistant
now abstains from scientific classification; the model assistant is explicitly
disabled pending approved calibration, model selection and measured quality.

## Operations, activation and rollback

SearchDay represents every expected Rome date. RunAttempt keeps actual execution
times separate from scheduled dates, with at most three attempts, a lease and
retry timing. QueryExecution preserves failures and at most one successful
checkpoint per source/query/day. DiscoveryOccurrence retains repetitions.
Outbox records delivery intent independently of external availability.

The deployed supervisor is gated by `REVIEW_V2_RUNNER_ENABLED=false`; merely
applying the empty SQL migration does not create a Review or start a search.
The owner-approved discovery policy is Exa-only (CILE-DAILY-v3). Seven approved
source/window query definitions, Exa credentials and preserved project budgets
are prerequisites to activation. The retired Consensus adapter is neither
called nor required. Old two-source query manifests cannot activate this runner.
This changes the operational source set, not CILE-4PT-OA-v3 scientific criteria.

`scripts/review_v2/prepare_cloudflare.py` can prepare a dedicated private D1
database, R2 bucket, queue and dead-letter queue using the existing deployment
credential. It does not grant permissions, enable public bucket access or change
an account plan. If permissions are absent, it reports the blocker and the
validated legacy safety fixes can still deploy. An existing nonmatching schema
requires an additive migration rather than an overwrite.

Before cutover, `scripts/review_v2/preserve.py` must snapshot Git history and
byte-identical tracked files plus complete external exports of issues/comments,
PR/reviews, ledger, automation, deployments and persistent coordinator state.
An incomplete external snapshot is explicitly `cutover_ready=false`. A restore
uses a new directory and checks every restored file hash. These tools never
reset the corpus or declare an incomplete snapshot complete.

T0 must be selected only after source preflight, private-storage validation,
complete external snapshot/restore and suspension of legacy writers. No T0,
seed membership, screening, coding or publication is inserted by these changes.
After T0, rollback pauses V2 delivery/writes and restores the previous public
pointer; it retains all V2 events and does not copy their decisions into legacy.
Both writers must never be active at once. Database changes stay additive.

## Remaining production gates

The repository API available during implementation can create and merge PRs but
does not expose branch-protection administration. Required checks and human
review protection still need repository administrator configuration. Removing
the scientific auto-merge command and enforcing exact human approval in the V2
importer are code protections; they are not a claim that GitHub main is protected.

The publication importer/export and model-based assistant must remain inactive
until their independent scientific/calibration approvals exist. No approved seed
set, gold labels or publication approvals are manufactured to complete a rollout.
