# Two-lane delivery and recovery

Owner implementation mandate: 14 September 2026; persistence-first/identity-resolution v4 amendment: 15 September 2026; completion-first v5 amendment: 15 September 2026. `docs/operations/completion-first-v5.md` is the current operational source of truth for KPI priority, work selection, WIP control and completion-convergence reporting. `docs/operations/hourly-hybrid-v4.md` remains authoritative for cadence, provider order, identity-resolution, branch-recovery, anti-repeat and runtime closeout where v5 does not explicitly supersede it. This file records the delivery architecture and scientific boundaries.

## Hourly hybrid lanes and scouting windows

The existing automation is a two-lane hourly system. **Lane A runs at :10 and Lane B at :40.** Both lanes are enrichment/recovery workers by default; scouting is a bounded mode inside them, not another scheduler. Lane A owns 08:00–20:00 Europe/Rome; Lane B owns 20:00–08:00. There are **exactly two project-wide scouting windows per day**.

Keep the existing `CILE-HOUR40-1` private enrichment service, namespace, catch-up semantics, fencing and immutable attempts. The conversational workers route through existing governed persistence paths; they do not create a second private scheduler.

Candidate ownership remains stable by `hashlib.sha256(candidate_id.encode("utf-8")).digest()[0] % 2`, Lane A = 0, Lane B = 1. Hash assignment and timestamps are not locks. Actual transactional claims, leases, fencing and version guards remain authoritative.

For scheduled scouting, **Parallel Search is the default discovery provider**. Exa is optional only when positively available and materially useful. Consensus and Scite are excluded from scheduled surveillance. W1–W7/adaptive depth are governed by `novelty-depth.md`.

## Current work router

A due owned scouting window selects `SCOUT`. Otherwise, after resuming any unfinished safe write, use the completion-first v5 router. The retained v4 concepts remain:

1. `PERSIST` — verified work can be durably written now;
2. `ENRICH`/`COMPLETE` — an owned CandidateRecord has an executable next completion gate and real persistence path;
3. `CALIBRATION_CASE` — an owned selected heterogeneous calibration case can advance;
4. `RESOLVE` — pending CILE-IDENTITY-RESOLUTION-2 debt can be advanced;
5. Lane B only: `ENGINEER` — a demonstrated shared blocker or mandatory gate prevents completion progress;
6. `NOOP` — no safe executable work remains.

Completion convergence is primary. Identity debt retains its starvation guard: oldest pending ≥24h or pending queue ≥20 makes the next eligible non-scout activation route to `RESOLVE` before opening new ordinary enrichment research.

## Persistence-first and completion-first work selection

The unit of productive work remains a **durable paper-stage transition**, but under v5 that is a secondary diagnostic unless it also reduces the paper's distance to `completed=true`.

Before substantial candidate research, establish the authorised writer/claim/dispatch path for the intended next completion gate. If it cannot be persisted in the activation, do not create a read-only cohort. Record the blocker/recheck condition once and select another executable completion gate.

A paper counts as materially progressed only after the new stage is written and read back successfully. Searches, locator rereads, issue comments, timestamps, CI checks, unchanged validation and engineering commits count as zero paper enrichment.

The primary operational view is now the completion frontier defined in `completion-first-v5.md`: deepest reached gate, first unmet gate and whether completion distance decreased. Ordinary active completion WIP is capped at six project-wide papers; blocked papers are parked with an exact recheck condition rather than left as unlimited WIP.

If an activation examines candidates but produces zero durable transitions, persist the common blocker key. The next activation may not repeat the same retrieval/selection/inference strategy unless that prerequisite changed.

## Heterogeneous calibration is global P0

The current completion predicate requires an accepted heterogeneous calibration receipt before paper-specific completion can be attested. Until that global gate is satisfied, the 12–18 paper calibration cohort is a project-wide P0.

Report `reference-checked calibration cases / 12 minimum` every non-scout activation. Cases count only after the independent/reference comparison is actually completed and persisted; proposal persistence alone does not increment the calibration numerator.

`CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-002` is currently the deepest calibration/frontier case because its private structured proposal has been persisted and read back. Its next intended gate is source-first independent comparison, not another unchanged inference run.

Select the remaining cohort deliberately for heterogeneity and completion feasibility, including full-text and hard cases, varied designs and missingness/source conditions, under `enrichment-adjudication.md`.

## Stateful discovery identity closure

Use `docs/operations/identity-resolution.md` and CILE-IDENTITY-RESOLUTION-2. Each provider observation is append-only state keyed by `observation_key`, with provider-independent `identity_key` only as a bibliographic grouping aid.

New unresolved observations are `pending`. They may resolve directly to known/not-forwarded outcomes, or use the explicit intake bridge:

`pending → forwarded_to_intake → resolved/new_candidate`.

A resolution comment cannot create a CandidateRecord. `new_candidate` is valid only after the normal v3 intake/recovery path has materialised the referenced CandidateRecord. Conflicting terminal states are rejected by the stateful validator.

## Validated branch recovery

Candidate metadata/identity workflows can validate and push an automation branch while repository token policy blocks PR creation. This is recoverable delivery debt, not a reason to rerun the underlying work.

Such workflows persist `cile-validated-branch-recovery:1` on #696 with branch/head/base/run identity. The next Lane-A/B activation, before new research, checks unresolved tickets. If the exact branch/head remains ahead of main and has no PR, it opens the PR through the authenticated GitHub connector. A validated branch must not remain without a PR for more than one subsequent activation unless a concrete connector/policy blocker is recorded.

## Durable scouting observations

`python3 -m scripts.query_checkpoint` validates and renders immutable query checkpoints. After each enumerable query, append/read back its permitted checkpoint before the next query. Incomplete fragments remain pending; a failed query remains failed.

At completed-window closeout, every observation counted as `unresolved_identity` must also exist as a durable CILE-IDENTITY-RESOLUTION-2 `pending` record. Aggregate counts without reconstructable identities are incomplete state.

The final batch still owns the governed v3 intake/terminal semantics. Partial evidence never manufactures a completed W1–W7 run or an inclusion decision.

## Engineering discipline and proof obligation

Lane A is the paper-production lane and does not open shared engineering/calibration repairs. Lane B alone owns shared throughput/persistence/calibration engineering, and only after higher-priority persist/complete/calibration-case/required-resolve work is unavailable.

Engineering is bounded tracked work and counts as zero paper enrichment until later real paper transitions demonstrate a gain. Under v5, a shared engineering change must demonstrate at least one downstream completion-gate transition within the next two eligible automation activations. If it does not, record it as unproven engineering debt and do not continue engineering the same class without new trace evidence.

If Lane A reports no actionable authorised writer/claim for ordinary completion work in two consecutive eligible activations, Lane B treats the missing generic governed writer/claim path as a shared throughput blocker before unrelated optimisation work.

Failure clusters follow `docs/operations/calibration-trace-audit.md`. Do not extend timeouts or repeat unchanged model paths merely to obtain a different result.

## Soft runtime close

At roughly 20 minutes of active work, enter soft-close: do not open a new paper cohort, search family, engineering branch or external workflow. Finish/persist/read back work already in flight, or leave an exact recoverable checkpoint/run/branch for the next activation. Do not poll long-running external jobs simply to fill the hour. Transactional safety and required terminalisation take precedence over the soft-close threshold.

## Completion policy and public index

`ontology/modules/completion-policy.json` remains CILE-COMPLETION-POLICY-2. Scientific completion requires the current accepted receipt and mandatory review checklist; inference success, PDF availability, abstract availability, proposed framework class or green CI are not completion.

Framework assessment may be a grounded proposed class or grounded `outside_framework` only under the existing independent acceptance rules. `insufficient_evidence` does not qualify.

The public research index remains revision-bound, lazy-detail and fail-closed. Unknown, failed, stale and withheld are distinct. The registered CandidateRecord denominator remains separate from canonical/eligible work populations.

## Original PDF and bibliography delivery

The existing private store remains the only authorised location for retained source/full-text/document/bibliography data. Exact original bytes are hash checked/read back; a downloadable file does not imply redistribution rights. Private research retention and public redistribution remain separate permissions.

`python3 -m scripts.enrichment.retain_document` handles reviewed, registered, allowlisted, hash-pinned sources through the existing signed service. Source text/PDF bytes must not enter GitHub, Pages or ordinary workflow artifacts.

Actual-paper bibliography, provider references and incoming citations remain distinct. Completion requires the current governed bibliography/null-assessment rules and cannot be inferred from provider citation coverage.

## Acceptance, verification and reporting

Report separately: scouting observations/intake; identity-resolution debt; completion-frontier state; source/document readiness; proposals/framework/bibliography state; independent comparison; calibration numerator; review-ready papers; accepted receipts; engineering/audit changes; and public revision identity.

The primary operational KPI is now papers whose completion distance decreased, followed by deepest gate reached, calibration progress toward 12 minimum, review-ready papers and final completions. Distinct papers with a durable stage transition remains a secondary operational metric and never substitutes for convergence.

Global CI/deployment/public-index verification is required after relevant state changes, not as an unchanged activity loop.

Maintenance changes follow `AGENTS.md` validation/merge rules. Scientific/canonical decisions retain their independent curator/human gates.
