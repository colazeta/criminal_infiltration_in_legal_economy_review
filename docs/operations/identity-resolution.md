# Durable discovery identity resolution

Owner mandate: 15 September 2026. Current protocol: **CILE-IDENTITY-RESOLUTION-2**. The earlier v1 renderer remains readable for historical records but must not be used for new unresolved-identity writes.

This contract closes the gap between completed scouting and later candidate handling. It is bibliographic/operational only. It does not decide scientific eligibility, canonical ScholarlyWork identity, source rights, framework class or publication acceptance.

## Two keys, two purposes

Each retrieved occurrence has an `observation_key`, derived from provider + DOI + normalised title + year + URL. It identifies the concrete observation/manifestation and is the append-only state-machine key.

Each record also has an `identity_key`, derived independently of provider and URL: DOI when present; otherwise normalised title/year and authors when available. This is a conservative bibliographic grouping aid, not a canonical-work decision. Different observations may therefore share one `identity_key` while retaining distinct `observation_key` values.

## RESOLVE mode and state machine

The hourly hybrid router contains `RESOLVE` alongside `SCOUT`, `PERSIST`, `ENRICH`, Lane-B `ENGINEER`, and `NOOP`.

A newly unresolved scouting observation must first be persisted as:

- `pending` — identity could not be safely closed during the scouting window.

A pending observation may then become:

- `forwarded_to_intake` — candidate-bound verification supports forwarding as a distinct plausible scholarly work, but the normal governed v3 intake has not yet materialised a CandidateRecord; or
- `resolved` with exactly one terminal outcome:
  - `known_exact_work` — reconciled to an existing CandidateRecord;
  - `known_work_new_manifestation` — a new version/repository/publisher manifestation of an existing CandidateRecord;
  - `new_candidate` — only after the normal v3 intake/recovery path has materialised the referenced CandidateRecord;
  - `not_forwarded` — the observation should not enter CandidateRecord intake under the operational standard, with a reason.

`forwarded_to_intake` may terminate only as `new_candidate`. A resolved observation is immutable. Conflicting later terminals are invalid. Ambiguity remains pending rather than being guessed.

## Stateful validation

Use:

```bash
python3 -m scripts.identity_resolution_v2 input.json \
  --history prior-records.json \
  --output comments.json
```

`prior-records.json` is the ordered array of already persisted CILE-IDENTITY-RESOLUTION-2 canonical records for the relevant observations, reconstructed from issue #696 and read back before a new append. The validator reduces the history and rejects illegal or conflicting transitions.

For outcomes that reference a CandidateRecord, the validator also checks the current `data/curation/review_queue.csv`; a syntactically valid but absent CandidateRecord id is rejected. This makes CandidateRecord existence a machine-enforced invariant rather than a prompt-only convention.

The rendered comments use marker `<!-- cile-identity-resolution:2 -->` and contain bibliographic metadata only. Never include abstracts, full text, evidence quotations, reviewer identity, private working notes or credentials.

## Work selection and intake handoff

At the end of every completed scouting window, persist every observation still counted as `unresolved_identity` as `pending` before closeout and read it back. On later activations, process the oldest feasible pending observations in bounded groups.

When candidate-bound verification establishes a distinct plausible scholarly work, record `forwarded_to_intake` and route it through the **normal governed v3 intake/recovery path**. Do not create a CandidateRecord by writing a resolution comment. Once the CandidateRecord is materialised, append `resolved/new_candidate` referencing that real id.

Do not repeatedly rerun the generic scouting query to resolve an identity. Use only candidate-bound verification needed to reach one of the operational states above.

## Fairness and starvation guard

Paper-stage throughput remains the primary operational KPI. Therefore, outside a due scouting window, prefer `PERSIST` and executable `ENRICH` work over `RESOLVE` when both are immediately available. However unresolved debt must not starve: if the oldest pending observation is at least 24 hours old, or the pending queue reaches 20 observations, the next non-scout activation with no unfinished safe write must route to `RESOLVE` before opening more enrichment research.

## Reporting

Report separately:

- unresolved observations created by scouting;
- pending observations examined in `RESOLVE`;
- `forwarded_to_intake` handoffs;
- terminal outcomes by type;
- observations still pending and their concrete blocker;
- new CandidateRecords actually materialised through normal intake;
- paper-stage transitions produced elsewhere.

Resolution comments themselves do not count as paper enrichment unless a CandidateRecord stage transition is durably persisted and read back.
