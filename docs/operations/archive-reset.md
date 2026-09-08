# Active archive reset — 8 September 2026

The owner explicitly instructed that the archive be reset now and restart from
zero under the new OA rules. Release 0.3.0 executes this operational instruction;
it neither assigns scientific eligibility nor activates the unprovisioned D1
Review V2 infrastructure.

## Reset scope

| Active data | Before | After reset |
|---|---:|---:|
| Canonical works | 2 | 0 |
| Work identifiers | 4 | 0 |
| Discovery events | 2 | 0 |
| Screening decision rows | 4 | 0 |
| Core publication history rows | 5 | 0 |
| Candidate records | 79 | 0 |
| Abstract / access / retrieval coverage | 79 each | 0 each |
| Assisted access evidence | 2 | 0 |
| Formal execution metrics | 1 | 0 |
| Candidate actions, coding and work relations | 0 | 0 |
| OA assessments and secondary publications | 0 | 0 |

Reading aids, manual overrides and residual abstract-resolution records are also
cleared. The editorial summary is a new explicit zero snapshot. Public archive,
secondary collections, curator totals and daily exports are rebuilt from these
empty active inputs. No past failure or search result is recoded as zero.

## Preservation and recovery

All 26 former registry/curation files are preserved byte for byte in
`data/legacy/pre-oa-reset-2026-09-08/`, with SHA-256/size inventory. Complete code
and data are retained by commit `f8d04e521fc2316acf82d339546a1b8e58f49db0` and branch
`legacy/pre-oa-reset-2026-09-08`. A local Git snapshot and isolated restore were
verified before editing the active files. The existing E0 pilot archive remains
retained separately. This is no claim of a complete private-infrastructure dump.

GitHub issue bodies and comments, ledger #30, previous PRs, deployment history,
credentials, application identity and provider-budget counters are retained in
place. The 79 old candidate issues are closed as retired operational tasks;
closure is not a scientific exclusion. The former research-gap task is also
retired. `retired-issues.json` records original issue states for recovery.

Rollback: pause new writers; retain any work created after this reset; restore
the former active data/code via a reviewed revert or the preserved commit;
reopen only the issue numbers in the retirement receipt and restore the earlier
automation scope. Verify all publication gates before redeployment. Never
restore over new work or reset provider budget counters.

## Active cycle boundary

`config/archive-cycle.json` binds this operational event to `oa-2026-09-08`,
OA-1, `CILE-4PT-OA-v3`, the preserved commit and an issue ceiling of 193. An issue
must be newer than that ceiling and created after the reset to appear in the
console or accept a decision. Old intake replay fails before writing. The
retired E0 materialiser cannot populate the active queue.

The first scheduled daily search is 9 September 2026, 07:00 Europe/Rome. Today's
pre-reset search is historical. The active daily projection starts on that first
scheduled date, keeps unknown measurements null, and represents every expected
date afterwards. Pre-reset ledger comments stay stored but cannot feed current
totals. A new invalid comment still fails validation. There is no implied daily
execution guarantee or automatic link revalidation.

## Retained rules

The controlled taxonomy, exclusion reasons, secondary collection definitions,
scientific ontology 0.3.0, four-part test, bibliographic model, source policies,
OA verification/publication gates and software remain. The operational cycle is
mapped onto existing ReviewEvent/protocol/snapshot concepts in the ontology;
no scientific category or decision value is introduced. The six proposed OA
seeds remain an external research proposal, not records in the new archive.

D1 authentication remains an infrastructure problem for private V2 activation.
It does not prevent resetting the current Git-backed archive, which is the
scope executed by this release. The existing daily task receives the same
cycle boundary; the personal broader AML digest keeps its separate scope.
