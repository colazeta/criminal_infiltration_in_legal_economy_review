# Runtime publication follow-up — 13 September 2026

PR #489 passed 521 Python and 150 Node tests and was merged at 042f93a.
The actual recovery run 34750246911 then persisted intake #496 on main at
b40154fded470828a7f72a806e3af808c310e6e4 and read back 243 identities,
including the one newly materialised candidate. This is persistence, not yet
proof of served publication.

The complete release in archive run 34750220034 exposed two remaining issues:

- Static candidate HTML was rendered only during deployment. Original HTTP
  source locators (including http://cepr.org/publications/dp12140) became clickable
  anchors, failing the existing HTTPS-only site gate. The renderer now preserves
  such source locators as escaped visible text, never rewrites them to unverified
  HTTPS, and leaves bibliographic JSON and provenance unchanged. HTTPS locators
  remain clickable. A regression test renders the entire actual register, not
  just the JSON export or a synthetic single record.
- Ledger comment 5647980951 is an intermediate byte-identical copy of the
  original #341 terminal 5642209455. The original and intermediate copy have
  exactly the same structured payload. The already-authorised replacement
  5652046564 preserves every numeric, identity, provenance, timing and disposition
  field, shortening only notes and limitations. The intermediate copy also must
  be excluded by its exact ID and batch. Both historical source comments remain
  immutable. Unknown duplicate batches still fail; there is no blanket dedupe.

This makes intake #341 eligible for the existing mechanical recovery checks,
not automatic scientific inclusion. The previously diagnosed missing completed
terminal for #225 is unaffected and must not be fabricated. Six regression tests
cover full real-register HTML rendering, unchanged HTTP provenance, escaping,
unsafe locator rejection and exact-ID-only terminal reconciliation.
