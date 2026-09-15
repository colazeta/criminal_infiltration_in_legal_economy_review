# Completion-first automation v5 — current operational contract

Owner mandate: 15 September 2026. This document supersedes `hourly-hybrid-v4.md` only for work selection, KPI priority, WIP control and completion-convergence reporting. Cadence, provider order, identity-resolution semantics, source/rights/privacy rules, ontology, transactional claims/fencing and human scientific acceptance remain unchanged unless explicitly stated here.

## Objective

The primary objective is no longer the number of durable intermediate stage transitions. It is **convergence toward scientifically completed papers** under CILE-COMPLETION-POLICY-2.

A durable transition is still required evidence of real progress, but it is a secondary operational metric. The primary questions are:

1. how many papers moved one or more completion gates closer to `completed=true`;
2. how many papers reached the deepest currently attainable gate;
3. how many cases entered or advanced the heterogeneous calibration cohort;
4. how many papers became ready for the next independent scientific or human gate;
5. how many final completion receipts were accepted.

Engineering, search, CI, comments and intermediate persistence remain zero completion progress unless they enable a paper to cross a completion gate.

## Completion frontier

Every non-scout activation must build a compact completion-frontier snapshot from persisted state. The labels below are operational routing labels only; they do not replace scientific states, receipts or ontology concepts.

- `F0_METADATA_SOURCE` — metadata/source identity still blocks full-text work.
- `F1_FULLTEXT_READY` — governed full text/source is retained and hash/readback verified.
- `F2_PROPOSAL_PERSISTED` — a structurally valid private proposal is persisted and read back, but not independently accepted.
- `F3_INDEPENDENT_COMPARISON` — source-first independent/reference comparison has been completed and persisted for the current proposal.
- `F4_REFERENCES_READY` — governed outgoing bibliography and dated citation/reference snapshot required by the completion contract are ready for the current candidate/proposal.
- `F5_CALIBRATION_EVIDENCE` — the case is reference-checked and usable as evidence in the heterogeneous calibration set, or the exact accepted global calibration receipt is already available for its extractor.
- `F6_REVIEW_READY` — all machine-verifiable prerequisites for the paper-specific exact-head human completion review packet are satisfied.
- `F7_COMPLETED` — the current immutable completion/adjudication receipt is accepted and still valid for the current candidate/proposal/public revision.

Report the first unmet gate and the deepest reached gate for active papers. A transition that does not reduce the remaining completion distance is not a primary success.

## Global P0: heterogeneous calibration

The completion contract requires an accepted heterogeneous calibration receipt before ordinary paper completion can occur. Therefore calibration is a **global P0 bottleneck** until satisfied.

Maintain a visible counter:

`reference-checked calibration cases / 12 minimum (18 maximum)`

The cohort must remain heterogeneous and comply with `enrichment-adjudication.md`: include full-text and hard cases, varied designs and source conditions, and explicit assessment of source fidelity, omissions, classification agreement, field accuracy and cost/call limits. Synthetic fixtures do not count.

`CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-002` is the current deepest case because its proposal is persisted/read back. It should be advanced through source-first independent comparison and, if valid, become a real calibration case. It is not counted as calibrated merely because proposal persistence succeeded.

Until the minimum calibration set is reached, work that advances eligible calibration cases outranks broad ordinary enrichment unless a nearly review-ready paper can be closed sooner without bypassing calibration.

## WIP limit and pull discipline

Avoid a large inventory of partially processed papers.

- Keep at most **6 ordinary completion-frontier papers project-wide** in active end-to-end WIP at once.
- The 12–18 calibration cases are a separate governed cohort, but process them in small homogeneous micro-batches; do not create 12–18 simultaneous inference jobs.
- Do not pull a new ordinary paper into active WIP while an existing active paper has a safe executable next completion gate.
- Prefer the paper with the deepest reached gate and the fewest remaining gates, subject to ownership, claim and scientific-safety constraints.
- A blocked paper may be parked only with an exact blocker and recheck condition; parking frees an ordinary WIP slot.

## Lane routing

A due owned scouting window still selects `SCOUT`. Outside scouting, resume unfinished safe writes first.

### Lane A (:10)

Lane A is the completion-production lane. Route in this order:

1. `PERSIST` — finish/read back an in-flight completion-gate write;
2. `COMPLETE` — advance the deepest owned ordinary WIP paper to its next completion gate;
3. `CALIBRATION_CASE` — advance an owned selected calibration case when executable;
4. `RESOLVE` — required identity debt under the existing starvation guard;
5. `NOOP` — only when no safe executable completion work exists.

Lane A must not build new read-only cohorts. If no authorised writer/claim exists for the deepest owned frontier paper, record the blocker once and do not re-research it.

### Lane B (:40)

Lane B owns shared engineering but is also completion-first. Route in this order:

1. `PERSIST` — finish/read back an in-flight completion-gate write;
2. `COMPLETE` — advance the deepest owned paper, especially current calibration/frontier cases;
3. `CALIBRATION_CASE` — build/advance the heterogeneous 12–18 case calibration set;
4. `RESOLVE` — required identity debt under the existing starvation guard;
5. `ENGINEER` — only a demonstrated shared blocker preventing the next completion gate;
6. `NOOP`.

For CAND-002, the next intended gate after `proposal_persisted_readback_verified` is the governed source-first independent comparison, not another synthesis run.

## Engineering proof rule

An engineering PR is not considered operationally successful merely because it is merged or CI is green.

A shared engineering change must, within the **next two eligible automation activations**, enable at least one real paper to reduce completion distance by crossing a completion gate. If it does not, record it as unproven engineering debt and do not continue engineering the same class without new trace evidence.

If Lane A reports no actionable authorised writer/claim for ordinary completion work in two consecutive eligible activations, Lane B must treat the missing generic governed writer/claim path as a shared throughput blocker before opening unrelated optimisation work.

## Calibration cohort selection

Select cases deliberately for heterogeneity and completion feasibility, not by arbitrary queue order. Keep a persisted roster with at least:

- candidate id;
- current frontier gate;
- design/study-type diversity tag;
- full-text availability;
- hard/negative/missingness characteristic when applicable;
- current independent-comparison status;
- reason selected;
- exact blocker/next action.

No case enters the calibration numerator until its independent reference check is actually complete and persisted.

## Anti-repeat and no false progress

Do not count as completion convergence:

- metadata/source rereads without a gate transition;
- issue comments or evidence packets that do not change the completion frontier;
- proposal regeneration when the current proposal is already valid/persisted;
- repeated CI/deploy verification without relevant state change;
- engineering PRs with no subsequent paper effect;
- moving between intermediate labels that leaves the same first unmet completion gate.

The previous v4 anti-repeat, soft-close, identity-resolution and validated-branch-recovery rules remain in force.

## Completion SLOs

Evaluate over rolling activations and 24–48 hour windows:

- `Completed`: must eventually rise above 0; zero is expected only while a mandatory global gate such as calibration is genuinely unsatisfied.
- Calibration progress: the reference-checked numerator should rise materially toward `12 minimum`; a flat numerator across 6–10 eligible activations is a system failure requiring diagnosis.
- Independent comparison: once proposals are persisted, at least one selected case should cross into `F3_INDEPENDENT_COMPARISON` within the next few eligible activations or the comparison path is the blocker.
- Ordinary WIP: active ordinary frontier papers ≤6.
- Zero-convergence activation rate: activations with no reduced paper completion distance should trend toward zero whenever safe executable work exists.
- Engineering proof: every shared engineering change must demonstrate a downstream completion-gate transition within two eligible activations.

These SLOs never override scientific, rights, privacy or human-acceptance gates.

## Closeout

Every activation reports, compactly:

- mode and reason;
- `Completed / registered`;
- calibration counter `x / 12 minimum`;
- count of active ordinary WIP papers (max 6);
- deepest gate reached by each active paper and its first unmet gate;
- papers whose completion distance decreased this activation;
- independent-comparison transitions;
- calibration cases newly reference-checked;
- papers newly review-ready;
- final completions;
- exact blockers and recheck conditions;
- engineering separately, including whether its two-activation proof obligation is satisfied;
- exact next action that most directly reduces distance to completion.
