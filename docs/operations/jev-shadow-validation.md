# Jev shadow semantic validation

Protocol: `CILE-JEV-SHADOW-1`.

Owner instruction: 20 September 2026.

## Purpose

This integration evaluates whether TypeSafe Jev can provide useful calibrated,
typed semantic judgements across the living review without changing any current
scientific, identity, publication or completion state.

The initial deployment is **observe-only / shadow**. A Jev answer is an
`AssistantRecommendation`-like external judgement for evaluation purposes only.
It is not a screening decision, canonical-identity relation, scientific
classification, completion receipt or publication approval.

The repository rules in `AGENTS.md` remain authoritative. In particular, this
protocol does not authorise automatic assignment of scientific eligibility or
canonical identity.

## Provider and model pin

The HTTP client uses the documented TypeSafe endpoint:

`POST https://api.typesafe.ai/v1/systemone`

with bearer authentication from `TYPESAFE_API_KEY`.

Calibration is pinned to `jev-1.13.0`. Do not replace it with
`jev-latest` during a benchmark or threshold-calibration series. TypeSafe
documents that aliases can move when a new release ships and recommends a
versioned ID when thresholds have been calibrated against a particular model.

The current API returns typed `Noul`, `Choice` and `Score` answers. The
client validates the complete response shape, exact question set, requested
version, probability ranges/distributions and usage counters before any receipt
is written. HTTP 429 and 529 are retried with bounded backoff; authentication,
validation, malformed response, timeout and other failures fail closed.

Primary external references:

- <https://docs.typesafe.ai/introduction/quickstart>
- <https://docs.typesafe.ai/api>
- <https://docs.typesafe.ai/models>
- <https://typesafe.ai/legal/privacy-policy>
- <https://typesafe.ai/legal/data-processing>

## Data boundary

The first approved Jev execution may transmit only bounded candidate metadata
and short **derived support summaries** or structured proposal fields already
authorised for this purpose.

The shadow policy explicitly rejects fields whose names indicate:

- private or retained full text;
- verbatim abstract text;
- raw source bodies or PDF bytes;
- reviewer/private notes;
- credentials, secrets, API keys or tokens.

Unknown fields also fail instead of being silently discarded. URLs must be
HTTPS. Long text fields and list cardinalities are bounded.

This restriction is deliberate. TypeSafe states that customer requests and
responses are not used to train Jev, but its general privacy policy describes
retention for as long as reasonably necessary for the service/business purpose,
and service processing is hosted in the United States. Zero-data-retention is
described separately for enterprise customers. Until a later reviewed
rights/privacy decision changes this contract, **no private retained full text or
verbatim abstract is sent to Jev**.

The raw state submitted to Jev is not persisted by this runner. The local shadow
receipt stores only its SHA-256 digest, the versioned question-set digest, typed
answers, model identity, usage and a subject identifier.

## Question sets

### `candidate_screening_v1`

Atomic, non-authoritative judgements for:

- scholarly scope;
- each of the four infiltration criteria independently;
- evidence sufficiency;
- whether richer/full-text evidence is needed;
- adjacent-phenomenon-only risk;
- each of the six scientific-framework classes independently.

No aggregate `eligible_core`, `eligible_contextual` or exclusion decision is
asked of Jev in this first contract.

### `metadata_assertion_v1`

Given one bounded bibliographic assertion and one or more explicit evidence
observations, Jev classifies the assertion as:

- `supported`;
- `contradicted`; or
- `insufficient_evidence`.

A separate Noul estimates whether a material metadata conflict is present.
Conflicting observations remain visible; the harness never chooses the last
string as truth.

### `identity_relation_v1`

Given two bounded bibliographic records and explicit relation evidence, Jev
classifies:

- `same_manifestation`;
- `same_work_different_manifestation`;
- `different_work`; or
- `insufficient_evidence`.

This is a recommendation only. It does not create a `ScholarlyWork`, merge
CandidateRecords or write a canonical relation.

### `enrichment_qa_v1`

Checks the support for the existing research-sheet dimensions and separately
asks about material omissions, overstatement and evidence sufficiency. It does
not generate a replacement assessment.

## Running a dry validation

Prepare a local JSON file containing `kind` and the allowed bounded fields.
For example:

```json
{
  "kind": "candidate_screening",
  "candidate": {
    "candidate_id": "CAND-EXAMPLE",
    "title": "Example scholarly work",
    "authors": "A. Researcher",
    "year": 2026
  },
  "evidence": {
    "source_basis": "verified publisher metadata plus derived research synopsis",
    "evidence_scope": "abstract_only",
    "research_synopsis": "Short analyst-derived synopsis.",
    "legal_economy_synopsis": "Short analyst-derived synopsis.",
    "relationship_synopsis": "Short analyst-derived synopsis.",
    "source_urls": ["https://example.org/article"]
  }
}
```

Validate it without contacting TypeSafe:

```bash
node scripts/jev/run-shadow.mjs --input /path/to/input.json --dry-run
```

The receipt is written with mode `0600` below the gitignored
`outputs/jev-shadow/` directory unless `--output` is supplied.

## First live call

A live call is permitted only after this provider-governance amendment is merged.

Create a TypeSafe API key in the TypeSafe console and provide it to the process
as:

```bash
export TYPESAFE_API_KEY='...'
node scripts/jev/run-shadow.mjs --input /path/to/input.json
```

Do not commit the key, put it in an issue/comment, or place it in a public CI
variable. This PR does not add a GitHub Actions workflow or require a repository
secret. A future automated workflow must be reviewed separately.

## Validation programme

### Stage 1 — harness verification

Use approximately 20–30 deliberately heterogeneous, already understood cases to
verify:

- data-boundary correctness;
- stable request/receipt identity;
- response validation;
- no leakage from existing decisions into the Jev state;
- useful separation between probability and uncertainty;
- behaviour on conflicts, incomplete evidence and manifestation differences.

This stage validates the harness before evaluating model performance.

### Stage 2 — full shadow replay

Once Stage 1 is technically sound, evaluate the current CandidateRecord
population in shadow mode. Store derived evaluation data separately from all
authoritative scientific tables.

For each question and relevant human/reference outcome, compute at least:

- accuracy;
- precision/recall/specificity where meaningful;
- false-inclusion and false-exclusion rates;
- Brier score for binary probability outputs;
- calibration / expected calibration error;
- coverage-versus-error curves at candidate thresholds.

Do not use one global threshold across different questions unless the evidence
supports doing so.

### Stage 3 — advisory and routing experiments

Only after a reviewed calibration report may a later change use Jev signals to
prioritise queues or route low-risk work. Scientific eligibility, canonical
identity and F7 validation remain unchanged until a separate explicit owner
instruction and governance change authorise otherwise.

## Relationship to F0–F7 and Kora

The intended long-term architecture is:

- deterministic code: schemas, hashes, permissions, identities already proven
  mechanically, CAS, receipts and integrity;
- generative assessment model: extraction and synthesis;
- Jev: typed semantic judgements and QA;
- Kora: control-plane routing and allowed transitions;
- archive/database: persisted source of truth;
- human/scientific gate: decisions that remain owner-governed.

This PR implements only the Jev shadow layer. It does not change F0–F7 routing,
the living-review scheduler, the Kora pilot or any writer.

## Validation

The implementation is expected to pass:

```bash
node --check curator-app/src/jev-client.js
node --check curator-app/src/jev-policy.js
node --check curator-app/src/jev-question-sets.js
node --check scripts/jev/run-shadow.mjs
node --test curator-app/test/jev-client.test.js curator-app/test/jev-policy.test.js
```

The complete repository test suite remains the merge gate under `AGENTS.md`.
