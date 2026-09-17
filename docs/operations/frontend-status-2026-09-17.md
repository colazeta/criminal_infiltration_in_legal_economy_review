# Clear loading and research states — 17 September 2026

Owner-requested maintenance after #767 and #768. Baseline: main `094496b53d19c34df364dfeab3ed19227250052a`, Pages artifact `10515416930`. The downloaded release has 292 provisional records, 119 public synopses and no independently approved corpus records. These are static populations, not an estimate of enrichment progress.

## Defects corrected

1. The register reported zero completions and other zero counts before fetching analytical data. The display now has distinct idle, loading, failed, partial, ready and empty states. Unknown counts are null/hidden, not zero.
2. Register and enrichment statistics used separate verbose descriptions of the same loading process. They now share the read-only `analysisSummary` presentation helper. Partial counts explicitly name their loaded denominator; an overall percentage requires a complete successful read.
3. Content filters could report zero matching records while their data were still loading. They now expose loading/failure/partial status instead of a false empty result.
4. A missing completion response in a paper sheet was presented as a negative completion finding. Missing data now read “Stato del completamento non disponibile”; an actual negative receipt reads “Completamento non registrato”. The accepted current-revision receipt predicate is unchanged.
5. Empty research sections repeated the same boilerplate. Their existing placeholders remain available to the manual-support loader but are hidden until populated. Current structured research is not overwritten by the manual fallback. Manual annotations remain explicitly unreviewed and cannot certify completion.
6. Category metrics retained previous values during failed refreshes. They are now cleared before loading/error rendering. Category counts check the selected bibliography against the public candidate snapshot. Missing/mismatched, stale and withheld rows do not create an overall coverage percentage.
7. Geographic read failures were counted as checked records. The loaded count now excludes request errors; failed/unloaded geography does not yield a zero-country result.
8. Bibliometric loading/failure is propagated to its dependent panels, not treated as an empty selected population. Malformed payloads fail rather than silently becoming empty arrays.
9. “Pending” wording confused scientific review with analytical work. The option now names records awaiting scientific assessment, which may already have summaries or analysis.
10. The private enrichment reading surface contained static claims about disabled scientific extraction and scheduling rather than current recorded work. Its copy now describes the data being displayed without asserting research progress or changing any backend operation.

## Public explanations

`site/method.html#reading-status` is the shared explanation of synopsis, detailed analysis, proposed category, recorded completion and independent scientific inclusion. The register has one short operational explanation: loading reads already registered data; it does not start analysis. Scientific warnings and source provenance remain accessible. Original source bodies, private notes and access rights are unchanged.

## Verification completed before PR creation

- `node --check` passed for every JavaScript asset in the local site copy.
- `node --test curator-app/test/frontend-status.test.js`: 17 tests passed. Fixtures are synthetic software cases, not research evidence.
- 34 offline Chromium DOM assertions passed, including the actual 292-record/119-synopsis static baseline, delayed loading, failed requests, partial index coverage, successful observed zeroes, retry after success, empty-sheet handling, category/geography failures and responsive widths 320/390/768/1440. No uncaught browser errors in the tested scenarios.
- All uploaded production and new-test blob hashes match the locally tested bytes.
- Generated index/statistics previews were restored to source-only placeholders and checked against main before editing; no generated data are committed.

The browser environment blocks URL navigation by policy. That policy was not changed: tests used in-memory HTML/CSS, preloaded child modules and deliberately mocked analytical responses. They test DOM and source logic, not live API progress, physical devices, Firefox/WebKit, screen readers or authenticated curator sessions. Full repository CI and subsequent main deployment remain mandatory.

## Integrity and scope

Changed production files: `site/paper-register.js`, `site/enrichment-statistics.js`, `site/paper-sheet-research.js`, `site/paper-sheet-manual.js`, `site/categorisation-statistics.js`, `site/geography-statistics.js`, `site/bibliometrics.js`, `site/enrichment.js`, `site/enrichment.html`, `site/index.html`, `site/stats.html`, `site/method.html`.

No bibliography, registered research, classification, citation edge, completion receipt, scientific decision, publication manifest, access status, schema, ontology, Worker implementation or workflow changes. No bibliographic retrieval, model calls, new service, scheduler, dependency or persistent store. No missing human decision is supplied by this maintenance. Existing identity/revision, confidentiality and acceptance tests must remain in force; wording and asset-version assertions should follow the revised interface rather than require the removed misleading text.
