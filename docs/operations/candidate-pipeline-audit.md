# Candidate publication completion: audit of 13 September 2026

## Evidence

Read-only audit run 34749366281 captured main c0ca0753d5964ddbbce850904082069917b0695f,
the complete issue/ledger inventories and unauthenticated served JSON. Main queue
and public projection had 242 records; the served register had 174. The difference
was 68 materialised but unpublished candidates, not 68 new scientific inclusions.
Archive run 34749237449 passed quality but failed at aggregate-metrics retrieval.

The issue-open writer raced the later terminal. Competing writers shared a
cancelling group. Optional network enrichment delayed preservation. Queue commits
could omit deterministic public exports. Malformed aggregate telemetry stopped
the whole site. Existing PR #489 remained unmerged with obsolete architecture tests.

## Completion contract

1. Intake: immutable issue plus authenticated terminal pass all existing source,
   schema, query, identity, timing and provenance checks.
2. Preservation: one terminal-driven writer reconciles candidates, scaffolds
   missing coverage without network calls, rebuilds projections, validates the
   full repository and persists the transaction. Main identities are read back
   before source issues are closed. Exact rediscoveries do not inflate novelty.
3. Publication: after deployment, ordinary unauthenticated public JSON is read
   and every expected record is verified. Equal counts with wrong identities or
   stale metadata fail. The workflow summary retains counts and payload hashes.
4. Scientific inclusion remains a separate explicit curator decision. Provisional
   visibility never creates eligibility, canonical identity, verified OA or approval.

The writer has a separate non-cancelling job queue; unrelated skipped events do
not hold its lock. GitHub queue:max permits at most 100 pending jobs, not unlimited
capacity or exact starts. Immutable open intakes are the durable backlog and the
hourly :55 sweep retries outstanding work. A zero-addition sweep still rebuilds
exports and refreshes publication, repairing failed deployments without inventing
new papers. Failure of one historical intake does not withhold unrelated valid ones.

## Independent telemetry failure

The strict ledger validator remains mandatory for statistics. On failure, no
invalid counts are published: the existing empty baseline retains null unmeasured
candidate counts, and the page displays an explicit unavailability banner with
its statistics renderer disabled. Independently validated bibliography can deploy.
The workflow still ends with an explicit metrics error rather than false health.
No fallback applies to ontology, authorisation, candidate identity, public-field
allowlists, scientific decisions or repository/publication gates.

## Immutable bounded-text repairs

All original comments remain unchanged. Only explanatory notes/limitations were
shortened in exact replacements; numeric fields, provenance, identity, windows
and dispositions were compared and preserved. The first six replacements already
existed; their exact originals are now reconciled. The last three were authored
and validated during this audit.

| Original | Replacement |
| --- | --- |
| 5642881870 | 5647982401 |
| 5644857109 | 5647983636 |
| 5645417536 | 5647985121 |
| 5645995942 | 5647986524 |
| 5647932606 | 5647995845 |
| 5647933485 | 5647996999 |
| 5648912417 | 5652442044 |
| 5651755147 | 5652443544 |
| 5652293899 | 5652444573 |

The prior-day replacement is accepted only by exact comment ID, batch and actual
Rome creation date. The evidenced Exa 402 reason for e58052b5dd95 is also retained
in notes, as required for governed fallback. Unknown malformed future comments
remain rejected; these are not general waivers or edited history.

## Recurring-task preflight and boundaries

Before posting, round-trip the complete envelope through the actual repository
extract_run/validate_run functions and verify intake consistency. Notes: at most
ten strings, each <=280 characters; each source's limitations: at most ten strings,
each <=180 characters. Use authoring budgets of 240 and 160. Preserve real failure
diagnostics; never manufacture missing query counts, timestamps or completion.

Before new discovery inspect valid completed intake and publication debt. Under
the owner's separate maintenance authority the task may reopen the existing
exact-title [MAINTENANCE][INTAKE-RECOVERY] issue, creating it only when absent.
Reuse running recovery rather than duplicate requests or cancellation. This is
not permission for discovery to edit repository files, canonical registries,
scientific states or immutable terminal evidence.

At the initial snapshot intake #225 lacked an authenticated completed terminal.
It stays explicitly blocked until genuine evidence is recovered or all source
candidates are individually reconciled. Missing evidence must not be invented.

Local validation passed 521 Python tests, 150 Node tests, repository/ontology/
archive/site checks, required syntax checks and the telemetry-unavailable path.
The normal PR workflow must pass on the final head before merge. Runtime recovery
and actual served publication require separate evidence, not inference from tests.
The software repair adds no candidate data, scientific states or ontology concepts.
Temporary audit/application files are removed before final review and merge.
