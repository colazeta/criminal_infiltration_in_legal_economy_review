# Private archive preservation and isolated restoration

`CILE-PRIVATE-ARCHIVE-BACKUP-1` is a transport representation of the existing
`LegacySnapshot` concept. It preserves a named revision, not a second current
research database. It supplies no identity reconciliation or scientific decision.

## Scope and identifiers

Each capture has a persistent random `snapshot_id`, deployed Git commit, SQL
schema/state digests, per-table row counts/digests and a digest of all retained KV
entries. Every encrypted page binds its snapshot ID and deployed commit as
authenticated associated data. Mixing captures, changing bytes, using the wrong
key or truncating the file fails restoration.

The scope is the complete existing `PaperEnrichmentStore`: all governed SQL rows
and all application KV entries, including historical/private sources, document
bytes, unattached objects, schema receipts and development checkpoints. Only
`nonce:` anti-replay tokens and `probe:` ephemeral readiness values are excluded;
their exact prefixes are declared. Unknown stored value types stop the export.
Cloudflare platform tables are accessed through the platform API, never copied
as user SQL. The captured alarm is operational context; restart scheduling must
be derived from the restored schedule/lease rows after maintenance review.

The live census at commit `23c01856c9fdb5d9b37a8d36c91d2409f44fb29f`
confirmed all 22 expected tables, no other mapped V2 table, `_cf_KV`, and one
unknown name digest. That digest (`e8f14d3f3bed3f3962063f5823fb1c5d3f6d717a933d31fa09d4bc36cc0875bb`)
matches `_cf_METADATA`, whose platform purpose and definition are confirmed by
[workerd SqliteMetadata](https://github.com/cloudflare/workerd/blob/main/src/workerd/util/sqlite-metadata.c++).
The exact platform-name exception does not allow arbitrary `_cf_*` tables.

This does **not** include SubmissionCoordinator, GitHub issues/reviews/ledger,
automation configuration or Git history. Their separate verified captures must
be joined by the existing `scripts/review_v2/preserve.py` manifest before any
authority cutover. A successful private-store restore alone always reports
`cutover_ready: false` and `other_stores_included: false`.

## Capture and consistency

The fixed machine operation requires the existing service signature, fresh nonce
and exact deployment. It accepts only the catalogue, a bounded page from an
allowlisted table, or a bounded KV page. It accepts no SQL, execution, publication,
restore or write instruction. It is independent of enrichment activation.

Pages are encrypted inside the Durable Object with AES-256-GCM and fresh 96-bit
nonces. The key is derived from the existing protected session secret using
HMAC-SHA-256 with a separate backup protocol domain. The secret itself is never
exported, logged or stored in the backup. **Retain the old session secret for the
backup's retention period when rotating credentials**, or reseal and verify the
backup under the successor key first. Loss of the key makes that copy unusable.

The protected workflow reads and hashes every SQL row, reads the entire KV space
twice, and rechecks SQL schema/state at the end. It refuses any intervening change
instead of certifying a mixed revision. A failed capture can be retried in a quiet
interval; it never pauses a writer or changes a candidate. Existing leases and
incomplete operations are preserved, not labelled successful.

The worker, runner and file are bounded. Exceeding a bound is an explicit failed
backup, never a truncated successful one. The runner decrypts only in memory.
Its file is ciphertext with mode 0600; Actions retains ciphertext only for 90 days.
Logs contain aggregate hashes/counts and closed failure codes, no original bytes,
SQL rows, reviewer identities, notes, raw errors or credentials.

## Restore rehearsal and recovery procedure

The workflow restores the captured file into a new in-memory SQLite database with
the same repository migrations and a new isolated KV adapter. It inserts all rows
in dependency order inside one deferred-foreign-key transaction, preserving all
SQL triggers and constraints, and reopens the existing storage core with
all research execution disabled, and runs the complete architecture audit.
It checks every historical source/document hash, target identity/input link,
proposal relation, current public projection, and SQL state/schema digest. It
does not contact providers or restore over production. Pre-existing integrity
failures remain failures; they are not repaired or concealed by the backup.

To repeat the rehearsal in an authorised environment with the retained secret:

```bash
node scripts/architecture/private-backup.mjs restore /private/backup.encrypted.json
```

Before a production recovery:

1. Stop the authorised writers and preserve the current failed/partial state.
2. Verify the immutable encrypted artifact digest and retained key, then rehearse
   the exact snapshot with its compatible code in isolation.
3. Reconcile events and withdrawals after the snapshot. Do not restore an old
   public projection that could republish withdrawn or restricted content.
4. Restore into the approved destination through a separately reviewed maintenance
   operation; no production restore endpoint is exposed by this change.
5. Re-run complete referential, byte and public projection checks, retain their
   receipt, and only then re-enable the correct writers and scheduling.

The application-level rehearsal verifies reconstructibility of the data and
adapters. It is not a claim that Cloudflare point-in-time recovery has been tested.
Production replacement and cross-store recovery remain gated until their actual
execution is evidenced.
