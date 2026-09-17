# Archive navigation and paper sharing — 17 September 2026

Maintenance follow-up to #767, authorised by the owner. The existing visual language, public projections, scientific gates and source datasets are unchanged.

## Delivered behaviour

- Search, filters, order, page size and requested page are encoded in bounded URL parameters. Reloading or bookmarking the URL can restore the view; unavailable filter values are visibly reported rather than substituted silently.
- Browser Back/Forward restores the view and opens/closes the correct paper sheet. Opening a sheet creates one navigation entry; typing does not create an entry per key. Closing a direct arrival does not navigate away from the archive.
- A paper has a project-relative direct link containing only its registered public identifier. Unknown IDs are never fetched or matched heuristically to another record. The full existing identity checks still protect all enriched content.
- Copy-link and copy-reference controls operate only on public, already registered fields. References preserve the supplied values without inventing initials, pages, publication types or missing data. Clipboard denial exposes selectable text and does not report false success.
- Printing isolates the current public sheet and temporarily expands its existing sections. After printing, section state is restored. This does not fetch additional source text or confer public rights on a private PDF.
- Hash links reveal collapsed sections, including the reviewed corpus and operational statistics. Method is present in the remaining AML, model and public curator menus.

The URL is the only new persistence surface. No cookies, local/session storage, tracking, dependency, scheduler, database or backend write is introduced. Shared links strip unrelated parameters; the existing page shell and project-path routing are preserved. `workspace.js` is presentation logic, not a new semantic contract.

## Files and checks

Production changes: `site/workspace.js`, `site/paper-register.js`, `site/application.css`, and the entry/navigation HTML for index, statistics, AML, model and public curator.

Nine regression tests in `curator-app/test/workspace-navigation.test.js` cover state round-trips, Unicode, repeated/invalid/oversized values, project paths, clean shared URLs, raw bibliography, read-only scope and script/navigation integration.

Local commands:

```sh
node --check site/workspace.js
node --check site/paper-register.js
node --test curator-app/test/workspace-navigation.test.js
```

A separate Chromium DOM exercise passed 44 assertions using the actual static assets and all 292 records from release `23ad27e94da8e375ed8675db2d5f70589c45f857`. It covered restored views, forward/back events, direct arrivals, unknown IDs, successful/denied copying, print layout/state, async synopsis filtering and six viewport widths (320–1920 px). No uncaught errors were observed. No source record was changed.

Important limitation: the audit browser blocks URL navigation by policy. That policy was not changed. HTML/CSS/JavaScript were rendered in memory; History and Clipboard responses were simulated, and existing child modules were preloaded rather than fetched through dynamic imports. This is a real DOM and source-logic test, not certification of live navigation, real clipboard permissions, physical printing, all browsers or authenticated curator operations. External research requests were deliberately unavailable. Existing release CI remains responsible for full repository tests, deterministic data and served candidate checks.

The source-only index/statistics placeholders were restored from the previous release and checked against their main-branch Git blob hashes before modification. The repository-wide workflows must pass before merge; main deployment must be checked afterwards. No scientific decision, schema, ontology, access state, manuscript, private data or workflow is changed.
