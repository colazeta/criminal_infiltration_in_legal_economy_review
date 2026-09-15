# Calibration failure-cluster audit

Owner mandate: 15 September 2026. This contract prevents serial one-error-at-a-time engineering from replacing scientific corpus progress.

## Trigger

For one calibration case/extractor lineage, a grouped trace audit becomes mandatory when any of the following occurs:

- three consecutive engineering remediations are merged without a structurally valid persisted proposal;
- the same validator failure family recurs after a targeted remediation;
- a new failure appears downstream after each targeted patch, indicating an invariant mismatch across model output, synthesis and validation rather than an isolated defect.

The current CAND-002 chain through #711, #712 and #713 has reached this threshold. Issue #714 is the audit ledger.

## Stop rule

Allow the already-natural successor run that existed when the threshold was recognised to terminate. Do not cancel or duplicate it. If that successor fails before a structurally valid proposal is persisted, do not automatically patch the next individual exception. Freeze the immutable terminal and route Lane B to a grouped audit.

## Required audit packet

The audit compares the failure cluster without exposing private source content. Record:

1. code, extractor, prompt, request and source/document fingerprints;
2. chunk count and reused/new checkpoint counts;
3. structural atom counts by entity and field;
4. synthesis input/output structural summaries;
5. exact validator stage and failure code;
6. whether the invalid relation originates in model output, chunk promotion/normalisation, synthesis, or cross-stage mismatch;
7. each prior remediation and the invariant it was intended to enforce;
8. repeated versus genuinely new failure subtypes;
9. regression cases covering every observed subtype;
10. one bounded remediation proposal for the failure class, or a documented conclusion that the synthesis representation should change before continuing heterogeneous calibration.

## Acceptance

A post-audit engineering change must preserve fail-closed scientific validation, private evidence boundaries, source-first reference comparison and fingerprinting. It may not weaken a validator merely to obtain a proposal. Engineering is not counted as paper enrichment. The failure cluster is considered operationally resolved only when a natural successor produces a structurally valid persisted proposal and that proposal proceeds to the existing independent comparison gate.
