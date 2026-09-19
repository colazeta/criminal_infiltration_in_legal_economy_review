# CILE ↔ Kora pilot integration contract

## Purpose

This pilot makes Kora an **observable control plane** for the existing Criminal Infiltration Literature Archive automation. It does not replace the current CILE-HOUR40-1 scheduler, Cloudflare persistence, claims, fencing, catch-up semantics, immutable attempts, GitHub recovery paths, or scientific governance.

## Authoritative systems

- Existing CILE automation remains authoritative for scheduling and persistence.
- The private enrichment store remains authoritative for candidate, source, proposal, bibliography, comparison, completion and validation state.
- Kora v0.1 records routing evidence only.
- Scientific eligibility, canonical identity and human validation remain outside this workflow.

## Trigger

The workflow starts from message `cile-activation-observed`. The existing automation should eventually send one message per observed lane activation. Kora itself must not add :10 or :40 timers in this pilot.

## Routing contract

The workflow mirrors the current order:

1. due owned scouting window → `SCOUT`;
2. unfinished safe write → `PERSIST`;
3. executable F0–F5 transition on deepest owned paper → `COMPLETE`;
4. validation/calibration case → `CALIBRATION_CASE`;
5. due identity debt → `RESOLVE`;
6. Lane B shared blocker only → `ENGINEER`;
7. otherwise → `NOOP`.

It also surfaces two explicit safeguards:

- ordinary assessment WIP above six → `BLOCKED`;
- inconsistent F0–F7 predicates → `BLOCKED`.

Owner clarification, 19 September 2026: a due `SCOUT` or unfinished safe
`PERSIST` may precede these blockers only when that selected activity is
independent of both the inconsistent frontier and ordinary assessment WIP.
The observing caller must positively attest this with, respectively,
`scout_independent_of_frontier_and_wip: true` or
`persist_independent_of_frontier_and_wip: true`. The optional fields have no
implicit true default: absence or false preserves `BLOCKED` in a collision.
An attestation for one route cannot authorize the other. Without a blocker,
the existing SCOUT/PERSIST order is unchanged. These are operational input
attestations, not scientific decisions, claim receipts, or write permissions.

Owner clarification, 19 September 2026: the mandatory identity starvation guard
pre-empts executable COMPLETE only when it would **open new research**. It does
not interrupt work already in progress or non-research work. SCOUT, PERSIST,
applicable frontier/WIP blockers, writer availability and anti-repeat checks
retain precedence. F3 does not imply new research.

The router's pure preflight computes `identity_starvation_status` from optional
`identity_preflight_evidence`, never from `identity_debt_due` or a caller-supplied
decision flag. The caller supplies these observations for the same preflight:

- `pending_observation_count`: nonnegative integer; absent/null means unknown;
- `oldest_pending_age_seconds`: nonnegative age of the oldest still-pending
  observation at preflight time; absent/null means unknown or not applicable for
  an explicitly empty queue;
- `activity_kind`: `new_research`, `in_progress`, `non_research`, or `unknown`,
  describing the work that COMPLETE would actually start, independently of its gate;
- `evidence_ref`: nonempty opaque reference to the evidence supporting these
  observations and activity classification. Never embed private content or secrets.

`required` means new research and age >=86400 seconds OR count >=20.
Either positively established threshold suffices; the other may be unknown.
`not_required` means evidenced in-progress/non-research activity, or new research
with both thresholds observed below limit, or an explicitly empty queue.
An empty queue with a supplied pending observation age is contradictory.
Missing provenance, unknown activity, insufficient or contradictory queue
evidence produces `undetermined`, not false. Before an otherwise executable
COMPLETE, `required` selects RESOLVE and `undetermined` selects BLOCKED.
The decision includes the tri-state and its reason even when a prior route wins.
No new-research permission follows from missing evidence. `identity_debt_due`
retains only the existing lower-priority ordinary-debt routing role.

This observe-only pilot computes over supplied evidence; it does not collect
queue data, verify referenced records, or call the private review service.
The observing adapter must establish those facts before any future live use.
Synthetic fixtures are not real queue measurements. The two original
underspecified fixtures are preserved in full in replay/history, including
their RESOLVE expectations and earlier mismatch results. Owner-authorized
current versions keep identical inputs but explicitly expect BLOCKED with
identity_starvation_status=undetermined and missing_preflight_evidence.
This revision follows the insufficient-evidence contract above, not the SUT's
output. The versions have distinct case IDs and links to their historical IDs.
The historical cases are outside the selected tests/ bundle; the current
versions retain active schema/exact gates. Explicit-evidence threshold cases
continue to require RESOLVE. Test failure exit-code rules are unchanged.

The anti-repeat flag suppresses an unchanged `COMPLETE` attempt but does not prevent a different safe route.

## Frontier contract

`F5_ASSESSMENT_COMPLETE` is computed only when the current candidate has durable full text, persisted proposal, accounted mandatory fields, grounded framework assessment, independent comparison, references/bibliography readiness, limitations/caveats, and matching version guards. It is not human acceptance.

`F6_VALIDATION_READY` and `F7_VALIDATED` remain a separate validation track.

## Side-effect boundary

Every v0.1 route decision emits `side_effect_authorized=false`. The authored
project manifest keeps `network.defaultAction: deny`; these changes do not
broaden it. The saved source export of existing release `rel_4wbyk58gsiuzfh8f`
instead contains `allow` and `inheritManaged: true`. That discrepancy must not
be treated as proof of deny in the immutable release; its server-side origin
and compiled execution policy still require verification. The release does not
include the subsequent source fixes. This pilot must establish routing
consistency before any connector is granted write access.

## Phase 2 gate

Only after the observe-only pilot is stable should Kora be connected to the private enrichment service. The existing machine interface uses a signed HMAC service envelope and supports operations including `verify`, `status`, `run`, `packet`, `proposal`, `source`, `document`, `bibliography`, completion and checkpoint operations. On hosted Kora SaaS, a custom customer extension cannot simply be installed; available Kora-shipped extensions must be inspected first. If no suitable HTTP/signing extension exists, the connector requires either a supported built-in path or a self-managed Kora extension.
