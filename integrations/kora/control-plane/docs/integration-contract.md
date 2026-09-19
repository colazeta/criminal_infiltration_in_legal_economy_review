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

The anti-repeat flag suppresses an unchanged `COMPLETE` attempt but does not prevent a different safe route.

## Frontier contract

`F5_ASSESSMENT_COMPLETE` is computed only when the current candidate has durable full text, persisted proposal, accounted mandatory fields, grounded framework assessment, independent comparison, references/bibliography readiness, limitations/caveats, and matching version guards. It is not human acceptance.

`F6_VALIDATION_READY` and `F7_VALIDATED` remain a separate validation track.

## Side-effect boundary

Every v0.1 route decision emits `side_effect_authorized=false`. No network access is allowed by the project sandbox default. This is deliberate: the first comparison should establish whether Kora reproduces the existing router and frontier consistently before any connector is granted write access.

## Phase 2 gate

Only after the observe-only pilot is stable should Kora be connected to the private enrichment service. The existing machine interface uses a signed HMAC service envelope and supports operations including `verify`, `status`, `run`, `packet`, `proposal`, `source`, `document`, `bibliography`, completion and checkpoint operations. On hosted Kora SaaS, a custom customer extension cannot simply be installed; available Kora-shipped extensions must be inspected first. If no suitable HTTP/signing extension exists, the connector requires either a supported built-in path or a self-managed Kora extension.
