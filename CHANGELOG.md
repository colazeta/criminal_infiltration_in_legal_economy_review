## 2026-09-11 — private paper enrichment foundation

* Add ontology profile 0.4.0, 15 empty additive private tables and closed scientific
  extraction schema with field-by-field semantic mapping.
* Add independently gated hourly mechanical enrichment, leases, retries, private
  source readback and resumable provider-specific citation coverage.
* Add authenticated source/proposal import and inspection; preserve all scientific
  approvals, registry records and original migration hashes.
* Add clinical contribution codebook 1.0.0, prompt, calibration requirements and
  explicit machine-extraction block. No model or calibration is manufactured.

# Changelog

All notable archive, protocol and schema changes are recorded here. Versions
follow semantic versioning while the project is in prerelease.

## [0.3.0] - 2026-09-08

- Owner-authorised reset of the active archive and candidate queue to zero under OA-1.
- Previous registries, decisions, coverage and reading aids preserved byte-for-byte in a retired snapshot and a dedicated Git branch.
- Legacy issue and intake replay blocked; daily statistics begin with the first scheduled run on 2026-09-09.
- No seed, eligibility decision or V2 database activation is included.

## Unreleased

### Changed — Exa-limit continuity fallback, 2026-09-09

- Protocol 1.2 / CILE-DAILY-v5 keeps Exa as the primary living-surveillance provider and authorises Parallel Search only after a documented Exa credit, quota, rate or provider-cap limit.
- Fallback is a clean W1–W7 restart. Final batch counts and intake use one provider only, preventing mixed-provider yield statistics; the incomplete Exa attempt remains diagnostic provenance and is never a zero-result search.
- Consensus remains retired; eligibility, canonical identity, publication gates, formal E1–E3 expansion and saturation rules are unchanged. Existing records require no reassessment.

### Fixed — OA intake enforcement, 2026-09-08

- Require a structured OA-1 attestation in both v2 intake import and ledger reconciliation; missing, restricted, cross-candidate or incomplete evidence fails closed.
- Preserve original intake access receipts and the issue-body hash in metadata-only curation snapshots; validate coverage against the active daily queue.
- Reuse existing ontology concepts and keep legacy v1 decoding unchanged. No seed, scientific decision or private V2 activation is included.
- Clarify that the active archive reset completed in 0.3.0 while private V2 activation remains separate.

### Changed — 2026-09-08

- Owner-requested removal of Consensus from discovery, daily intake and V2 runner readiness. Exa is the sole daily source for W1–W7.
- Version 2 run/intake contracts and CILE-DAILY-v3; historical v1 telemetry retains original provenance and outcomes.
- OA calendar expectations use one source and seven baseline queries, with partial query execution and missing days visible.
- Bibliographic agreement UI uses “Concordanza bibliografica” to distinguish metadata reconciliation from the retired provider.
- OA-1, CILE-4PT-OA-v3, ontology 0.3.0 and all scientific approval gates remain unchanged. No seeds or decisions are imported.

### Added

- Italian quick guide and a plain-language curator portal;
- authenticated curator workflow for topic changes, exclusions and confirmed
  duplicate merges;
- Work surveillance contract using the active Consensus + Exa connector pair,
  with Scite's current account limitation recorded explicitly;
- guarded GitHub intake lane added to the existing Daily AML & CI Research Work
  automation without consuming another scheduled-task slot;
- append-only work-relation registry and curator-operation tests;
- controlled exclusion-reason registry and versioned topic-coding history;
- separate plain-language and technical literature-expansion guides;
- aggregate daily-surveillance ledger, closed telemetry schemas and a public
  statistics page with source-completeness guardrails;
- isolated on-site candidate browser and decision form backed by a
  least-privilege GitHub App, OAuth PKCE, atomic submission coordination and an
  attributed issue-to-PR workflow.
- separate broader AML and economic/financial-crime collection with an
  independent publication gate for scholarly works that remain `not_eligible`
  for the criminal-infiltration review.

### Changed

- simplified the repository index, public-site methodology and search-strategy
  wording;
- extended validation to curator actions, work relations and every workflow;
- repaired malformed historical screening and execution-metric rows; row-width
  and header defects are now validation failures;
- removed direct raw-registry access from the public curator page and expanded
  every generated or manually opened curator PR with the complete audit record;
- separated daily discovery statistics from formal E1–E3 saturation metrics and
  scheduled a fail-closed Pages refresh from ledger issue #30;
- changed materialised queue issues to open their candidate directly in the
  curator workspace while retaining the GitHub issue form as a fallback.
- made candidate screening record an optional governed `broader_aml`
  destination and distinct relevance rationale without changing core decisions,
  review counts or saturation.

## [0.2.0] - 2026-08-30

### Added

- searchable public archive and deterministic JSON/CSV exports;
- explicit publication manifest and closed public-field allowlist;
- work-to-identifier mapping, controlled taxonomy and archive version registry;
- cycle-grouped saturation reporting and negative gate tests;
- Scite + Exa academic intake policy with GitHub issue-only writes;
- plain-language repository index and GitHub Pages publication guide;
- calibrated, multi-source literature expansion strategy with explicit
  workstreams, citation chasing and coverage-gap metrics;
- citation, contribution, release and PRISMA-oriented reporting metadata.

### Changed

- reconciled seed bibliographic metadata and identifier manifestations;
- migrated unresolved seed screening and publication states into append-only,
  governed histories;
- set the current public archive to empty until independent human publication
  approval is recorded;
- public cards now read only governed registries;
- public empty-state copy now distinguishes a governed empty corpus from filter results;
- build/deploy checks are pinned, cancel superseded runs and fail closed.

### Removed

- Symphony/Linear setup, smoke-test forms and transient next-action files;
- placeholder/check-wrapper scripts and the disabled unsafe E0 retrieval script;
- noisy raw E0 snapshots and duplicated execution logs from the active tree.

## [0.1.0] - 2026-04-29

- Initial governance scaffold and preliminary E0/E0R1 pilot.

[0.2.0]: https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/releases/tag/v0.2.0
[0.1.0]: https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/tree/9d3210652cc943c514969f245cce754f22e2c3a4
