# Two-lane delivery and recovery

Owner implementation mandate: 14 September 2026; persistence-first/identity-resolution v4 amendment and assessment-completion v5.1 amendment: 15 September 2026. `docs/operations/completion-first-v5.md` is the current source of truth for KPI priority, work selection, WIP control and the meaning of `Completed`. `docs/operations/hourly-hybrid-v4.md` remains authoritative for cadence, provider order, identity-resolution, branch recovery, anti-repeat and runtime closeout where v5.1 does not supersede it.

## Critical terminology

**Completed = assessment complete.** It means the current paper has a complete, persisted, source-grounded assessment under the F0–F5 predicate in `completion-first-v5.md`. It does not require owner/human validation.

**Validated / Accepted** is separate. Calibration acceptance, exact-head human review and adjudication receipts belong to the validation track. A paper can be `Completed=yes, Validated=no`.

Until the public projection/UI is migrated, any legacy `completed=true` field that still means accepted adjudication must be described as a legacy validation/acceptance field and must not be used as the operational Completed KPI.

## Consolidated hourly worker and scouting windows

As of the owner consolidation on 22 September 2026, the single scheduled ChatGPT living-review worker runs at :10 and owns both project-wide scouting windows: 08:00–20:00 Europe/Rome and 20:00–08:00 Europe/Rome. The former scheduled :40 Lane B is retired and must not be recreated. There are exactly two project-wide scouting windows per day, and the :10 worker scouts only when the currently open window is due and unsatisfied.

The existing `CILE-HOUR40-1` private enrichment service, namespace, claims, fencing, catch-up semantics and immutable attempts may remain where required for compatibility with persisted history. They are not a second scheduled ChatGPT worker and do not own the PM scouting window. Candidate ownership and historical attempts remain stable; timestamps and hash assignment are not locks.

For scheduled scouting, **Parallel Search is the default discovery provider**. Exa is optional only when positively available and materially useful. Consensus and Scite are excluded from scheduled surveillance.

## Current router

A due owned scouting window selects `SCOUT`. Otherwise resume unfinished safe writes, then route:

1. `PERSIST` — finish/read back an assessment-gate write;
2. `COMPLETE` — advance the deepest owned paper toward `F5_ASSESSMENT_COMPLETE`;
3. `CALIBRATION_CASE` — advance validation/calibration evidence without displacing executable assessment-completion work;
4. `RESOLVE` — advance required CILE-IDENTITY-RESOLUTION-2 debt;
5. `NOOP`.

Shared persistence/calibration engineering is owned by the repository-designated maintenance owner/lane, not by a second scheduled research worker.

Identity debt keeps the v4 starvation guard.

## Completion-first work selection

The primary unit of success is a paper whose distance to complete assessment decreases. A `durable paper-stage transition` is required evidence but is only a secondary metric.

Before substantial research, establish the authorised writer/claim/dispatch path for the intended next assessment gate. Do not build read-only cohorts when persistence is unavailable. Record the blocker once and move to another executable assessment gate.

The primary frontier is:

`F0 metadata/source → F1 full text → F2 proposal persisted → F3 independent comparison → F4 bibliography/references ready → F5 assessment complete`.

`F6 validation ready → F7 validated` is a separate quality/acceptance track and does not define Completed.

Ordinary active assessment WIP is capped at six project-wide papers. Blocked papers are parked with exact blocker/recheck conditions.

## Calibration track

The 12–18 case heterogeneous calibration remains important for scientific validation and scaling confidence, but it is not a prerequisite for `Completed` under v5.1.

Report `reference-checked calibration cases / 12 minimum` separately. Cases enter that numerator only after their independent/reference comparison is completed and persisted.

CAND-002 currently has a persisted structured proposal. Its next assessment gate is source-first independent comparison, not another unchanged synthesis run.

## Stateful identity closure and branch recovery

Preserve CILE-IDENTITY-RESOLUTION-2 append-only state, real CandidateRecord existence checks, `pending → resolved` / `pending → forwarded_to_intake → resolved/new_candidate`, and the existing starvation guard. Do not manufacture pending identities from the historical exact reconstruction deficit.

Validated branch recovery remains mandatory. The v4 `cile-validated-branch-recovery:1` ticket is still authoritative: an exact validated branch/head ahead of main with no PR is recovered through the authenticated connector rather than by rerunning the underlying work.

## Engineering discipline

The scheduled living-review worker does not open shared persistence/calibration engineering. The repository-designated maintenance owner/lane owns that work when a demonstrated blocker requires it.

Engineering itself counts zero assessment completion. A shared engineering change must demonstrate at least one downstream F0–F5 gate transition within the next two eligible activations or be recorded as unproven engineering debt.

If the scheduled living-review worker lacks an authorised ordinary completion writer/claim in two consecutive eligible activations, the maintenance owner/lane treats that as a shared blocker before unrelated optimisation.

Failure clusters continue to follow `calibration-trace-audit.md`; no unchanged retries or exception-by-exception patching.

## Soft close and anti-repeat

At roughly 20 minutes, enter **soft-close**: open no new paper cohort, search family, engineering branch or external workflow. Finish/persist/read back in-flight work or leave exact recoverable state. Do not poll long jobs to fill the activation.

Do not repeat an unchanged zero-progress retrieval/selection/inference strategy until its prerequisite changes.

## Completion versus validation reporting

Every activation reports separately:

- `Assessment Completed / registered` — primary Completed KPI;
- `Validated / Assessment Completed` — separate scientific/human acceptance KPI;
- assessment frontier and first unmet F0–F5 gate;
- papers whose assessment distance decreased;
- independent comparison and bibliography/reference progress;
- calibration numerator;
- validation-ready/validated transitions;
- blockers and recheck conditions;
- engineering proof status; and
- exact next action most directly reducing distance to complete assessment.

Human acceptance remains protected and must never be fabricated. The terminology split changes what `Completed` means operationally; it does not weaken evidence, privacy, rights, ontology, scientific review or exact-head acceptance requirements for `Validated`.
