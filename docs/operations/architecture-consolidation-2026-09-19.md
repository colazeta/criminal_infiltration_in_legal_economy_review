# Architecture consolidation — controlled implementation record

Status: **in progress; no cutover declared**. This work is governed by the owner's
19 September 2026 instruction to consolidate the conceptual, logical, physical,
write and publication layers. A successful UI export is not completion.

## Verified starting point

- Repository baseline: `63b15f80b4c19e4fcab0ca83f17ead7fca61d690`.
- PR #773 is open at `9573e83149a53bebd711583e8ba7de5141e9f719`.
  Its later reading-snapshot additions are not a deployed database migration.
  Do not copy its older data files over current main.
- Current baseline has 294 CandidateRecords, four 294-row candidate/coverage
  registries, no canonical works, no screening decisions and no publication rows.
- Authenticated observer run [35437517165](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/actions/runs/35437517165),
  at 10:28 UTC, reports Worker commit
  `bfff9713f94ae28cacba0c0bea7be477fe2c57d1`, 294 active targets, 108 sources,
  two proposals, zero adjudication receipts and two withheld research projections.
  It checked seven HTTP records, not the entire population. These are observed
  historical receipts, not a fresh SQL export or evidence of a successful restore.
- The actual configured enrichment backend is the existing isolated SQLite
  Durable Object `cile-enrichment-1`; SQL migrations 0003–0006 and private KV are
  used there. Review V2 D1/R2 migrations 0001–0002 are a separate prepared contract.
  Their presence does not prove deployment or use. D1/R2 inventory was denied in
  the earlier storage decision; this work does not evade that permission boundary.
- The active :10 task still permits `manual-scientific-enrichment` issue comments;
  the :40 ChatGPT task is disabled. The Worker's :40 metadata schedule is separate.
  Existing two-lane documents therefore do not prove two active ChatGPT writers.
- A paginated snapshot of 1,288 public issue comments and 373 queue-labelled
  issues found strict annotation markers for 291 current candidates and 18 other
  candidate identities. The remaining three current candidates have no such
  marker in this capture. This is **marker coverage**, not scientific completeness,
  eight-section coverage, current source identity verification or acceptance.
  Edited comments do not expose their unobserved earlier contents.

## Phase 1: make the live preflight executable

`architecture-audit` is a fixed operation on the existing signed machine service.
It requires the existing secret, one-use nonce and exact deployed commit. It does
not expose SQL, a new public API, raw errors, source text or reviewer material.

It checks all application tables and all their rows, current and historical:

- SQLite foreign-key enforcement/checks and integrity;
- current input identities, retained historical inputs and content hashes;
- all retained source text and document bytes through their existing private adapters;
- document/source/input ownership and redistribution evidence;
- every proposal's original closed schema, evidence and within-study references;
- proposal/child/framework parity rather than trusting counts alone;
- every active current-cycle public projection and completion response;
- identical schema and complete SQL state before/after the audit, refusing a mixed revision.

The existing observer executes the audit after deployment. Limits fail explicitly;
no sample is reported as a complete population. A clean receipt sets
`integrity_verified=true`, never `cutover_ready=true`. It does **not** assert that
CSV, GitHub and private SQL have already been reconciled, or that KV orphan keys,
the submission coordinator, external backups or scientific decisions are verified.
The receipt is infrastructure evidence, not a new paper state or ontology concept.

Local tests use synthetic SQLite/KV data, including the complete 294-target case,
damaged historical source chunks, disabled foreign keys, schema drift, concurrent
changes, authentication and error sanitisation. They are not live migration evidence.

## Preservation and next gate

The baseline Git history was fetched in full. `scripts/review_v2/preserve.py`
created a verified repository archive and history bundle, then restored 671 files
in an isolated directory with byte-for-byte checks. Its honest result is
`cutover_ready=false`: the private persistent state and the other complete external
exports are not yet present in that preservation manifest.

The local client has no `CURATOR_SESSION_SECRET` or Cloudflare credential; direct
Worker requests return Cloudflare 403/1010. Use the existing protected repository
workflow for the closed audit. Do not disable the firewall, expose credentials,
export source bodies to public CI artifacts, or treat a read-only receipt as a backup.

Before moving authoritative data, complete and restore-test the private SQL/KV
backup and the external captures, then use an additive, versioned import with
one receipt per source item. Unresolved candidate/annotation links remain retained
exceptions. No annotation becomes a ScientificExtractionProposal or human decision.
Do not retire the current writer until its replacement has passed live write,
readback, restart, replay, supersession and withdrawal checks.

Remaining work includes candidate authority cutover, governed GitHub annotation
ingestion, normalised repeated facts/relations, conflict-preserving assertions,
all consumer/API changes, writer retirement and live publication verification.
PR #773's automatic loading and menu removal must be integrated against current
main after the database-derived reading contract is ready; a reading JSON alone
cannot satisfy this instruction.

The [Cloudflare storage contract](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/)
describes private SQL/KV and 30-day point-in-time recovery. A PITR capability or
bookmark is not itself a completed restore rehearsal.
