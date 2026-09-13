# Targeted reading retrieval

When the mechanical abstract cascade or first-pass assisted search does not expose a reliable abstract, the review may run a targeted per-record retrieval pass using exact DOI, exact title, author, book or venue metadata, publisher pages, institutional repositories, book previews and verified alternate manifestations.

The goal is to improve curator reading support without changing eligibility. Higher-confidence results may replace an earlier preparatory aid through `data/curation/reading_aid_overrides.json`.

An override may upgrade a `metadata_warning` or `review_synopsis` to a `publisher_summary`, `full_text_intro` or `verified_abstract_source` only when the exact work identity and source support that label. A source that verifies only identity must not be represented as an author abstract.

Targeted retrieval remains non-decisional. Screening, canonicalisation and publication require their existing human-governed gates.

## Parallel Search assisted OA retrieval

For already-registered candidates, Parallel Search is a normal targeted-retrieval channel under the 2026-09-12 owner instruction. Query exact DOI first; otherwise use a strict title/author/year formulation. Prefer publisher, institutional repository, recognised scholarly repository/preprint and direct OA PDF manifestations. Verify the final source before writing any locator or synopsis.

A search excerpt is not a substitute for an accessible paper. If only the author/publisher abstract is actually verified, mark the reading basis `abstract_only`; if only selected substantive passages are verified, treat it as partial text; use `full_text` only when the whole scholarly manifestation is actually available to the retrieval step. Information absent from the available evidence remains `not_verifiable`. Public reading aids contain concise paraphrases and provenance only, never copied full text or long abstracts.

This lane may improve methods/findings/variable reading support only when those claims are supported by the final OA scholarly source. It does not convert such support into a scientific decision or an approved extraction proposal.

## Completion-first delivery contract

The sidecar owns its unfinished branches, PRs and mechanical `automation/selected-support-*` follow-ups. Before selecting another batch, inspect the current head, run ID, attempt, jobs and terminal result. `queued`, `in_progress`, `action_required`, `failure` and `success` are different states. Never keep waiting for a repair that has already finished, and never infer publication from an old green observer. An independent global backfill is not itself a reason to stop candidate-bound work; conflicting writes require evidence of a live writer to the same branch or data.

On a branch reconciled non-destructively with current main, retain the verified source findings first and then run:

```sh
python3 scripts/retrieval/selected_paper_delivery.py --prepare --validate
python3 scripts/retrieval/apply_verified_reading_locators.py --check
```

Preparation applies the existing full-text locator bridge and verified-abstract bridge, then regenerates deterministic public projections. It performs no external search or full-queue backfill. Validation runs the full mandatory block in `AGENTS.md`; none of the scientific or ontology checks is removed. Include changed support ledgers and deterministic `site/data` projections in the same reviewed PR as the reading aids. Inspect the final diff, the ordinary quality check on the actual head, and any review blockers before an expected-head-guarded merge. No direct-main or force-push fallback is permitted in this lane.

The read-only audit is:

```sh
python3 scripts/retrieval/selected_paper_delivery.py --check
```

It checks candidate identity parity between the current queue and public register, the materialised count, unique override identities and the presence of verified locators/abstract support. Missing general coverage rows are reported separately: preserving a new CandidateRecord is not conditional on finding its abstract, full text or scientific label. A full-text locator is not proof of OA reuse rights or a private source-ingestion receipt. All private retention still needs the authorised ingestion path, exact-source hash and provenance; scientific proposals still need calibration and adjudication.

The existing retrieval and abstract workflows distinguish local support-only pushes from full refreshes. Scheduled runs, queue/code changes and unresolvable Git history still use the full provider cascade. Local-only pushes use the existing verified bridges instead of searching the whole queue again. Both writers share a serial group; active work is not cancelled. `queue: max` is only GitHub's bounded pending queue (up to 100 runs), not the canonical at-least-once record. Cloudflare `CILE-HOUR40-1`, its tickets, leases, catch-up watermark, namespace and failed-ticket history remain unchanged.

Mechanical persistence retains a content-addressed branch/PR and fails explicitly when quality, permissions or a moved main prevent completion. An identical validated diff against the same base reuses that checkpoint instead of multiplying run-ID branches. Because a PR created with the repository `GITHUB_TOKEN` does not recursively start an ordinary pull-request workflow, the support writers use the supported `workflow_dispatch` exception to run the archive quality workflow on the exact retained head. The merge still requires that dispatched quality run to finish successfully, an unchanged validated main and an expected-head guard. A retained branch, dispatched run or green preparation step is not itself main persistence or public deployment.

For an owner-authored selected-paper PR, the retrieval workflow may commit deterministic support projections back to that same PR branch after the full mandatory validation. It then explicitly dispatches archive quality on the generated head. A bot-authored head that GitHub marks `action_required` is not treated as running or green; the explicitly dispatched final-head quality run is the validation receipt. If dispatch is denied, the branch remains a recoverable checkpoint and the workflow fails rather than inventing success.

The next invocation reuses an unresolved checkpoint rather than creating another paper batch or another temporary repair workflow. Checkpoint information belongs in the existing PR/issue and workflow summary: observed slot if available, candidate IDs, base/head, exact run/attempt, completed stages, blocker and next safe action. Do not publish private evidence in checkpoints.

A sidecar result has three honest outcomes: verified support delivered to main and its governed public surface; an explicit recoverable blocker with retained work; or a documented no-safe-improvement result after bounded source checks. A merged PR is not yet a Pages deployment. Verify the actual downstream receipt and served public records before claiming end-to-end publication. Citation-provider completion remains provider-specific, and none of these operational outcomes constitutes scientific approval.

## Audited failure modes: 13 September 2026

Batch 13's repair had already completed while later reports still treated it as queued/running. PR #495 was reconciled and merged only after a fresh ordinary quality check. Its deterministic projections restored 242 existing CandidateRecords where the old projection counted 174; the 68 recovered records were not new discoveries or scientific inclusions by the retrieval lane.

The delivery repair removes reproducible failure patterns: full-queue provider scans triggered by small already-verified reading updates; successful workflow exits after persistence was blocked; cancellation of an earlier publication run by the outer archive concurrency group; duplicate retained branches for the same mechanical diff; and token-created support PRs that could never acquire the quality check awaited by their own persistence step. It also keeps all mandatory validation commands together and checks delivery identities rather than treating a green scheduler as evidence that papers were published. Historical failed runs and Cloudflare tickets retain their original status.
