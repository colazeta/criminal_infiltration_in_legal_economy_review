# GitHub reliability audit — 27 September 2026

Baseline: `83fd6e937a708c7d1e877f2802b54300ceff2a4f`. This is an engineering
audit and recovery, not a scientific acceptance or an identity decision.

## Findings and corrections

| Cause | Evidence | Resolution |
|---|---|---|
| Statistics and heartbeat fail on malformed terminal text | Actions run `36329351189`, deploy job `108648708151`: `run.notes: invalid text value`; heartbeat `36318076656` | Audited all 138 ledger comments; isolated the three additional invalid active-cycle terminals below. All other validation remains mandatory. |
| A terminal was edited after submission | Comment `5790164542`, created 23 September 06:28:13 UTC, updated 12:10:55 UTC | Exact ID/batch/body-hash quarantine. No replacement history or counts are invented. |
| An approved DOI update destroys earlier retrieval evidence | Retrieval run `36313023827`: the refreshed Mafias and Firms row lost its previously verified full text and identity evidence | Preserve evidence for the same candidate/title when the recorded queue DOI equals the previously resolved DOI; reject different candidate/title/DOI and conflicting provider identifiers. |
| Tests freeze transient URLs/statuses | The same run fails on `source_link_only`/`landing_page` versus `unresolved`, and an alternative institutional PDF locator | Test the intended evidence boundary: abstract-only records cannot become full-text records; the exact original full-text locator remains in provenance while the primary URL may change. |
| Support branches cannot become PRs | Abstract run `36313695479`, job `108604298495`: GitHub Actions is not permitted to create or approve pull requests | Recover the already validated `d8d47f8f01f268219e7259a63051646de3b67d55` checkpoint in this maintenance change. The repository setting still requires owner action; a clearer diagnostic identifies it. |
| A dispatched replacement check immediately sees its old failed check | `persist_selected_support.sh` reads the old latest check before the asynchronous rerun starts | Ignore the snapshot of pre-existing check IDs after dispatch and wait for a new exact-head check. A new failed check still blocks merge. Paginate the check inventory. |
| One recovery starts two Pages builds | Consecutive `workflow_dispatch`/`workflow_run` archive runs after recovery, including `36329345632` and `36329351189` | Keep recovery's explicit post-readback dispatch; remove its duplicate `workflow_run` subscription. The support-workflow subscriptions remain. |

## Ledger quarantine

The original comments remain in issue #30. The three new exceptions pin their
exact UTF-8 SHA-256 body; changing the body fails closed and requires another
audit. The regression fixtures reproduce the observed defects.

| Comment | Batch | Defect |
|---|---|---|
| `5739910343` | `ACADEMIC-2026-09-19` | Note exceeds the 280-character bound |
| `5784336676` | `ACADEMIC-2026-09-22-EXTRA-ce155a5f6d3d` | Source limitation exceeds 180 characters; a note also exceeds 280 |
| `5790164542` | `ACADEMIC-2026-09-23` | Edited terminal violates immutable timestamp contract |

Each declares zero intake candidates and no intake issue. Quarantine loses no
CandidateRecord; these three runs contribute no accepted metrics until a
separately evidenced recovery is reviewed. Missing calendar days remain unknown,
not zero-result searches. The remaining 93 active terminal bodies and timestamps
pass local validation. Remote ancestry, author, intake uniqueness and source
validation remain the deployment reader's responsibility.

Before a future terminal write, materialise the exact prospective body and run:

```bash
python3 scripts/metrics/validate_terminal.py \
  --body /path/to/prospective-terminal.md \
  --expected-batch ACADEMIC-YYYY-MM-DD
```

This is a read-only preflight, not a persistence receipt. Reconcile remote
idempotency immediately before writing, read back afterwards and never edit a
terminal. Recover an invalid terminal through the existing evidence-pinned
maintenance procedure. Diagnostic exceptions now identify the offending comment.

## Recovered support checkpoint

The 27 September abstract backfill had already completed mandatory validation
before pushing `automation/selected-support-068d54540a45debf9315`; PR creation
then failed. Its exact retained commit is applied without repeating retrieval.
It changes only `abstract_coverage.csv`: 149 observation rows, including four
`needs_web_search` → `available` transitions and no reverse transitions.
Available abstract metadata increases from 175 to 179 of 294 registered
candidates. This does not mean that four scientific assessments are complete.

## Remaining repository setting

The owner must enable **Settings → Actions → General → Workflow permissions →
Allow GitHub Actions to create and approve pull requests**. The current GitHub
connector cannot change repository administration settings. Do not replace
this blocked permission with a direct-main push, a stronger credential or a
weakened review gate. Existing per-job permissions, expected-head checks and
scientific approval boundaries remain in force.

Reference: [GitHub's repository Actions settings documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository#preventing-github-actions-from-creating-or-approving-pull-requests).

## Stalled pull requests and scientific delivery

| PRs | Audit disposition |
|---|---|
| #359 | All 22 proposed quarantine entries are already in main. Superseded; merging the old implementation is unnecessary. |
| #227 | Its apt installation step no longer exists in the intake workflow, which now defers to terminal-driven recovery. Superseded. |
| #765 | Native-runtime diagnostic work; current deployed observer succeeds. Its historical outage is not evidence of a current storage outage. Reconcile remaining test improvements separately. |
| #769, #773 | Some frontend behaviour has reached main through other changes; remaining differences need reconciliation against the current interface. Do not blindly merge stale branches. |
| #797, #808 | Substantial, overlapping archive/document migrations. Both introduce a `0009` migration for different purposes; they require a combined migration and compatibility plan, backup and readback, not an automatic blanket merge. |
| #779 | Observe-only Kora pilot. It must remain observe-only until current single-worker contracts and native evidence are reconciled. No additional scheduler is created by this audit. |
| #223 | Scope/methodology proposal; independent of the transport failures. Not merged as an infrastructure fix. |
| #23–#27 | Major Actions dependency updates. Deprecation warnings do not explain the observed failures. Review as a separate compatible set after recovery. |

The latest observed private service check (`36336445148`) reports 294 targets,
197 sources, 3,378 citation observations, two structured proposals, one document,
two bibliography snapshots, zero calibration receipts and zero adjudication
receipts. Its public projection check succeeds. These are distinct stages;
healthy GitHub jobs do not establish scientific completion. The engineering
priority after this recovery is to advance the existing source-grounded proposals
through their next executable assessment gates, with persistence and readback.

## Validation

The mandatory `AGENTS.md` build/ontology/repository/publication checks and Python
and Node suites run on the complete recovery change: 785 Python tests and 411
Node tests pass, with no skipped tests. Targeted tests reproduce
the invalid terminal bounds, immutable timestamp rule, altered quarantined
bodies, DOI-promotion regression and asynchronous replacement-check sequence.
Candidate IDs, canonical works, scientific decisions, ontology profile and
publication approvals are unchanged. No bibliographic search was performed;
GitHub records/logs and the already retained support checkpoint are the evidence.


## Post-merge runtime follow-up

PR #823 passed remote quality and was merged as
`b574e9c1118fcf7aa48d0c989885811dd912e2d7`. The subsequent full retrieval refresh
(`36342425970`) exposed one further historical test assumption: the CEPR reading
aid's `abstract_only` basis was incorrectly treated as a permanent prohibition
on an independent provider finding a full-text locator. The follow-up keeps the
reading aid and its evidence basis unchanged, requires separate provider provenance
for a later full-text locator and verifies that the abstract bridge neither
promotes an abstract nor erases independently obtained full text. No retrieval
record or scientific decision is changed by this test correction.

The same post-merge deployment (`36342425967`) successfully fetched all 93 runs,
including remote ancestry, author, intake and source checks. Its build exposed
two frontend tests that loaded the generated publication data and assumed it was
always empty. They now use a deterministic empty fixture and continue to test
both empty and populated states. The full Node suite is also exercised against
an artifact built from the 93 validated runs, matching the deployment path.

Follow-up validation passes 786 Python tests and 411 Node tests, with zero skips.
The populated artifact also passes all 411 Node tests, archive/site validation
and selected-paper consistency checks. Its public projection contains nine
completed scheduled days through 22 September and 76 extra runs; other ledger
entries are not silently converted to successful public iterations. The later
calendar gaps remain unknown. All 294 candidate identities and both support
coverage tables remain complete.
