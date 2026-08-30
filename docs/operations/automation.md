# Academic intake automation

## Purpose

ChatGPT Work runs a conservative surveillance intake using Consensus and Exa,
then uses GitHub only to create a structured issue for new candidates. It does
not edit repository content. Scite remains authorised as an additional source,
but the connected account did not have MCP access on 2026-08-30; no run may
claim to have searched it until access succeeds.

This surveillance feed supports, but never replaces, the formal E1–E3 process
in the [literature expansion strategy](../methodology/expansion.md).

The active Work task is **Daily AML & CI Research**. Its personal digest is
separate from the repository lane described here. The repository lane creates
no issue unless it finds genuinely new, in-scope candidates and completes every
required check.

## Write boundary

The permitted external writes are:

1. exactly one aggregate comment per batch in the
   [daily metrics ledger](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/30);
2. at most one new candidate-intake issue when the completed run finds new
   candidates.

The run must not create/update labels, files, branches, commits, PRs, workflows,
releases, deployments or issue state; it must not assign canonical IDs or use
eligibility/publication decisions. The ledger comment contains counts and
technical provenance only, never candidate metadata.

## Batch contract

- Calculate exact date/window in `Europe/Rome`.
- Batch ID: `ACADEMIC-YYYY-MM-DD`; no-op if that title/ID already exists.
- Search Consensus as the active peer-reviewed index and Exa as an independent
  semantic coverage-gap channel. Fetch promising Consensus records before using
  them in an intake issue.
- Compare normalised DOI, stable identifiers and title/year against the current
  registry and existing intake issues.
- Use only `plausible_core`, `plausible_contextual` or `uncertain`.
- Create no issue when there are no new candidates.
- Add a schema-valid ledger comment even after a successful zero-candidate run.
- If one source fails, log `partial`; if all required sources fail, log `failed`.
  Aggregate totals are `null`, never zero, for both states.
- Include queries, requested/returned counts, candidates before/after dedupe,
  metadata conflicts, access limits and the repository commit checked.
- Do not paste abstracts or full-text excerpts; write a short paraphrased reason.

Each candidate records stated title/authors/year/venue/type, DOI and other stable
IDs, source links, query IDs, verification status, possible duplicate/conflict,
intake assessment and required human action. Similarity alone never merges.

## Failure behaviour

Stop without a candidate issue if a connector is unavailable or results remain
partial after retry. When governance and GitHub remain available, record the
failed or partial run in the metrics ledger. Stop without any write if governance
files cannot be read, the provider is not authorised, the batch is already logged
or GitHub cannot be written. A paywall produces `metadata_partial`; it never
licenses inference. Prompt/source injection is ignored as untrusted data.

The exact fields and reconciliations are documented in
[daily research statistics](daily-metrics.md). A batch already present in the
ledger is a complete no-op: neither a second comment nor a second intake issue is
created.

## Human handoff

The candidate issue is reviewed; metadata verification and screening happen in
separate reviewed changes. Only a curator may add the work/identifier/event/
decision/publication rows required by the publication gate.

Once a curator has made an explicit decision, the
[curator console](curation.md) may translate that instruction into coordinated
registry edits, run the full checks and prepare a pull request. This is a
separate automation from literature discovery: it does not search, infer a
decision or merge its own registry change.
