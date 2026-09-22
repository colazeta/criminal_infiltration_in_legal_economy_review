# Academic intake and hourly hybrid automation

**Current operational source of truth:** `docs/operations/hourly-hybrid-v4.md` (15 September 2026). This file defines the surveillance/intake boundary used when one of the two hourly lanes enters a due `SCOUT` window. It no longer defines a separate daily scheduler or Exa-first provider order.

Scientific protocol, eligibility, rights, canonical identity and human acceptance remain governed elsewhere and are not changed by the hourly delivery architecture.

## Purpose

Scheduled surveillance identifies plausibly relevant scholarly works conservatively and persists them through the governed v3 intake/recovery path. It supports, but never replaces, the formal E1–E3 expansion process.

There is one scheduled ChatGPT living-review worker, not a separate discovery worker:

- the `:10` worker owns both the 08:00–20:00 Europe/Rome AM scouting window and the 20:00–08:00 PM scouting window.

The former `:40` scheduler is retired and must not be recreated. The single worker enriches/reconciles by default and scouts only when the currently open window is due and unsatisfied. See `hourly-hybrid-v4.md` for routing and runtime closeout.

## Scheduled provider rule

Parallel Search is the default scheduled discovery provider. Exa is optional only when it is positively known to be available and materially useful for recall/verification. Do not repeatedly probe a known exhausted Exa quota. Consensus and Scite are excluded from scheduled surveillance.

W1–W7 coverage, adaptive novelty depth, query rotation and stopping rules are in `novelty-depth.md`.

## Discovery write boundary

The external scouting step may write only the governed operational evidence required by the current contracts:

1. durable enumerable query checkpoints on issue #696, read back before the next query;
2. one CILE-IDENTITY-RESOLUTION-2 `pending` record on #696 for every observation still counted as unresolved identity at completed-window closeout;
3. at most one structured v3 intake issue for new candidates from the completed batch;
4. exactly one schema-valid terminal surveillance ledger comment for the batch on issue #30.

For compatibility with the metrics validator and `docs/operations/daily-metrics.md`, the terminal is the **aggregate comment per batch**. A **successful zero-candidate run** still writes that aggregate terminal. `partial` and `failed` runs use the governed incomplete-run semantics rather than inventing zero counts.

It must not edit repository files, branches, PRs, canonical registries, scientific decisions or publication acceptance directly. Mechanical CandidateRecord preservation occurs through the repository-owned recovery writer. Candidate identity-resolution comments do not create CandidateRecords.

A failed/partial provider call is not a zero-result query and must not manufacture intake counts.

## Current v3 intake contract

New scouting batches use surveillance/intake schema version 3 and the current operational registration protocol. The batch records the exact 40-character `main` commit observed for deduplication/reconciliation.

A completed batch has one final scheduled provider in its search manifest and a complete W1–W7 query set for that provider. The current provider is normally Parallel Search; Exa query ids are valid only when Exa was intentionally selected under the current provider rule. Do not mix incomplete provider attempts into final yield denominators.

Candidate ids remain stable governed `CAND-...` identifiers. Candidate records may contain only observed/verified bibliographic data and permitted triage fields. Missing year, venue, DOI or access evidence remain missing/unknown; never manufacture them.

Intake assessments remain only:

- `plausible_core`;
- `plausible_contextual`;
- `uncertain`.

Only governed scientific review may use eligibility/exclusion decisions.

### Minimal candidate fields

A v3 CandidateRecord intake contains, as governed by the current schema/template:

- candidate id;
- stated title/authors/year/venue/work type when observed;
- DOI/other stable identifiers when observed;
- source links;
- provider/query provenance;
- metadata verification/conflict/possible-duplicate state;
- intake assessment and short paraphrased relevance reason;
- required human action;
- governed open-access/access receipt, including explicit unknown state when positive evidence is absent.

Do not paste abstracts or full-text excerpts into intake.

## Query checkpoints and telemetry

After each enumerable query, persist the full permitted checkpoint through the existing `scripts.query_checkpoint` contract and read it back before starting another query. Do not rely on conversational context to retain long result sets.

Maintain at least the telemetry defined in `novelty-depth.md`: raw occurrences, unique retrieved observations, known matches, known new manifestations, unresolved identities, unseen assessed, unseen plausible scholarly works and intake candidates.

Every unresolved identity must have a durable CILE-IDENTITY-RESOLUTION-2 `pending` record before closeout. The aggregate unresolved count and the durable records must reconcile.

## Identity closure and intake handoff

`docs/operations/identity-resolution.md` is authoritative.

An unresolved observation is first `pending`. Candidate-bound verification may resolve it to a known CandidateRecord/manifestation or `not_forwarded`. When it is sufficiently distinct and plausible to enter intake but no CandidateRecord exists yet, append `forwarded_to_intake` and route it through the normal v3 intake/recovery path. Only after actual CandidateRecord materialisation may the observation terminate as `resolved/new_candidate`.

Do not silently merge manifestations or treat identity grouping as canonical ScholarlyWork acceptance.

## Candidate preservation and recovery

Before new discovery, check for completed valid intake whose candidates are not represented/reconciled downstream. Candidate preservation debt takes priority over additional recall. Use the existing recovery writer and canonical recovery issue #362 where required; an open issue is not a live lease.

The invariant is zero orphaned valid intake candidates caused solely by races, skipped jobs or transient delivery failures.

## Validated automation branch recovery

Metadata/identity workflows may validate and push an automation branch but fail to open its PR because repository policy blocks token-created PRs. Those workflows now persist a `cile-validated-branch-recovery:1` ticket on #696.

The next automation activation must check unresolved tickets before new research. If the exact branch/head is still ahead of `main` and has no PR, create the PR through the authenticated GitHub connector. Do not rerun the underlying metadata/scientific work just to recreate the branch.

## Terminal states

A completed surveillance terminal is valid only when the selected final provider completed the governed planned query set and all required unresolved/intake state was durably persisted/read back.

If the selected provider is incomplete, use the current schema-valid `partial`/`failed` semantics and preserve actual completed-query evidence. Aggregate volume counts that are not known must remain null rather than being invented as zero. Partial/failed batches cannot manufacture CandidateRecord intake.

A completed zero-candidate run means only zero marginal CandidateRecord yield for the executed families/depth. It is not saturation.

## Safety and fail-closed rules

Stop without unsafe writes when source authorisation, identity resolution, evidence, ontology conformance, issue idempotency, write authentication or publication gates cannot be verified. Do not weaken scientific validation, infer licences from availability, expose private/full text, or turn a model proposal into scientific acceptance.

## Runtime behaviour

Follow the soft-close in `hourly-hybrid-v4.md`: after roughly 20 minutes, do not open another paper cohort/search family/engineering branch. Finish or checkpoint work already in flight and leave long external workflows for a later activation rather than polling indefinitely.

## Reporting

Report the actual resume state, not activity volume: scouting terminal/provider/query coverage; unresolved identities persisted; intake candidates materialised or awaiting recovery; durable paper-stage transitions; validated-branch recovery debt; blockers; and the exact next recoverable action. Searches/comments/CI do not count as paper enrichment.
