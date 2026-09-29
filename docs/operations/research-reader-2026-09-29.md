# Continuous reading in the public register

This maintenance extends the [existing navigation contract](frontend-navigation-2026-09-17.md)
and preserves the [classic interface](classic-site-ui.md). It changes presentation,
not CandidateRecord identity, research projections, completion or publication gates.

## Finding and reading papers

- Search requires every whitespace-separated word, in any order across the recorded
  title, authors, venue, DOI, year, candidate ID and existing topic code. Case,
  diacritics and curly/straight apostrophes are normalised for matching only.
  Recorded metadata are never rewritten. The search field remains bounded to the
  600-character URL contract.
- Quick views select the existing governed content filter. Other filters stay
  active. Each active filter is visible outside the advanced drawer and can be
  removed independently. Data refreshes retain unchanged controls and keyboard focus.
- Previous/next paper follows the current filtered, sorted result set across page
  boundaries. It never wraps, performs identity guessing or opens a record outside
  that result set. A valid direct link outside current filters remains readable,
  with both navigation buttons disabled and an explicit explanation.
- Reading successive papers replaces the single sheet history entry. Close or
  browser Back returns to the results and reveals the last-read record when it
  still matches; Forward restores the selected sheet. Closing a direct arrival
  removes the paper parameter without leaving the site. Saved paper links remain
  independent of the current filters.
- A contents index exposes only sections already rendered in the public sheet.
  Desktop uses a sidebar; narrow layouts use a native section selector. A section
  action opens the disclosure, scrolls to it and places keyboard focus there.
  Asynchronous support/research arrivals refresh the index only for the current
  sheet. Hidden placeholders are excluded. Every section keeps a unique ID.
- Existing proposal, source, missingness, access, completion and scientific-review
  labels are retained in the content itself. Section navigation is not an assertion
  that content is present, accepted, complete or reusable. No private data request,
  additional research store or additional fetch is introduced by the reader.
- Print omits navigation and retains the existing disclosure expansion/restoration.
  On screen the window has a stable viewport-bound height: asynchronous sections
  cannot move the previous/next/close controls by re-centring a growing dialog.
  Print retains automatic height.

## Delivery and regression checks

`workspace.js` owns the read-only search and navigation controls. `paper-register.js`
provides the current records, filtered order and return-to-result focus. Layout uses
the existing `application.css`; no additional stylesheet or framework is required.

`research-reader.test.js` exercises event order in a DOM/history test double:
filtered order, boundary cases, direct links, Back/Forward, cross-page return,
independent filter removal, keyboard focus and asynchronous section IDs. Existing
public-sheet tests still guard identity mismatches, stale responses and read errors.

The existing post-deployment register verifier now also compares the exact served
bytes of `workspace.js`, `application.css` and `classic-site.css`. Its durable
receipt includes their SHA-256 hashes. A current data file with stale navigation or
layout is no longer sufficient evidence of successful delivery.

No ontology amendment is required: there are no new governed fields or scientific
states. Candidate, source, document, annotation, extraction, completion, validation
and corpus populations are unchanged by this maintenance.
