# Repository ingress and unreviewed annotations

This is the implemented 0008 migration and writer contract,
`CILE-ANNOTATION-ARCHIVE-1`, under ontology profile 0.4.3. Application in production
must be evidenced by the protected ingestion and complete-store audit receipts.
It does not complete the candidate/CSV authority transition or certify that the
browser's older GitHub reader has already been replaced.

## Meaning and authority

An observed GitHub issue/comment is an external input snapshot. Its original body,
source ID, URL, source timestamps and attribution are retained privately with a
content digest. Snapshot identity is independent of issue number, candidate ID,
DOI and paper identity. Snapshots are `LegacySnapshot` instances with this explicitly
limited input scope; none is represented as a full-system preservation manifest.

A marked reading annotation is an `AssistantRecommendation`, with scoped
`oa:Annotation` sections and fields. Its effective state is always
`unreviewed_manual_support`; unknown model, prompt and source-content version are
not invented. A heading “Study S1” remains a declared annotation group, not a new
`ReportedStudy` with invented membership or a complete extraction. Unlabelled
dataset/variable/finding prose stays an attributed annotation; it is not promoted
to a normalized scientific dataset or analysis. The original complete text remains
available privately even when the bounded parser cannot interpret it.

Only one consistent exact candidate marker in both the issue and comment binds
an already active candidate target. Absent markers are unresolved; inconsistent
markers are conflicts; markers outside the current register are unregistered.
These inputs remain private exceptions with persistent IDs. They do not create
candidates, canonical works, expressions, eligibility or completion decisions.

The configured curator's already owner-authorised public reading annotations may
use the closed display projection. Other commenters cannot acquire that authority
by copying a marker. Their inputs are retained, with `authorised_display=0`.
This is a publication boundary for unreviewed support, not scientific approval.

## Logical and physical contract

| Entity / relation | Key and constraints | Update and provenance |
|---|---|---|
| Ingress snapshot | `enrichment_ingress_snapshots.snapshot_id`; unique source kind/external ID/content digest and private object key | Immutable hash-derived ID; original JSON is a bounded source capture only, not current queryable research state. |
| Manual annotation | `enrichment_manual_annotations.annotation_id`; unique snapshot FK; issue snapshot FK; optional target FK | Immutable ID binds source revision and parser contract. Candidate marker, association state, display authority and review state remain separate. |
| Annotation section | `enrichment_annotation_sections.section_id`; annotation FK and unique position | Closed eight-part reading scope and source-declared group label. It supplies no inferred study/analysis link. |
| Annotation field | `enrichment_annotation_fields.field_id`; section FK and unique position | Controlled field names and a scope-checking trigger. Text is an attributed claim, not an unrestricted extension object. |
| Proposed class assertion | `enrichment_annotation_classes.assertion_id`; field/annotation FKs; unique field/category/role | Only a complete explicit six-class value/list under primary, secondary or alternative is interpreted. Mentions in rationale/free text never generate labels. |
| Current source revision | `enrichment_annotation_heads.external_id`; annotation FK, integer record version | Compare-and-swap plus a SQL version trigger. Current/withdrawn/conflict is display revision state, independent of scientific status. |
| Revision event | `enrichment_annotation_events.event_id`; current/prior annotation FKs | Immutable import, external revision, older revision, conflict or withdrawal history. Event replay cannot create endless versions. |
| Verified transform receipt | `enrichment_annotation_receipts.receipt_id`; unique annotation FK | Original source digest and identical parsed/reconstructed graph digests; parser version and verification time. |

All new keys are explicitly non-null. The generated physical dictionary and
traceability matrix list every column, SQL type, mandatory field, FK, index and
guard. All rows except versioned head pointers are append-only. SQL prohibits
changing a withdrawn head back to current through the ordinary importer.

## Writes, conflicts and failure recovery

`ingestAnnotation` first preserves and hashes the original issue and comment bytes.
It reads them back before recording their source rows. Annotation, section, field,
class, head and event writes form one validated SQLite transaction. The transaction
reconstructs the stored graph and compares it exactly before inserting the receipt.
Concurrent identical inputs return the same receipt. Failed annotation transactions
retain their input snapshots for retry, with no false successful annotation receipt.

For one external comment, a later observed GitHub edit supersedes that comment's
earlier display revision. Both originals and their graph rows remain. Older versions
cannot displace a newer version. Different content at the same external revision
time creates a retained conflict, never a last-string choice. Replaying an old
version cannot clear that conflict. Different comments remain coexisting proposals;
the importer does not choose a scientific winner or invent a supersession between
them. GitHub's unobserved intermediate edits cannot be recovered and are not claimed.

A deletion event withdraws the source annotation from the current projection;
its history remains. Later observations, even newer timestamps, cannot republish
it. A complete, repeatedly checked upstream census also retires absent comment IDs.
Heads updated after the census began are explicitly deferred, preventing accidental
retirement of a concurrent input. Restoration/republication requires a separately
reviewed human instruction; it is not supplied by re-running migration.

`archive-annotation` and bounded 25-item `archive-annotation-batch` are fixed signed
operations tied to the currently deployed commit. A partially failed batch can be
replayed because each item has its own transaction and receipt. There is no SQL,
arbitrary command, approval or free publication parameter in the envelope.

## Acquisition and projection

`scripts/architecture/ingest_annotations.py` runs from trusted main code with a
read-only repository token and the existing protected service credential. It reads
all paginated issue/comment inputs, refuses missing parents and repeated IDs,
imports every observed input and verifies replay. It then compares another complete
source capture, acquiring only changed observations in at most four reconciliation
rounds. Only a repeated complete population can certify the final census; continuing
changes fail explicitly with retained partial progress. A census cannot precede that
check. Its observation cutoff follows the writes and precedes the final source read,
so concurrent later head updates remain protected. Repository
PR issue-comments are retained as source snapshots but cannot become candidate
annotations through this path. Full PR review/audit preservation remains a separate
scope in the system preservation manifest.

Deployment performs the complete import after schema migration and before execution
activation; subsequent audit/backup workflows therefore start after this gate.
The ingress workflow handles created/edited/deleted issue-comments. It adds no
scheduler and writes no GitHub messages. A failed delivery
is incomplete; a later full reconciliation resumes existing receipts. Source bodies,
attribution and raw errors are never printed or uploaded in plaintext artifacts.
The existing protected pre-deployment backup and post-deployment preservation cover
all eight new tables and retained private input bytes.

Operational errors expose only a closed diagnostic class, never a raw exception,
source body, actor or credential. A generic failure without a diagnostic cannot
establish that storage failed: inspect the complete private audit and per-item
receipts before recovery. The first 0008 deployment retained 317 annotations and
passed the full-store integrity audit while its final acquisition gate failed;
execution correctly remained inactive. Bounded catch-up handles mutable upstream
inputs without discarding earlier versions or relaxing the final stability check.

The internal `readPublicAnnotations` projection reconstructs stored relations and
checks original source integrity. It emits only authorised, current, candidate-bound
reading fields, proposed class roles and public source URLs. It withholds conflicts
and withdrawals and excludes attribution, hidden analyst notes, source storage keys,
credential-like text and unrecognised sections. The private audit checks every
original source and reconstructed graph, including withheld and unresolved records.
External API and browser cutover must follow the successful migration receipt;
this document does not claim that remaining browser GitHub reads are already retired.

## Controlled preflight, 19 September 2026

The previously preserved source capture contains 373 candidate issues and 1,288
repository comments. 336 comments have parents in that capture; 952 parents require
the complete acquisition rather than an invented association. The local import of
those 336 preserved comments retained 653 source snapshots and 314 annotations:
291 candidate-bound, five unresolved and 18 outside the current register. There
were no import errors. All 294 current candidates were projected: 291 had at least
one authorised unreviewed annotation; three had none. There were 614 explicit
primary/secondary/alternative class assertions, **not** 614 classified papers.
This is a scoped local preflight of the dated capture, not a production population
or migration receipt. The live workflow must acquire all current parents/comments.

Tests cover concurrent replay, explicit group preservation, private redaction,
untrusted commenter markers, marker conflicts, competing annotations, source edits,
equal-time conflicts, rollback/retry, withdrawal and encrypted isolated restoration.
