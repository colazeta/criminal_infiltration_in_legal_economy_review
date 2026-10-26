# Completion-first automation v5.1 — current operational contract

Owner mandate: 15 September 2026. This document supersedes `hourly-hybrid-v4.md` only for work selection, KPI priority, WIP control and completion-convergence reporting. Cadence, provider order, identity-resolution semantics, source/rights/privacy rules, ontology, transactional claims/fencing and human scientific acceptance remain unchanged unless explicitly stated here.

## Terminology amendment: Completed means assessment complete

For operational routing, reporting, archive statistics and the intended public `Completed` concept, **Completed means that the paper has a complete current assessment**. It does **not** mean that the owner/human curator has validated or accepted that assessment.

Human validation is a separate state and must be reported separately as `Validated` / `Accepted`. A paper may therefore be `Completed=yes` and `Validated=no`.

The existing exact-head human approval, heterogeneous calibration receipt and adjudication receipt remain required for scientific validation/acceptance where the governance contract requires them. They no longer block the operational `Completed` count for a complete assessment.

### Assessment-complete predicate

A paper is `ASSESSMENT_COMPLETE` only when the current candidate/version has, with durable readback:

1. governed full-text/source evidence retained and integrity-checked;
2. a current structurally valid structured assessment/proposal persisted and read back;
3. every mandatory assessment field explicitly accounted for: reported, source-grounded `not_reported`, or `not_applicable`; mandatory `ambiguous` or `not_verifiable` remains incomplete;
4. a grounded framework assessment recorded as a proposal or grounded `outside_framework`; this is not human acceptance;
5. source-first independent/reference comparison completed and persisted for the current assessment;
6. the paper bibliography explicitly assessed (`source_complete` or governed `not_reported`) and a dated incoming/outgoing reference/citation snapshot persisted;
7. authors' limitations and required caveats represented; and
8. current candidate/proposal/source/reference hashes and version guards still match.

`ASSESSMENT_COMPLETE` is a completeness state, not a correctness or acceptance claim. It may remain `unreviewed_proposal` scientifically.

Calibration acceptance, human exact-head approval and adjudication receipts belong to the separate **validation track**. They may turn a completed assessment into a validated/accepted assessment, but they do not define whether the assessment itself is complete.

## Objective

The primary objective is **convergence toward complete paper assessments**.

A durable transition remains required evidence of real progress, but it is secondary. The primary questions are:

1. how many papers reduced their distance to `ASSESSMENT_COMPLETE`;
2. how many became assessment-complete this activation;
3. how many completed assessments remain unvalidated versus validated;
4. how many papers reached the deepest currently attainable assessment gate; and
5. separately, how the 12–18 case calibration/validation programme is progressing.

Engineering, search, CI, comments and intermediate persistence are zero assessment-completion progress unless they enable a paper to cross an assessment gate.

## Assessment-completion frontier

Every non-scout activation builds a compact frontier snapshot. These labels are operational routing labels only and do not replace ontology/scientific states.

- `F0_METADATA_SOURCE` — metadata/source identity still blocks full-text assessment.
- `F1_FULLTEXT_READY` — governed full text/source is retained and hash/readback verified.
- `F2_PROPOSAL_PERSISTED` — a structurally valid private assessment/proposal is persisted and read back.
- `F3_INDEPENDENT_COMPARISON` — source-first independent/reference comparison has been completed and persisted for the current assessment.
- `F4_REFERENCES_READY` — governed paper bibliography and dated incoming/outgoing reference/citation snapshot are ready for the current candidate/assessment.
- `F5_ASSESSMENT_COMPLETE` — all assessment-complete predicate requirements above are satisfied. **This is `Completed`. No human approval is required for this gate.**
- `F6_VALIDATION_READY` — the completed assessment has all machine-verifiable prerequisites for the separate calibration/human validation path.
- `F7_VALIDATED` — the current assessment has the required accepted calibration/adjudication/human exact-head approval and remains current.

Report the first unmet assessment gate and deepest reached gate. A transition that does not reduce distance to `F5_ASSESSMENT_COMPLETE` is not a primary success.

## Validation track: heterogeneous calibration

The 12–18 paper heterogeneous calibration remains a high-priority quality/validation programme, but it is **not a prerequisite for counting a paper as assessment-complete**.

Maintain a visible, separate counter:

`reference-checked calibration cases / 12 minimum (18 maximum)`

The cohort remains governed by `enrichment-adjudication.md`: full-text and hard cases, varied designs/source conditions, source fidelity, omissions, classification agreement, field accuracy and cost/call limits. Synthetic fixtures do not count.

`CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-002` remains the current deepest case because its proposal is persisted/read back. Its next assessment-completion gate is source-first independent comparison. It must not be sent back through unchanged synthesis merely to create activity.

Assessment-completion work outranks validation-only work when an active paper can safely cross a missing F0–F5 gate. Calibration work runs in parallel to make completed assessments scientifically validated, not to hold the Completed numerator at zero.

## WIP limit and pull discipline

- Keep at most **6 ordinary assessment-completion papers project-wide** in active end-to-end WIP at once.
- Calibration cases are a separate governed cohort, processed in small micro-batches.
- Do not pull a new ordinary paper while an active paper has a safe executable next assessment-completion gate.
- Prefer the deepest paper with the fewest remaining F0–F5 gates, subject to ownership, claims and safety.
- A blocked paper may be parked only with an exact blocker and recheck condition; parking frees a WIP slot.

## Lane routing

A due owned scouting window still selects `SCOUT`. Outside scouting, resume unfinished safe writes first.

### Lane A (:10)

1. `PERSIST` — finish/read back an in-flight assessment-gate write;
2. `COMPLETE` — advance the deepest owned WIP paper toward F5;
3. `CALIBRATION_CASE` — advance a selected owned validation/calibration case when it does not displace executable assessment-completion work;
4. `RESOLVE` — required identity debt under the existing starvation guard;
5. `NOOP` — only when no safe executable assessment-completion work exists.

Lane A must not build read-only cohorts. If no authorised writer/claim exists for the deepest owned frontier paper, record the blocker once and do not re-research it.

### Lane B (:40)

1. `PERSIST` — finish/read back an in-flight assessment-gate write;
2. `COMPLETE` — advance the deepest owned paper toward F5;
3. `CALIBRATION_CASE` — advance heterogeneous validation evidence;
4. `RESOLVE` — required identity debt;
5. `ENGINEER` — only a demonstrated shared blocker preventing the next F0–F5 assessment gate or the validation track;
6. `NOOP`.

For CAND-002, the next intended gate after `proposal_persisted_readback_verified` is the governed source-first independent comparison, not another synthesis run.

## Engineering proof rule

An engineering PR is not operationally successful merely because it merges or CI is green.

A shared engineering change must, within the **next two eligible activations**, enable at least one real paper to cross a deeper **assessment-completion** gate. If it does not, record it as unproven engineering debt and do not continue the same engineering class without new trace evidence.

If Lane A reports no actionable authorised writer/claim for ordinary assessment-completion work in two consecutive eligible activations, Lane B must treat the missing generic governed writer/claim path as a shared blocker before unrelated optimisation work.

## Calibration cohort selection

Select calibration cases deliberately for heterogeneity and feasibility. Keep a persisted roster with candidate id, frontier gate, design/study-type diversity, full-text availability, hard/negative/missingness characteristic, independent-comparison status, selection reason and exact next action.

A case enters the calibration numerator only after its independent reference check is complete and persisted. This counter is separate from `Completed`.

## Anti-repeat and no false progress

Do not count as progress toward Completed:

- metadata/source rereads without an assessment-gate transition;
- issue comments/evidence packets that do not change the F0–F5 frontier;
- proposal regeneration when the current proposal is already valid/persisted;
- repeated CI/deploy verification without relevant state change;
- engineering PRs with no subsequent paper effect;
- calibration/human-approval work on an already completed assessment when reporting assessment-completion throughput; or
- moving between labels while the first unmet F0–F5 gate is unchanged.

The previous v4 anti-repeat, soft-close, identity-resolution and validated-branch-recovery rules remain in force.

## SLOs

Evaluate over rolling activations and 24–48 hour windows:

- `Completed assessments`: must rise as papers satisfy F5; human approval is not required for this numerator.
- Independent comparison: once proposals are persisted, selected papers should cross F2→F3 within the next few eligible activations or that path is the blocker.
- References: papers at F3 should move to F4 without opening unrelated cohorts.
- Ordinary WIP: active F0–F4 ordinary papers ≤6.
- Zero-convergence activation rate should trend toward zero whenever safe executable assessment work exists.
- Engineering proof: each shared engineering change must demonstrate a downstream F0–F5 transition within two eligible activations.
- Validation/calibration progress is reported separately; a flat calibration numerator is a validation-track failure, not a reason to report completed assessments as zero.

These SLOs never weaken scientific, rights, privacy or human-acceptance gates.

## Closeout

Every activation reports compactly:

- mode and reason;
- `Assessment Completed / registered` — this is the primary Completed KPI;
- `Validated / Assessment Completed` — separate human/scientific acceptance KPI;
- calibration counter `x / 12 minimum`;
- active ordinary WIP count (max 6);
- deepest assessment gate and first unmet F0–F5 gate for active papers;
- papers whose distance to assessment completion decreased;
- independent-comparison transitions;
- papers reaching F4 references-ready;
- papers newly reaching `F5_ASSESSMENT_COMPLETE`;
- validation/calibration transitions separately;
- exact blockers/recheck conditions;
- engineering separately with its two-activation proof obligation; and
- exact next action most directly reducing distance to complete assessment.

