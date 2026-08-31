# Curator review queue

This directory is the governed, non-public working layer between legacy or
daily intake and the canonical archive.

- `review_queue.csv` contains one row per materialised candidate that still
  requires an explicit human review action.
- `actions.csv` is an append-only record of decisions submitted through the
  authenticated GitHub curator workflow.

Neither file is read by the public archive builder. Candidate metadata, review
evidence and curator identity must never be copied to `site/data/`.

## Initial legacy materialisation

The initial legacy subset of `review_queue.csv` is deterministically
reconstructed and checked by `scripts/curation/build_legacy_queue.py`. It
combines the E0 candidate outcomes with the pre-import audit, removes the two
works already represented in the canonical registry and assigns only a
**review stage**:

| Review stage | Meaning |
|---|---|
| `metadata_fix` | Bibliographic metadata must be repaired before screening |
| `manual_review` | Scope or contextual relevance needs a human decision |
| `abstract_full_text_review` | Title-level triage is insufficient |
| `legacy_rejection_review` | A pilot rejection signal is retained for re-checking, not treated as a governed exclusion |

Legacy recommendations are provenance only. They are not eligibility
decisions, publication approvals or evidence that two records are identical.

## Daily intake staging

`scripts/curation/import_intake_issue.py` validates an authorised daily intake
issue and appends its candidate manifest mechanically. It retains search links,
query IDs, verification status, possible duplicate/conflict notes, intake
assessment and required human action. It never writes to `data/registry/`.

Daily rows use `origin=daily_surveillance`. Partial, unresolved or conflicting
metadata is routed to `metadata_fix`; otherwise the row is routed to
`abstract_full_text_review`. Those routes are work assignments, not screening
decisions.

## Decision boundary

An authenticated curator decision updates the candidate's current queue state
and appends a row to `actions.csv`. It does not create a canonical paper, alter
`data/registry/`, or publish anything. Metadata verification and canonical
promotion remain separate reviewed changes.

The GitHub issue materialiser keeps open work visible, links merged actions to
the originating queue issue and closes only those issues whose current queue
status represents a completed screening outcome.
