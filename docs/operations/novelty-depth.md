# Adaptive novelty-depth rule for living surveillance

## Purpose

Living surveillance must not confuse a fixed search-engine rank cutoff with a
meaningful discovery depth. Once benchmark and already-known works dominate the
head of a ranking, examining only the first 10 or 20 returned results can produce
an artificial zero-yield run even though relevant unseen literature remains below
the cutoff or is reachable through a materially different query formulation.

This document governs the operational stopping rule for the Exa-primary surveillance
lane with a governed Parallel Search fallback. It does not change scientific eligibility, canonical identity, the formal
E1-E3 expansion protocol, or the human saturation decision.

## Core rule

The operational target is **unseen plausible scholarly works**, not raw search
results.

For each workstream W1-W7, the surveillance run aims to assess at least:

`NOVELTY_TARGET = 10 unseen plausible scholarly works`

A result is `unseen` only when it is not already represented in the active
operational register, the active review queue, or a relevant post-reset intake
issue after identity reconciliation under the repository rules.

A result that appears only in a research-gap/backlog issue is not considered
acquired. It must be independently rediscovered and verified under the current
protocol before it may become a CandidateRecord.

## Known results do not consume the novelty quota

Already-known works remain part of retrieval provenance and telemetry, but they
do not count toward `NOVELTY_TARGET`.

Example:

- 20 unique results returned;
- 15 are known exact works;
- 5 are genuinely unseen plausible scholarly works.

The workstream has reached novelty depth 5, not 20. The search must continue if
technically possible because the target of 10 unseen plausible works has not yet
been reached.

## Identity classes during retrieval

Each unique retrieved result is assigned one operational class before the
novelty quota is evaluated:

1. `known_exact_work` - already represented by a reconciled DOI, stable
   identifier, or sufficiently established title/year identity. It remains in
   telemetry and does not consume the novelty quota.
2. `known_work_new_manifestation` - a new repository copy, working-paper
   version, accepted manuscript, version of record, new DOI manifestation, or
   other representation of an already-known ScholarlyWork. Record the new
   provenance/metadata opportunity where permitted, but do not count it as an
   unseen work and do not create a duplicate CandidateRecord.
3. `possible_duplicate` - similarity exists but identity is unresolved. Do not
   silently merge it. It does not count as a resolved unseen work until the
   ambiguity is handled conservatively under the identity rules.
4. `unseen_non_scholarly_or_clearly_outside_lane` - newly encountered but not a
   plausible scholarly work for the surveillance lane. Record the retrieval
   outcome where the telemetry permits it; it does not satisfy the novelty
   target.
5. `unseen_plausible_scholarly` - a newly encountered scholarly or plausibly
   scholarly work that may be relevant under the intake standard. It counts
   toward the novelty target and, after the governed checks, is persisted as a
   pending CandidateRecord when the intake contract is satisfied.

The novelty rule is deliberately upstream of scientific screening. Counting a
work toward novelty is not an eligibility decision.

## Adaptive search depth

For every W1-W7 workstream:

1. Run the planned Exa query and preserve every returned occurrence while Exa remains available under the governed provider limits.
2. Reconcile identity against the active register, queue and post-reset intake
   issues.
3. Count unseen plausible scholarly works.
4. If the count is below 10, continue retrieval rather than treating the first
   rank page as exhausted.
5. Continue by one or both of these authorised mechanisms:
   - examine a deeper rank tail when the provider/interface permits it;
   - execute an additional materially different query within the same workstream
     using the next provider-scoped identifier (`EXA-Wn-Qm` for Exa;
     `PARALLEL-Wn-Qm` after governed fallback).
6. Stop that workstream only when one of the stopping conditions below is met.

A workstream is therefore a coverage objective and may contain multiple queries.
The target is not `top 10`, `top 20`, or another fixed number of raw results.

## Stopping conditions

A workstream may stop for the current surveillance run only when at least one of
these conditions is true:

### A. Novelty target reached

At least 10 unseen plausible scholarly works have been assessed for that
workstream during the current run.

### B. Provider/interface limit

The authorised provider or exposed connector does not permit further rank-tail
retrieval, pagination, or a larger result set. The run must record the requested
cap, effective cap and limitation. It must not describe the literature as
exhausted.

### C. Governed search-budget limit

The run reaches a documented operational budget limit after materially distinct
queries have been attempted. Record the limit and the unseen count achieved. A
budget stop is not a saturation claim.

### D. Repeated marginal-zero variants

Multiple materially different formulations within the same workstream produce
no additional unseen plausible scholarly works after deduplication. Record the
query variants and marginal yield. This supports a statement of low marginal
yield for that workstream/query family only; it does not establish literature
saturation.

## Governed Exa-limit fallback

Parallel Search is **not** a co-equal daily source. It is activated only when Exa
cannot continue because of a documented provider limit: credit/quota exhaustion,
rate limiting that remains after the bounded retry, or an exposed provider/interface
cap that prevents the required novelty-depth continuation. Generic metadata ambiguity,
GitHub failure, governance failure, authentication uncertainty or disappointing yield
do not authorise fallback.

When fallback activates:

1. stop issuing Exa searches for that batch;
2. record the Exa failure code, requested/effective cap where known, number of primary
   queries completed and any aggregate raw-occurrence telemetry in the run notes;
3. restart the coverage objective from W1 with Parallel Search and run W1-W7 under the
   same novelty target, identity rules, query rotation and stopping conditions;
4. use `PARALLEL-Wn-Qm` query identifiers in the fallback search manifest;
5. if the fallback completes, final batch counts and CandidateRecord intake are derived
   only from the complete Parallel Search rerun. The incomplete Exa attempt is diagnostic
   provenance and is not mixed into yield denominators;
6. if Parallel Search also fails before W1-W7 complete, the batch remains `partial` or
   `failed` under the terminal gate, with no intake.

This clean restart avoids provider-mix artefacts in candidate-yield statistics. A switch
to Parallel Search is therefore continuity handling, not evidence of literature
saturation and not permission to weaken `NOVELTY_TARGET`.

## Query rotation

Do not repeat the same seven prompts mechanically on every hourly execution.
W1-W7 are coverage objectives, not fixed strings. Use recent query logs and
marginal-yield telemetry to rotate materially different concept families.

Rotations should systematically cover, where relevant:

- direct infiltration/penetration language;
- criminal or mafia entrepreneurs;
- grey area / zona grigia / collusion / embeddedness;
- ownership, beneficial ownership, directors, shareholders and governance;
- figureheads, straw men, professionals, accountants, lawyers and intermediaries;
- seized/confiscated firms, judicial administration and post-removal outcomes;
- white lists, anti-mafia interdictions, legality certification, vendor integrity
  and administrative prevention;
- public procurement and sector-specific literatures;
- accounting characteristics, detection models, ownership networks, machine
  learning and risk indicators;
- territorial expansion/transplantation;
- non-Italian settings and non-English/local terminology;
- chapter-level contributions and edited volumes where the governed work type
  permits them;
- recent terminology and publications, especially 2025-2026.

Query rotation must not be used to weaken the eligibility construct or to add an
unapproved discovery provider.

## Gap-recovery rule

Before reporting zero marginal yield, inspect unresolved research-gap/backlog
records, including issue #165 and any successor gap inventory.

These records are search seeds only. They do not establish identity,
acquisition, eligibility, OA status, or a scientific decision. For any gap item
that is absent from the active register/queue/intakes:

1. search for it independently through the authorised surveillance provider;
2. verify enough bibliographic identity to avoid inventing metadata;
3. if rediscovered as a plausible scholarly and potentially relevant work,
   persist it through the normal v3 intake path as pending;
4. otherwise retain the unresolved gap and record the concrete reason.

Known ingestion debt must therefore be addressed before an hourly run is
reported as having zero useful novelty.

## Required telemetry

Where the existing schema permits, report or derive at least:

- `raw_occurrences` - all returned occurrences before within-run deduplication;
- `unique_retrieved` - distinct retrieved manifestations/results after within-run
  reconciliation;
- `known_matches` - results already represented in active governed state;
- `known_new_manifestations` - new manifestations of known works;
- `unresolved_identity` - possible duplicates/conflicts not safely reconciled;
- `unseen_assessed` - genuinely unseen results whose scholarly/plausibility
  status was assessed;
- `unseen_plausible_scholarly` - the operational novelty numerator;
- `intake_candidates` - unseen plausible works actually persisted under the
  intake contract.

If the current ledger schema lacks a dedicated field, keep the schema valid and
place the additional novelty-depth figures in the governed notes/limitations or
search-provenance artefact until a reviewed schema revision introduces explicit
fields.

Useful derived measures include:

`novelty_rate = unseen_plausible_scholarly / unique_retrieved`

and

`known_share = known_matches / unique_retrieved`.

Neither measure is a saturation statistic.

## Zero-result language

A completed run that persists no new CandidateRecord must be described as, for
example:

> Zero marginal CandidateRecord yield for the executed query families and
> effective ranking depth.

Never describe a surveillance zero as:

- the literature is exhausted;
- the universe has been covered;
- the review is saturated;
- no other relevant papers exist.

The formal saturation rule remains governed by
`docs/methodology/saturation.md` and requires complete assessable E1-E3 cycles
and human review.

## Relationship to the formal review

This rule improves recall in the recurring surveillance lane. It does not turn
that lane into a formal expansion cycle. Formal E1-E3 work still requires the
source, citation-frontier, screening and failure-inventory requirements in
`docs/methodology/expansion-reference.md`.

A high known share or repeated zero marginal yield can motivate a formal
coverage-gap or citation-expansion cycle; it cannot replace one.
