# Hourly hybrid automation v4 — current operational contract

> **Superseded for KPI priority, work selection, WIP control and completion-convergence reporting by `docs/operations/completion-first-v5.md` (owner mandate, 15 September 2026).** The cadence, provider, identity-resolution, branch-recovery, anti-repeat and soft-close rules below remain in force unless v5 explicitly changes them.

Owner mandate: 15 September 2026. This document is the **current operational source of truth** for the two ChatGPT automation lanes. Where older wording in `automation.md`, `novelty-depth.md` or historical runbooks conflicts on cadence, provider order, work routing, identity-resolution state or runtime closeout, this document prevails. Scientific eligibility, rights, ontology and human acceptance rules are not superseded.

## Cadence and roles

- Lane A runs hourly at minute `:10` and is the normal paper-production worker.
- Lane B runs hourly at minute `:40` and is the only lane authorised for shared throughput/persistence/calibration engineering.
- Lane A owns the AM scouting window 08:00–20:00 Europe/Rome.
- Lane B owns the PM scouting window 20:00–08:00 Europe/Rome, labelled by opening date.
- There are exactly two project-wide scouting windows per day. Hourly activations are primarily enrichment/recovery activations, not hourly full scouting cycles.

## Provider order

Scheduled scouting uses **Parallel Search by default**. Exa is optional only when it is positively known to be available and materially improves recall or verification. A known exhausted Exa quota must not be probed on every window. Consensus and Scite are not scheduled-surveillance providers.

The W1–W7 coverage objectives, adaptive depth, query rotation, checkpoint/readback, v3 intake, retry/backoff and anti-saturation language remain governed. Historical Exa-primary/fallback-only wording is superseded for scheduled scouting.

## Work router

After one compact preflight and after resuming any unfinished safe write, choose exactly one primary mode.

Priority outside a due scouting window:

1. `PERSIST` — already verified work can be durably written now;
2. `ENRICH` — an owned CandidateRecord has an executable next stage and authorised persistence path;
3. `RESOLVE` — pending discovery-identity debt can be advanced under CILE-IDENTITY-RESOLUTION-2;
4. Lane B only: `ENGINEER` — a demonstrated shared blocker or mandatory gate prevents corpus progress;
5. `NOOP` — nothing safe and executable remains.

`SCOUT` pre-empts that order only when the lane's owned AM/PM scouting window is genuinely due and unsatisfied under the existing terminal/retry/backoff/idempotency rules.

### RESOLVE starvation guard

Paper-stage progress remains the primary KPI, so executable `ENRICH` normally precedes `RESOLVE`. Identity debt may not starve: if the oldest pending CILE-IDENTITY-RESOLUTION-2 observation is at least 24 hours old, or the pending queue reaches 20 observations, the next non-scout activation with no unfinished safe write must choose `RESOLVE` before opening new enrichment research.

## Persistence-first invariant

Before substantial research on a paper, positively establish the authorised writer/claim/dispatch path for its intended next stage. If the stage cannot be persisted in the current activation, do not build a read-only cohort. Record the precise blocker/recheck condition once and move to another executable stage or mode.

A paper counts as materially progressed only after the stage transition is durably written and read back. Search hits, source rereads, issue comments, timestamps, CI checks, unchanged validations and engineering PRs count as zero paper enrichment.

## Stateful identity resolution

New unresolved scouting observations use CILE-IDENTITY-RESOLUTION-2. The validator distinguishes `observation_key` from provider-independent `identity_key`, checks legal append-only transitions against prior persisted history, and verifies that any referenced CandidateRecord actually exists.

State path:

`pending → resolved`

or, for genuinely new work:

`pending → forwarded_to_intake → resolved/new_candidate`.

The `forwarded_to_intake` state is the explicit bridge to the normal governed v3 intake/recovery path. A resolution comment never creates a CandidateRecord. Conflicting terminals are invalid.

## Validated branch recovery

Candidate metadata/identity workflows may successfully validate and push an `automation/...` branch while repository policy blocks `gh pr create`. Such a branch is delivery debt, not a reason to rerun scientific/metadata work.

The workflow must persist a `<!-- cile-validated-branch-recovery:1 -->` ticket on #696 containing branch, exact head SHA, base and workflow run. At the start of each Lane-A/B activation, after any genuinely unfinished transactional write and before new research, inspect unresolved recovery tickets. If the exact branch/head is still ahead of main and no PR exists for it, create the PR through the authenticated GitHub connector. If it is already merged, superseded or has a PR, record/observe that state and do not duplicate it.

No validated branch may remain without a PR for more than one subsequent automation activation unless a concrete connector/policy blocker is recorded.

## Calibration failure clusters

Lane B must follow `docs/operations/calibration-trace-audit.md`. Once a failure cluster crosses its stop threshold, do not patch the next exception or rerun unchanged inference. Use the bounded private structural trace audit and require a reviewed class-level conclusion before a further production calibration activation.

## Soft runtime close

The hourly workers must remain recoverable and must not overlap by opening unbounded new work.

- Before roughly 20 minutes of active work, normal routing applies.
- At roughly 20 minutes, enter **soft-close**: do not open another paper cohort, new search family, new engineering branch or new external workflow. Finish/persist/read back work already in flight, or checkpoint the exact recoverable state.
- Do not poll long-running external workflows merely to fill the activation. Leave them pending with their run/branch identifier for the next activation.
- Safety, transactional completion and required terminalisation may exceed the soft-close threshold; the threshold never authorises abandoning an in-flight write.

## Anti-repeat rule

If an activation examines candidates but produces zero durable paper transitions, persist the common blocker key/prerequisite. The next activation must not repeat the same retrieval/selection/inference strategy unless that prerequisite changed. An unchanged whole-index scan, unchanged locator reread or unchanged model retry is not work.

## Operational SLOs

Evaluate the system over rolling 24–48 hour windows, not one activation:

- completed scheduled scouting windows: target ≥95%;
- candidate/intake orphan rate: 0%;
- conflicting identity-resolution terminals: 0;
- validated automation branch without PR for more than one following activation: 0;
- repeated unchanged blocker strategy: approximately 0;
- unresolved identity observations older than 24h: target <10% of pending queue;
- when safe actionable paper work exists, non-scout productive activations should normally produce at least one durable paper-stage transition;
- engineering changes are not throughput until subsequent real paper-stage transitions demonstrate the gain.

These are operational diagnostics, not scientific acceptance criteria and not quotas that justify unsafe work.

## Closeout

Report only the state needed to resume correctly: mode/reason; actionable paper pool; recovery-ticket state; pending identity debt; papers examined and durably advanced; exact `from→to` transitions with readback; final completions; scouting/RESOLVE outcomes when applicable; blocker groups; engineering/audit state separately; and the exact next recoverable action.

