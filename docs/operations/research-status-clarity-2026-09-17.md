# Research status and loading clarity — 17 September 2026

Owner-requested maintenance following #767 and #768. Baseline: main commit
`094496b53d19c34df364dfeab3ed19227250052a`, published Pages artifact `10515416930`.

## Findings

The register displayed initial zero counters for research data it had not yet
requested. Its summary check was a browser read/identity check, not scientific
verification. Similar ambiguities affected aggregate enrichment, classification,
geography, individual sheets, bibliometrics and private-console messages.

The current `completion-first-v5.md` and `two-lane-delivery.md` distinguish
assessment completion (F0–F5) from final validation. The existing public index's
legacy `completed` receipt still means accepted validation. This maintenance
labels that value accurately; it does not fabricate or infer an F5 count or
change the public/private data contract. The old filter parameter is preserved
for compatible saved links but labelled as recorded final validation.

## Changes

- A shared read-only overview distinguishes not requested, loading, complete,
  partial, failed and empty-population states. Aggregate research counters are
  unavailable until a complete successful read. Genuine measured zeros remain
  visible. A refresh immediately removes previous totals; failure never leaves
  stale totals presented as current.
- Summary availability remains independent of analytical loading. Statistics
  no longer pretend to verify summaries they did not load.
- Technical loading counts are in closed diagnostics explicitly labelled as
  page loading, not research progress. Primary controls say load/reload, not
  analyse or scientifically verify.
- Individual paper sheets distinguish unavailable validation information,
  unrecorded validation, old-version records and recorded validation. Assessment
  completion is explicitly unavailable from this public projection. Existing
  source, identity, privacy, receipt and delayed-response checks remain intact.
- Classification and geography separate successful reads from failed/missing
  entries. Percentages identify their actual readable denominator; partial
  populations are explicit. Unread charts and previous failed-refresh totals
  are not displayed as zero results.
- Pending scientific screening is no longer described as a paper not yet
  analysed. Malformed bibliometric arrays fail visibly instead of becoming an
  empty corpus. Operational statistics clear stale KPIs after failed loading.
- Private entrypoints use unknown rather than zero for missing fields and do
  not claim that extraction never ran merely because no proposal was returned.
  No authenticated action was performed and no authentication/write contract
  was modified.
- The methodology page provides a concise glossary of summaries, consultable
  analyses, assessment completion, validation and scientific inclusion. Its
  source/cadence copy is aligned with the already-authorised current mandate;
  this change does not alter any schedule or source configuration.
- Static register fallback copy uses the same scientific-screening distinction.

## Verification before PR

- `node --check` passed for all site JavaScript files.
- `node --test curator-app/test/research-status-clarity.test.js`: 23/23 passed.
- Python compilation and static fallback rendering passed, retaining all 292
  registered identities.
- 39 Chromium DOM checks passed with no uncaught JavaScript errors. Scenarios:
  independent synopsis availability; initial, partial, failed and complete
  analytical reads; real zeros; failed refresh clearing; filter uncertainty;
  enrichment, categorisation and geography states; individual validation
  messages; malformed bibliometrics; operational KPI reset; and widths
  320, 390, 768, 1024, 1440 and 1920 pixels.

The browser environment blocks URL navigation by policy. That policy was not
changed. Tests rendered the actual local HTML/CSS/JavaScript in memory, preloaded
child modules and supplied controlled software-only fetch responses. The
292-record bibliographic baseline was real; synthetic analytical responses are
software fixtures, not research/calibration evidence. These checks do not certify
live browser navigation, authenticated curator flows, other browser engines or
screen readers. Main-branch CI/deployment checks are required separately.

## Integrity boundary

No registry, bibliography, source document, research extraction, classification,
scientific decision, completion/validation receipt, schema, ontology, API or
workflow is changed. No bibliographic retrieval, provider call, new persistence
store, tracking, dependency or scheduler was introduced. Public F5 assessment
completion requires a separately governed projection migration and remains
unavailable rather than guessed. Historical audit notes remain historical.

Repository-wide CI must pass before merge, including all existing semantic and
security assertions. Existing tests tied to obsolete user-facing wording or
cache keys must be aligned with the corrected display without dropping source,
identity, unknown-state or validation checks. Verify the subsequent main release
and served candidate identities, and compare the published assets and unchanged
data with the tested baseline.
