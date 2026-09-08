# Review V2 delivery and verification

Technical implementation after the owner approved the audit plan. The existing
data rows and their historical decisions remain byte-identical. No seed is
approved, no new scientific decision is created and no T0 is assigned.

| Delivered surface | Verification |
|---|---|
| Neutral publication ontology, 32 private entity tables, field mappings | Ontology validator, isolated SQLite schema and foreign keys |
| Public model explorer and private V2 console | Closed generated definitions, assembled Worker serving test, no unauthenticated V2 access |
| Source typing and conservative identity match | Description/abstract distinction, absent title, wrong DOI, unrelated-title tests |
| Scientific proposal / receipt boundary | Four criteria, source/candidate identity, stale version, human exact-head approval, hash, atomic import and idempotency tests |
| Private evidence and append-only provenance | Exact source hashes/offsets, private storage retrieval, rollback of failed database batches |
| Durable daily runner | Rome DST, duplicate delivery, completed zero, partial recovery, successful-checkpoint reuse, expired final lease |
| Legacy statistics calendar | Eight dates / five gaps fixture; no missing execution counts invented; closed error-code allowlist |
| Preservation tools | Hash manifest, isolated restore, incomplete external-state gate, tamper rejection |
| Existing production safety fixes | Scientific auto-merge removed; generated guided module served; external CSP-compatible styles; OAuth/GitHub timeouts |
| Deployment gate | Full tests before production changes; deployed commit endpoint checked against workflow SHA |

Legacy daily scheduling is 07:00 Europe/Rome. GitHub's 06:20 UTC watchdog and
06:30 UTC publishing job remain secondary observations/publication; neither is
the scientific search runner. The external daily task is retained until V2 is
ready. A missing row is an operational gap, not a failed-source measurement or
a zero-result search. Daily source completeness includes absent expected days.

The new calendar projection uses explicit `--as-of` during deployment; the
committed legacy baseline remains deterministic. It displays coverage from the
aggregate ledger's effective date, 2026-08-31, through the projection date, last
observed ledger date, complete/partial/failed/missing/planned status, query
coverage and safe failure categories. Legacy retry counts remain unknown.

The Worker's future supervisor runs every 15 minutes when enabled. Expected
search time is 07:00 Rome; failed attempts become eligible for retry after
20 minutes then 60 minutes, respecting a longer Retry-After. Duplicate queue
messages cannot create another successful source/query checkpoint. Availability
is not absolutely guaranteed; missed work is made visible and recoverable.

V2 activation remains blocked until its private infrastructure, Consensus server
adapter, approved query manifest, complete external freeze and restore checks
pass. `GET /api/v2/status` shows the actual blockers after authentication. There
is no source substitution, empty success ledger, approval default or automatic
scientific import from legacy.

Rollback before activation reverts application code while retaining any empty
provisioned resources. Rollback after activation preserves V2 history and pauses
its writers before restoring the legacy public pointer. Never restore a dump
over an active database or reset global provider-budget counters.
