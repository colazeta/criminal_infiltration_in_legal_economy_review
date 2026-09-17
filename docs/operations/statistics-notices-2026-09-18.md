# Research statistics: publication and loading notices

Owner-requested maintenance following PR #770. This change concerns the public communication of research statistics, not ledger repair or scientific completion.

## Behaviour

- One scoped notice separates initial/loading, unavailable publication, request/format/timeout failure, successfully loaded empty data, stale published data and available data.
- The collapsed research section names its current state. A publication failure is rendered in static HTML; hidden counters are not presented as five unexplained dashes.
- A withheld release retains the existing removal of `stats.js`: an empty deterministic fallback cannot overwrite the publication warning. There is no fake retry action for a release-level problem.
- The browser has a 12-second read timeout, one in-flight request, a real retry button and complete clearing of previous research charts and counters before retry/failure. It neither sends credentials nor starts research.
- The publication date and the last published research date remain distinct. Neither missing telemetry nor an old snapshot proves that research has stopped.
- Public charts/tables use completed records only; failure codes and missing-day operational diagnostics are not rendered. Ordinary-series indicators explicitly exclude extraordinary runs, which retain their own table and the combined iteration chart.
- The former calendar source-completion percentage is replaced by the existing count of completed ordinary runs, consistent with the public completed-only scope. Canonical metrics, definitions and JSON are unchanged.

## Verification

Local source baseline: the served release for `faa811d9aa20f4330cf48cf37738eb0707b654e4`; its deployment-only warning was reversed before editing. Restored `site/stats.html` matches the repository blob `56d9c5f732ad2fd1f2f9aa7fdbd1043fc5136ef8`.

- `node --check site/stats.js`: passed.
- `node --test curator-app/test/statistics-notice.test.js curator-app/test/stats-freshness.test.js`: 17 passed.
- `python -m unittest discover -s tests -p 'test_statistics_notice.py'`: 8 passed.
- Offline Chromium: static unavailable state at 320, 390, 768 and 1280 px; no page overflow; no visible counters or misleading retry. Loading -> observed zero -> failed refresh -> successful retry passed with synthetic responses.
- Tests preserve the JSON bytes and reject marking a nonempty series as unavailable. Existing minimal release-marker fixtures remain supported.

Browser testing embeds actual local release assets and prevents external requests. Synthetic transition fixtures are software tests, not research observations. It does not certify live API availability, cross-browser behaviour or the correction of the ledger. Full repository CI and main release verification are required separately.

## Boundaries

No candidate, source evidence, extraction, classification, scientific decision, schema, ontology, provider, schedule or workflow is changed. No new service or dependency. Existing canonical validation, quarantine and publication gates remain in force. The reported ledger validation problem is not bypassed or silently repaired by this maintenance.
