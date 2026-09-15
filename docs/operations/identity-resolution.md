# Durable discovery identity resolution

Owner mandate: 15 September 2026. This contract closes the gap between a completed scouting query and later candidate handling. It does not change scientific eligibility, canonical-work identity, source rights or curator acceptance.

## Why this exists

A completed scouting window may end with retrieved scholarly-looking identities that cannot be conservatively classified as known, a manifestation of a known work, a new CandidateRecord, or not-forwarded during the bounded search run. Those identities must not disappear into aggregate telemetry. They enter a durable resolution queue and must later receive an explicit operational terminal outcome.

## RESOLVE mode

The hourly hybrid router includes `RESOLVE` in addition to `SCOUT`, `PERSIST`, `ENRICH`, Lane-B `ENGINEER`, and `NOOP`.

`RESOLVE` is selected when unresolved discovery identities exist and the lane is not required to execute its owned scouting window or a higher-priority safe persistence transition. It is not scientific screening. Its purpose is bibliographic identity closure.

Use `python3 -m scripts.identity_resolution <input.json> --output <comments.json>` to validate and render `CILE-IDENTITY-RESOLUTION-1` comments. Append validated comments to the existing operational checkpoint thread #696 and read them back. This is an owner-authorised narrow extension of the #696 non-decisional write boundary.

The protocol permits bibliographic metadata only: title, HTTPS URL, DOI when observed, year, provider/query identifiers, operational status/outcome, CandidateRecord id where already governed, and a short non-private rationale. Do not include abstracts, full text, evidence quotations, reviewer identity, internal notes or credentials.

## State machine

Each identity has a stable `identity_key` derived from provider + DOI + title + year + URL.

An identity first appears as:

- `pending`: identity could not be safely closed during the scouting window.

It must eventually receive exactly one current terminal interpretation in a later append-only comment:

- `known_exact_work`: reconciled to an existing CandidateRecord;
- `known_work_new_manifestation`: a new version/repository/publisher manifestation of an existing CandidateRecord;
- `new_candidate`: the normal governed intake path has already created the referenced CandidateRecord;
- `not_forwarded`: the retrieved result should not become a CandidateRecord under the operational intake standard, with the reason recorded.

A `new_candidate` terminal does not itself create the CandidateRecord and cannot bypass v3 intake. A known-work terminal does not make a canonical ScholarlyWork decision. If ambiguity remains, the identity stays pending rather than being guessed.

## Work selection

At the end of every completed scouting window, persist every identity still counted as `unresolved_identity` into this queue before closeout. On later activations, process pending identities in bounded groups. Do not repeatedly run the same generic query; use candidate-bound verification sufficient to reach one terminal state.

Unresolved identities are operational debt. A lane must not indefinitely accumulate new unresolved identities while an older pending queue can be safely resolved. Prefer the oldest feasible pending identities and report the number entering and leaving the queue.

## Reporting

Report separately:

- unresolved identities created by the scouting window;
- pending identities examined in `RESOLVE`;
- terminals by outcome;
- identities still pending and their concrete blocker;
- new CandidateRecords actually materialised through the normal intake path.

Do not count a resolution comment itself as a durable paper-stage transition unless it causes an authorised CandidateRecord persistence step elsewhere. Resolution throughput and paper-enrichment throughput remain separate metrics.
