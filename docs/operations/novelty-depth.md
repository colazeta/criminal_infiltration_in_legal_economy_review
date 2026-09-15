# Adaptive novelty depth for scheduled living surveillance

Current operational amendment: 15 September 2026. Read together with `hourly-hybrid-v4.md`. This document governs search depth inside a **due scouting window**; it does not create an hourly scouting cadence. There are two project-wide scouting windows per day and the hourly workers enrich/recover by default.

## Purpose

Do not confuse a fixed provider rank cutoff with meaningful discovery depth. Once known works dominate the head of a ranking, examining only the first 10 or 20 hits can create an artificial zero-yield result even though unseen literature remains below the cutoff or behind materially different query formulations.

The target is **unseen plausible scholarly works**, not raw search results.

For each W1–W7 workstream, aim to assess up to:

`NOVELTY_TARGET = 10 unseen plausible scholarly works`

subject to the stopping conditions below. This is an operational recall target, not a saturation rule and not a quota that authorises unsafe or unbounded searching.

## Current provider order

Scheduled scouting uses **Parallel Search by default** under `hourly-hybrid-v4.md`. Exa may be used only when it is positively known to be available and materially improves recall or verification. Historical Exa-primary / Parallel-fallback-only wording is retired for scheduled scouting.

Do not use Consensus or Scite for the scheduled lane. Provider failure, truncation or a partial query is never a zero-result observation.

## Identity classes during retrieval

Classify each retrieved observation conservatively before novelty accounting:

1. `known_exact_work` — already represented by sufficiently reconciled identity;
2. `known_work_new_manifestation` — another repository/publisher/working-paper manifestation of an existing CandidateRecord;
3. `possible_duplicate` / unresolved identity — similarity exists but identity is not safely closed;
4. `unseen_non_scholarly_or_clearly_outside_lane` — newly encountered but not a plausible scholarly intake item;
5. `unseen_plausible_scholarly` — newly encountered scholarly/plausibly scholarly work that may warrant governed intake.

Known observations do not consume the novelty target. Unresolved identities are not silently counted as unseen resolved works: they enter CILE-IDENTITY-RESOLUTION-2 before scouting closeout. A novelty classification is upstream of scientific screening.

## Adaptive search depth

For each W1–W7 workstream during the due window:

1. execute one materially appropriate query through the current scheduled provider;
2. durably checkpoint and read back the enumerable result set before opening the next query;
3. reconcile against the active CandidateRecord/register/intake state;
4. count unseen plausible scholarly works;
5. if the target has not been reached and the workstream has not hit a stopping condition, continue via deeper provider results or a materially different query formulation in the same workstream;
6. stop immediately when a canonical stopping condition is met; do not add decorative variants after closure.

W1–W7 are coverage objectives, not fixed strings. Preserve provider-scoped query ids such as `PARALLEL-Wn-Qm` or, when Exa is intentionally used, `EXA-Wn-Qm`.

## Stopping conditions

A workstream may stop for the current scouting window when at least one applies:

### A. Novelty target reached
At least 10 unseen plausible scholarly works were assessed for that workstream.

### B. Provider/interface limit
The authorised provider cannot expose further result depth or a materially larger set. Record the effective limit. This is not literature exhaustion.

### C. Governed runtime/search budget
The activation enters the soft-close/runtime boundary in `hourly-hybrid-v4.md` after materially distinct queries have been attempted. Preserve the achieved depth and close the workstream/window according to the terminal contract. A budget stop is not saturation.

### D. Repeated marginal-zero variants
Multiple materially different formulations add no unseen plausible scholarly works after deduplication. Record the variants and marginal yield. This supports a low-marginal-yield statement only for that query family/depth.

## Query rotation

Across successive scouting windows, rotate materially different concept families where useful, including direct infiltration terminology, criminal entrepreneurs, grey-area/collusion concepts, ownership/governance, professionals/intermediaries, seized/confiscated firms, administrative prevention, procurement, accounting/detection models, territorial expansion, non-Italian/non-English terminology, chapter-level contributions where permitted, and recent 2025–2026 terminology.

Do not repeat the same W1–W7 strings mechanically and do not weaken the eligibility construct to manufacture novelty.

## Gap recovery

Before describing a completed window as zero marginal CandidateRecord yield, inspect unresolved research-gap/backlog records such as issue #165 and successors. Gap records are search seeds only: rediscover and verify them through the authorised provider before intake. Known ingestion/persistence debt takes priority over opening new discovery when repository contracts say so.

## Required telemetry

Where the current schema permits, report or derive:

- `raw_occurrences`;
- `unique_retrieved`;
- `known_matches`;
- `known_new_manifestations`;
- `unresolved_identity`;
- `unseen_assessed`;
- `unseen_plausible_scholarly`;
- `intake_candidates`.

Every unresolved observation must also be persisted under CILE-IDENTITY-RESOLUTION-2 before closeout. Aggregate unresolved counts without durable identity records are incomplete operational state.

Useful diagnostics include `novelty_rate` and `known_share`; neither is a saturation statistic.

## Zero-result language

A completed window with no new CandidateRecord should be described as **zero marginal CandidateRecord yield for the executed query families and effective depth**. Never claim that the literature is exhausted, the universe is covered, the review is saturated or no relevant papers exist.

Formal saturation remains governed by `docs/methodology/saturation.md` and the full E1–E3 process.
