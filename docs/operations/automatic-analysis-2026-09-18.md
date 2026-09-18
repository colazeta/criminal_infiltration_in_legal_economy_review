# Automatic analysis loading and navigation — 18 September 2026

Owner-requested presentation maintenance. Baseline: `da554933d5b76b318d05b4f024764712056da44d`, published Pages artifact `10523040267`. The baseline contains 292 provisional records and 119 reading-aid synopses, independently of analytical completion. No scientific record or decision changes.

## Behaviour

- The archive starts one bounded public-index scan on mounting. No click or analytical filter is required. The existing page cursor, revision checks, identity checks, timeouts and single-flight guard remain in place.
- Synopsis and analysis requests start independently. A slow synopsis dataset no longer prevents the public analysis index from loading. Missing synopsis data cannot imply missing analysis.
- Statistics already started their initial read automatically. The redundant success-state refresh button is now hidden, and statistics no longer download the unused synopsis dataset.
- Retry controls appear only after an incomplete or failed read. Filter/reset actions never start a duplicate scan or an implicit retry loop. Empty registries do not open unnecessary remote requests.
- Loading still takes network time. No false immediate value is invented; unknown counts remain hidden, partial counts retain their denominator, and observed zeroes remain zeroes.
- The AML tab is removed from all eight HTML menus and the Method footer. Historical AML routes, exports, records, screening choices and scientific-publication boundaries remain intact. This is tab removal, not data deletion or reclassification.
- Entry bundle versions are updated, and the Method explanation describes automatic reading.

## Validation

Local commands:

```sh
node --check site/paper-register.js
node --check site/enrichment-statistics.js
node --test curator-app/test/automatic-analysis.test.js
git diff --check
```

All passed. The 13 new regression tests cover automatic loading, independent slow synopsis reads, no duplicate requests, retry behaviour, all 292 synthetic index rows in six bounded requests, empty registries, statistics without unused synopsis requests, observed zeroes, partial denominators and navigation/data preservation. Two existing UI expectations are updated from idle/manual loading to automatic loading; all identity, source, completion and error assertions remain.

A separate Chromium exercise passed 16 in-memory DOM checks using the actual changed modules and explicit synthetic responses: request initiation without interaction, no initial gate, delayed response, working analytical filters without duplicate requests, statistics loading, AML navigation removal and widths 320/390/768/1440. No uncaught errors were observed. Browser navigation is blocked by policy in the audit environment; the exercise is not a live API, real navigation, cross-browser or authenticated-session certification. The policy was not bypassed.

The source index/statistics templates were restored from the baseline release and checked against their main-branch Git blob hashes before editing. All changed production files and the new test match their uploaded blob hashes. Full repository validation is delegated to the existing PR CI and must pass before merge. Afterwards, verify actual Pages deployment and served candidate identities separately from the existing operational-metrics failure.

## Integrity and remaining boundary

No bibliography retrieval, model execution, backend code, credential, new service, dependency, storage, scheduler, workflow, schema or ontology change. No missing human scientific decision is supplied. This maintenance does not repair the separate research-statistics ledger validation error or turn provisional analytical content into accepted research. The approved-corpus default in bibliometrics is unchanged.
