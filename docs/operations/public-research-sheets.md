# Public paper research context

**Current delivery amendment (14 September 2026):** see [two-lane-delivery.md](two-lane-delivery.md). It supersedes the earlier proposal-only UI limitation, defines the current receipt-backed index/filter/statistics, private PDF and bibliography paths, explicit assessed-field policy, and daily discovery with durable query checkpoints. Historical observations below remain historical; no scientific acceptance is implied.

Owner instruction and issue #597, 13 September 2026. This extends the public
paper **display**, not scientific eligibility, canonical identity or acceptance
of model-generated extraction. The original 1990s dialog, double-click and
accessible open button remain the entry points.

## One source, a separate public boundary

The current candidate-bound immutable extraction in the existing private
SQLite/KV enrichment store is the source. No second database, publication ledger
or scheduler is introduced. `curator-app/src/public-paper-research.js` derives
`schema/public-paper-research.schema.json`; the physical/semantic mapping is
`ontology/modules/public-paper-research.json`.

`GET /api/public-paper-research?id=<CandidateRecord ID>` is a **new public
projection endpoint**, not public access to `/api/paper-enrichment/*`. The latter
and the machine service remain authenticated. The new endpoint accepts only one
bounded candidate ID, uses parameterised read-only queries and forwards no
cookies or credentials. The browser uses no-store/omit credentials and checks the
candidate ID, title, normalised DOI and source-link snapshot against the open
sheet. A late response cannot overwrite another sheet.

Before projection the service checks the current candidate input hash, immutable
proposal hash, exact privately retained source hashes, source/span coverage and
all existing extraction/hierarchy constraints. Only the current input is served.
An older proposal is not silently substituted. Current proposals are ordered by
the recorded creation timestamp, then immutable proposal ID. No history is
rewritten. A revision digest covers the actual public values, not a paper count.

## Content and interpretation

The sheet shows research question, contribution, summary, conceptual definition
and operational identification of infiltration; each recorded study, dataset,
analysis, analysis-specific variable use and linked finding; uncertainty and null
results as recorded; authors' limitations; source URLs/locators, consultation
coverage, protocol/codebook and the recorded update date. Multiple studies remain
separate. Comparisons, causal identification and validation are not inferred
from model names or keywords. Facts retain source/analyst origin and missingness.

The six original classes and grounded primary, secondary and alternative coding
are retained exactly. `insufficient_evidence` and `outside_framework` are distinct
abstentions, not seventh/eighth categories. The private schema only establishes
proposals, so the public assessment is always `unreviewed_proposal`. It cannot
invent a confirmed classification or accept the calibration benchmark. When model
provenance exists the UI explicitly says **automated preliminary extraction,
not scientifically validated**; otherwise production mode is unspecified, not
assumed to be human review. This authorisation allows proposed research context
to be displayed as such; it does not enable automated scientific extraction.

The public availability values are display states only:

- `available`: a current proposal passed structural, identity, source-integrity
  and publication-boundary checks; this is not a correctness assessment.
- `not_assessed`: no stored extraction for the indexed candidate.
- `stale`: only extraction of an older candidate snapshot is available.
- `not_registered`: no active target in the current analytical index; this does
  not remove the paper from the independent bibliographic register.
- `withheld`: stored material cannot safely pass the projection checks.

A transport failure remains an explicit temporary failure, not an absent
analysis. `not_reported` remains limited to the material actually consulted,
particularly when only an abstract or partial text was read.

## Exclusions and limits

No raw proposal object, private target/proposal/source ID, storage key, source
body, offset, reviewer identity, generated-by object, original quotation or
internal `analyst_limitations` working note is exposed. The public framework
rationale is a source-linked analyst paraphrase, not the private notes field.
Response-local study/evidence identifiers preserve relationships without exposing
private identifiers. Credentialled, signed, non-HTTPS and private-service URLs
are rejected. Long verbatim source sequences (25 consecutive normalised words),
obvious credentials, and private identifiers in text withhold the projection.
These are conservative publication safeguards, not a substitute for scientific
review or a guarantee that every paraphrase is correct.

The bounded public response permits at most 20 consulted sources, 8 million
source characters and 750,000 projected characters per paper. Exceeding a limit
withholds the record explicitly, rather than truncating scientific content.
Future reference-checked human confirmation requires a separately governed source
of that decision; there is no such decision in the current proposal schema.

## Delivery and verification

A context update changes the same sheet on its next opening; it needs neither a
new discovery nor another Pages build. Existing Pages release verification also
checks the exact `paper-sheet-research.js` asset. The existing Worker deployment
and hour-40 observer run `scripts/enrichment/public_research_check.py` using the
existing HMAC service secret inside its existing environment. The signed
`public-research-audit` operation returns **only public candidate IDs, projection
states, public-content digests and aggregate counts**, never private proposal or
source bodies. It performs no source retrieval, model inference, activation,
scientific approval, or mutation of research records.

The verifier compares every populated/withheld/stale projection with an
unauthenticated HTTP read and the public register; it additionally samples up to
five not-assessed candidates. Its receipt states both denominators, source
counts, visible class assignments and any mismatches. Counts of missing material
are not recoded as successful research. Concurrent genuine content changes make a
verification fail rather than silently accepting a stale snapshot.

Unit tests include source integrity, unsupported coverage, private-field and
URL exclusion, all six classes and abstentions, multiple studies, analysis-local
variables/findings, null effects, same-count content revisions, stale identity,
failed and delayed requests, and the unchanged private authentication boundary.
Unit fixtures are synthetic and remain software tests, not calibration evidence.
