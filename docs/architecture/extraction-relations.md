# Governed extraction relations

`CILE-EXTRACTION-RELATIONS-1`, ontology profile 0.4.2, implements the extraction
part of the consolidation. It does not complete the candidate/GitHub authority
transition. Migration 0007 extends the existing private SQLite Durable Object;
it does not enable a new service or the prepared V2 database.

## Concepts, keys and cardinalities

An `AnalyticalAnnotation` is a scoped assertion expressed by the existing closed
extraction schema, mapped to `oa:Annotation`. It retains a reported/ambiguous or
explicit missing-value status, source/analyst origin, and evidence locations.
It is neither the original source nor an accepted scientific decision. The schema
defines the field vocabulary separately for overview, study, dataset use, analysis,
variable use, finding and contribution-class rationale. This is a finite typed
relation, not an unrestricted key/value or JSON extension field.

| Logical entity or relation | Physical structure / key | Cardinality and update rule |
|---|---|---|
| Extraction proposal | Existing `enrichment_proposals`; `proposal_id` | Target/input-scoped immutable submission; hash-derived internal ID. Multiple incompatible proposals remain separate. No acceptance is inferred. |
| Proposal provenance | `enrichment_proposal_details`; proposal PK/FK | Exactly one; source coverage and private agent/model/prompt provenance. |
| Proposal source membership | `enrichment_proposal_sources`; proposal/source PK | One or more source references, unique order; source must belong to that target and input. No metadata-only source may ground an extraction. |
| Evidence location | `enrichment_spans`; proposal/span PK | Zero or more per proposal; one source each, start/end offsets and optional locator. Application validates retained source bytes and offsets. |
| Study, dataset use, analysis, variable use, finding | Existing typed component tables; proposal/component composite PK, plus five `*_order` tables | A study has zero or more dataset uses and analyses. An analysis has zero or more variable uses and findings. Component IDs retain their original proposal scope; order does not define identity. |
| Analysis/dataset use | `enrichment_analysis_datasets`; proposal/analysis/dataset PK | Many-to-many; same study enforced by trigger; ordered within analysis. |
| Variable/dataset use | `enrichment_variable_datasets`; proposal/variable/dataset PK | Many-to-many; dataset must be used by the owning analysis. |
| Finding/variable use | `enrichment_finding_variables`; proposal/finding/variable PK | Many-to-many; same analysis enforced by trigger. |
| Proposed secondary classes / alternative | `enrichment_secondary_classes`, `enrichment_framework_alternatives` | Zero or more unique secondary classes; exactly one nullable alternative row. Existing primary class/status remain proposed or explicitly missing, never accepted by migration. |
| Scoped assertion | `enrichment_facts`; `fact_id`, proposal FK and typed nullable owner FKs | Exactly one for each schema-declared field of its owner. SHA-256 of canonical `[proposal, scope, owner, field]` gives persistent internal identity. SQL checks permit only the appropriate single owner and closed field/status/origin domains. |
| Assertion grounding | `enrichment_fact_evidence`; fact/span PK with proposal-scoped FKs | Many-to-many, ordered and unique; reported assertions require evidence. Ambiguity requires an explanation and retains any available evidence. No source excerpts appear in public output. |
| Transformation receipt | `enrichment_normalization_receipts`; receipt PK, unique proposal FK | Exactly one successful native/backfill transform; original and rebuilt digests must match. Receipt ID binds proposal and transform version. |

All new primary-key columns are explicitly `NOT NULL`. Foreign keys, unique
constraints, field-specific checks and immutable-row triggers are enumerated in
`physical-schema.json`. `traceability.csv` maps every column to its ontology slot;
`ontology/modules/extraction-relations.json` is the machine mapping. Regenerate
with `build_extraction_relations.py`, `catalogue.py`, and `build_model_browser.py`.
Generation reads the normative closed extraction JSON schema and is validated
against the actual SQLite schema, so a new queried field cannot silently remain
only in a payload.

## Write, read and recovery contract

The sole extraction function is `storeExtraction`. It validates the current
target/input, every retained source hash, schema, evidence and parent relations.
The existing byte store validates immutable source bytes before the SQL write.
Source replay returns its existing ID. If a later SQL operation fails, retained
source bytes remain auditable and reusable; they do not imply a saved extraction.

`batchValidated` then inserts the original immutable submission, existing typed
component identities, normalized facts and joins inside one SQLite transaction.
Before commit it reads the graph back through the actual read queries, reconstructs
the closed submission, and compares its complete canonical value. Only then does
it insert the verified transform receipt. Any mismatch rolls back all these SQL
writes together. Competing identical writes return the same verified receipt;
different content gets a different proposal ID and is never overwritten.

`readNormalizedExtraction` requires a receipt and verifies the reconstructed graph
against the original digest. Ordinary private target reads, adjudication checks and
public research reads use it. Legacy payloads are retained for provenance and
integrity checking; they cannot supply missing normalized fields as a fallback.
The public projection retains its independent privacy/publication gate. An input
revision makes old proposals stale; it cannot silently attach them to new sources.

The signed, exact-deployment `architecture-normalize` operation enumerates every
stored proposal, validates original payload/input/source history, and backfills
each in a verified transaction. It preserves all IDs and source bytes. A failure
leaves already verified proposals intact and the failing proposal uncommitted.
Rerunning validates prior receipts and resumes the remainder. The deployment gate
calls it twice and requires zero new migrations on replay. Logs contain only closed
aggregate counts; per-proposal receipts remain in the private archive and backup.

Before deploying any schema change, the protected workflow obtains the currently
deployed commit and runs **that exact version's** encrypted backup and isolated
restore check. The ciphertext must be retained successfully before deployment.
After deploying, normalization must succeed before execution activation. A failed
normalization leaves the new exact commit inactive; it cannot be reported complete.
Post-deployment preservation captures the expanded schema and its receipts.

Restoration uses the code matching the backup schema: a 22-table capture is restored
with its original release before applying later additive migrations. Keep failed
and post-change captures as well as the pre-change capture; restoring an old code
version alone is not a data rollback. No original proposal/table is deleted by this
migration. Follow `preservation.md` before production replacement, including current
withdrawal restrictions and retention of post-backup events.

## Verification and remaining boundary

Tests exercise concurrent identical writes, two studies with distinct dataset,
analysis and variable membership, injected transaction/readback failure and retry,
physical rejection of cross-scope references, historical backfill/replay, stale
input rejection, public redaction and encrypted restoration of a populated graph.
The complete runtime audit checks all targets, original sources/documents, proposals
and rebuilt relational graphs. Its deployed receipt, not this document, proves
production migration.

This change does not reconcile bibliographic identities, accept classifications,
approve completion, import free-form GitHub annotations, retire the CSV register,
or claim that all other current facts have already moved into SQLite. Those remain
explicit subsequent migration gates in the architecture consolidation record.
