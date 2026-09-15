# Source-first independent assessment comparison

Protocol: `CILE-ASSESSMENT-REFERENCE-1` + `CILE-ASSESSMENT-COMPARISON-1`.

This is the private F2→F3 assessment path under completion-first v5.1. It is not a validation, calibration-acceptance or human-approval mechanism.

## Ordering and privacy

1. Read the exact current candidate through the authenticated source-only `packet` operation. The packet must contain current full text and passes private source hash readback.
2. Produce an independent reference assessment without inspecting the current proposal. It must satisfy the same closed extraction schema and current completion-policy mandatory-field/framework checks and identify its actual assessor/model/prompt fingerprint.
3. Persist the reference through the authenticated immutable checkpoint path and read it back exactly. The reference identity binds candidate, current candidate input, exact source snapshot and request hash.
4. Only after reference readback may the comparison packet be created. It combines the persisted private reference with the current privacy-filtered proposal projection and its cryptographic projection revision. No original source text or private source/span ids are required in the comparison packet.
5. Persist a closed comparison result binding candidate input, source snapshot, proposal revision and reference digest. Re-read it and verify the comparison payload digest.

A changed candidate input, source snapshot, proposal revision or reference digest makes the old comparison non-current. Re-running synthesis is not a repair for a stale comparison.

## Comparison envelope

The persisted comparison records only controlled outcomes and disagreement paths: source fidelity (`pass|fail|partial|uncertain`), omissions (`none|nonmaterial|material|uncertain`), classification agreement (`agree|partial|disagree|uncertain`), field accuracy (`pass|fail|partial|uncertain`), plus mandatory/optional disagreement paths and the actual comparison assessor fingerprint. Reviewer prose is deliberately not part of the persisted comparison envelope.

## Completion semantics

A current comparison checkpoint with exact readback is evidence that F3 has been executed. It does **not** by itself establish F5 assessment completion. F4 bibliography/reference/citation readiness and all F5 predicates still apply, including current proposal/source/reference version guards and explicit mandatory-field accounting. `Validated/Accepted` remains a separate F6/F7 track.

The proposal revision used at F3 is the current privacy-filtered research projection revision. Before F5, the completion predicate must additionally establish that the current private proposal/source/reference state still corresponds to that revision; the F3 checkpoint must never be used to bypass a stale private proposal or source.

## Execution helper

`scripts/enrichment/assessment_comparison.py` implements the four bounded steps:

- `source-packet`
- `persist-reference`
- `comparison-packet`
- `persist-comparison`

Private packet/identity files are mode `0600`; source/reference bodies are never printed. The helper re-reads current source state immediately before reference persistence and re-reads the current proposal projection immediately before comparison persistence. All service calls remain commit-fenced and use the existing HMAC/nonce/replay boundary.
