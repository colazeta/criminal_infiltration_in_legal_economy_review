# Paper enrichment implementation verification — 11 September 2026

This receipt distinguishes observed software checks, live provider access and production readiness. It does not record a research iteration or scientific calibration.

## Implemented release

Protocol `CILE-ENRICH-1`; ontology profile `0.4.0`; clinical contribution codebook `1.0.0`.
The implementation adds fifteen empty private SQL tables, a closed and ontologically mapped extraction envelope, a persistent hourly work queue, source integrity checks, immutable proposals, directed citation observations and a curator-only interface. No candidate, canonical work, eligibility decision or publication entry is added or changed by this release.

## Observed tests

GitHub Actions run `34598826634`, job `103260878536`, completed successfully on 11 September 2026 at 12:25 UTC. The action verified SHA-256 `af9f928f5734a1fc2126f8d709a7e9d8deb833b74312d6826a2e9cc7ed823fa0` for the source-only implementation patch before applying it, ran validation, and committed the validated source as `c21c4bfa03e99951e06c2440bb718cc63117a8a0`.

Observed results:

- 398 Python tests passed.
- 114 JavaScript tests passed, including 29 new enrichment tests.
- Repository, ontology, public archive and static-site validators passed.
- Model-browser generation produced 48 entity definitions and no corpus data.
- The checked register contained 174 candidates and zero canonical works in the active review cycle. These are different populations, not conflicting counts.
- The saturation check reported zero recorded cycles and `NOT SATURATED`; this is not a finding of literature coverage.

The tests include replay protection, input versioning, concurrent-run exclusion, lease recovery, retry exhaustion, source readback and tampering, identity conflicts, pagination checkpoints, missingness, source-backed proposals, study/analysis scope and private authentication boundaries. Synthetic test fixtures demonstrate software behaviour, not the scientific accuracy of extraction.

## Observed live-provider access

The same action ran `scripts/enrichment/provider_smoke.py` against two existing registered candidates. Only transient provider responses were inspected; zero source texts were persisted and no database or register was modified.

| Candidate | Crossref | OpenAlex |
| --- | --- | --- |
| `CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-001` | DOI/title matched; abstract returned | DOI/title matched; 29 outgoing identifiers returned |
| `CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-006` | DOI/title matched; abstract returned | DOI/title matched; 42 outgoing identifiers returned |

These observations establish connectivity and identity agreement for these requests only. They do not establish full-text access, incoming-citation completeness, whole-corpus coverage or production Worker connectivity.

## Actual production blocker

The separate production-environment preflight, run `34596980260`, job `103254908996`, at 12:03 UTC reached account discovery and then failed on the D1 inventory request with HTTP 401. The credential was never displayed. D1 authorisation/account scope must be verified. R2 and queue access were not established by that failed request.

The optional account variable being blank was not the observed cause: unique-account discovery had already succeeded. No production enrichment migration, authenticated source readback or scheduled enrichment run has been verified by this receipt.

## Remaining activation work

`PAPER_ENRICHMENT_ENABLED` remains `false`. Restoring private D1/R2 access, applying the additive migration, verifying authenticated storage and checking the deployed scheduler are prerequisites for mechanical metadata/citation execution.

Scientific extraction and framework classification remain `blocked/model_calibration_required`. A validated source/proposal import path is implemented, but an automatic model executor is not connected. Selecting and connecting that executor, specifying cost/call limits, and testing it against independently checked extractions from 12–18 real heterogeneous papers are still required. No gold-standard labels or model-accuracy claims have been invented.

A successful build or deployment must not be described as an active hourly scientific task. See `paper-enrichment.md` and `../methodology/paper-extraction.md` for the operational and methodological contracts.
