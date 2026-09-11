# Hour-40 implementation verification — 11 September 2026

This is an engineering verification receipt, not a scientific calibration or a fabricated production execution history.

## Starting point and actual failure

The inspected main commit was `3019ad90c81dddeea2978dbeb3fdce6c689f9289`. The existing production storage is the private SQLite/KV Durable Object, not the earlier blocked D1/R2 configuration. Previous deployment run `34603354658` demonstrated authenticated readback, activation and a completed real metadata job. Latest inspected pilot run `34606679010`, job `103286700143`, reached model-response parsing and failed with `pilot_framework_ungrounded`. Its final aggregate was 174 targets, two private sources, zero citation observations and zero proposals. These are historical observations, not a current whole-corpus completion claim.

## Changes and software evidence

The implementation retains the existing source/analysis envelope and adds three empty operational tables through migration `0004_enrichment_schedule.sql`. Ontology profile `0.4.1` maps every new table/column, with schedule, iteration and attempt kept distinct. The original scientific migration and evidence remain unchanged.

The exact public-source patch SHA-256 is `eb8a54fd91be74d68984dd4a97f9259de002036cd9e1989d5dd1ce3d1a6c7082`. It was applied only after an integrity check and `git apply --check`, then independently rerun in GitHub Actions run `34621143961`, which completed successfully. No production secret, source text or model output was used in that transfer or regression run. The temporary transfer files and workflows were removed from the branch tip.

Local checks passed: 421 Python tests, 137 JavaScript tests, repository and ontology validators, deterministic model-browser generation, archive/secondary/curator builders, archive and static-site validators, and mandatory JavaScript syntax checks. GitHub repeated the full validation commands successfully. The model browser contains 51 entity definitions and no private corpus data. The source snapshot still contains 174 candidates, zero canonical works and zero published core/secondary records. The saturation report remains NOT SATURATED with zero recorded cycles.

Twelve scheduler tests use a controlled clock and synthetic processing receipts. They cover minute-40 boundaries; duplicate notifications; 401 overdue slots without a truncated recovery window; overlapping two-hour simulated work with pending slots retained; asynchronous concurrent calls; processor leases; crashes and fencing; reconciliation after a committed processor receipt; backoff; immutable attempts; and reactivation without resetting the scheduling epoch. These tests are NOT actual production hours, actual long-running Cloudflare invocations or real scientific extractions.

## Deployment and pilot ordering

The configured cron includes `40 * * * *`. The earlier supervisor remains a recovery notification, not four new research iterations per hour. Durable alarms also wake the persistent queue. Planned time, actual materialisation, attempts and actual completion are separately visible in the authenticated console.

The pilot generation schema now requires an evidence-backed non-null rationale whenever it generates a category. The existing converter's rejection of unsupported classification remains intact. A second change runs the one-paper pilot after successful main-branch deployment rather than concurrently with it; it refuses a stale deployed commit before private access. It has no hourly scientific schedule and does not approve any label. The private interface can render a stored proposal as readable field tables while preserving its evidence IDs and raw provenance.

## Evidence still required after merge

Check exact deployed commit and ontology, additive migration, activation, the first planned slot and a real source/proposal readback. Observe subsequent actual minute-40 iterations and inspect their persisted receipts. Do not relabel test-clock overlaps as production overlap evidence.

The heterogeneous 12–18-paper independent content benchmark, full-text extraction capability and scientific recurring execution remain outstanding. Schema-valid source references establish location and scope, not entailment or extraction accuracy. No calibration score, reference label, source fact or claim of completed scientific automation has been invented.
