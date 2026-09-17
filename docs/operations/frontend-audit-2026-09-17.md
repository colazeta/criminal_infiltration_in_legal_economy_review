# Frontend audit and maintenance — 17 September 2026

## Scope and evidence

This is a presentation-only maintenance change requested by the repository owner. It preserves the 1990s desktop/archive visual language and the existing site, datasets, public endpoints and scientific gates. It does not create a parallel research interface.

The baseline is the published GitHub Pages artefact from successful run `35142697803`, commit `b354836311f0b058fc59318776d10ad5461ba70b`. The source-only placeholders in `index.html` and `stats.html` were restored and their Git blob hashes checked before editing. Other public pages were inspected for regressions. Authenticated operations were neither performed nor redesigned.

The published snapshot contains 292 provisional records, 141 records bearing the recorded `metadata_verified` state, 119 identity-matched public reading-aid synopses and zero records in the independently approved corpus. These are different populations. They are not an estimate of how much scientific enrichment has subsequently been completed in the Worker or in public annotations.

Live Pages navigation was unavailable in the audit environment. The downloaded release was therefore rendered with Chromium using locally fulfilled static resources. Live research API availability was not inferred from these tests. Deliberate API failures and an explicitly labelled excerpt of existing public annotation [issue 237, comment 5684504903](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/237#issuecomment-5684504903) exercised failure handling and the existing manual-support fallback.

## Findings and changes

| Priority | Finding | Implemented response |
|---|---|---|
| High | The headline “paper da analizzare” read the canonical editorial queue, not the displayed provisional register. | Name and derive register, metadata, synopsis and approved-corpus counts separately. Retain the canonical queue in labelled release information. |
| High | The register inherited non-wrapping table cells and exceeded its desktop container. | A fixed-width, wrapping table on desktop and stacked records on narrow screens; source values are not truncated. |
| High | Every filter rendered all 292 rows; the initial desktop document was about 29,000 pixels high. | Presentation-only pagination, 25/50/100 rows, explicit ranges and accessible navigation. Filtering still operates on the complete population. |
| High | Bibliographic diagnostics and verification caveats preceded the research content repeatedly. | Synopsis first; research next; bibliographic identity, access metadata, sources and completion diagnostics remain available in native expandable sections. |
| High | A failed research API request removed the preset sections needed by the existing manual annotation fallback. | Keep clearly unavailable, empty sections on failure so the existing identity-bound manual loader can populate them. Manual material remains explicitly unreviewed and does not attest completion. |
| Medium | The empty approved corpus and the provisional register competed as two primary search surfaces. | Make the register primary and retain the approved corpus, all original IDs and its controls inside a labelled disclosure. |
| Medium | Operational logs dominated the statistics page. | Keep literature and enrichment information before a collapsible operational audit; retain all charts, tables, source records and explicit pending-population selection. |
| Medium | A generic CSV link pointed to the approved corpus, which is empty in this release. | Label the register JSON and approved-corpus CSV/JSON separately; do not misrepresent one as the other. |
| Medium | Missing or malformed registry payloads could become a false empty population. | Check schema, record identity and required display fields; fail visibly rather than report a fabricated zero. |
| Medium | Modal header and close control scrolled away; focus could be lost after an asynchronous row refresh. | Sticky window bar, bounded responsive dialog, Escape/native modal behaviour, and stable-record focus restoration. |
| Medium | An added filter-change listener initially interrupted a title click when search lost focus. | Regression caught in the browser test and fixed before publication: only select changes trigger that handler. |
| Low | The skip link led to the secondary empty corpus, and the statistics navigation omitted Method. | Point the skip link at the register and restore Method in the statistics navigation. |
| Low | Historical reset notices and mixed administrative language occupied the first screen. | Keep historical/version information in the footer, clarify acquisition-time access labels and identify the dominant Italian body language. |

The colour system, square geometry, navy title bar, underlined links and system fonts are retained. No web font, framework, new stylesheet, tracking code or external service is introduced. Component rules are grouped in the existing application stylesheet; the legacy stylesheet stack has not been comprehensively rewritten.

## Verification

Six dependency-free regression tests are added in `tests/test_frontend_workspace.py`. They exercise the actual pagination helper in Node, prove that every record remains reachable without mutation or duplication, check collection/download boundaries and stylesheet inventory, and check changed JavaScript syntax.

Local command:

```sh
python -m unittest discover -s tests -p 'test_frontend_workspace.py' -v
```

Result before PR creation: **6/6 passed**.

A separate offline Chromium test passed **35 functional checks**: complete traversal of the 292-record population, page sizes, last-page boundaries, search, year and content filters, reset, DOI lookup, Enter without a page submission, real-paper synopsis, existing manual-annotation fallback under API failure, scientific-state warnings, modal scrolling, Escape and focus restoration, malformed/missing data, pending-population opt-in, and access to the collapsed operational audit. No uncaught JavaScript errors were observed in these scenarios.

At viewport widths 320, 390, 768, 1024, 1440 and 1920 pixels, the register and document fit their available width. At 1440 pixels the final initial register document is approximately 2,823 pixels tall, with 25 displayed records. The original full-list document was approximately 29,283 pixels. This measures rendered page length and DOM workload, **not** a network-speed improvement: the complete static registry and support dataset are still downloaded.

The test evidence includes before/after screenshots, structured results and the real-paper scenario for *The Economic Effects of Mafia: Firm Level Evidence*. Its manual annotation is used only to test rendering, not to re-evaluate its scientific claims.

## Integrity and release boundary

No registry, annotation, manuscript, metadata value, classification, eligibility decision, completion receipt, full text, access decision, export, schema, ontology, Worker, secret or workflow is changed. Public projections continue to use their existing identity checks and `textContent` rendering. Unknown, unavailable, proposed and approved states remain distinct. No archive-version increment is warranted for this presentation-only maintenance.

The repository-wide quality workflow must succeed before merging. This local audit is not a substitute for that workflow or for confirmation of the subsequent main-branch deployment.

## Remaining work, explicitly not certified here

Cross-browser rendering on Firefox/WebKit, physical touchscreen behaviour, screen-reader review and live authenticated curator flows were not certified. The CSS stack still contains legacy overlap outside the revised components. Full-text research delivery and valid positive completion receipts need a live service smoke test; the present audit does not claim that all enrichment is complete. URL-persisted search/filter state and a shared navigation template remain useful later improvements. Operational scheduling text outside the revised HTML should be reconciled with its governing workflow in a separate operations change, rather than changing schedules during a visual cleanup.
