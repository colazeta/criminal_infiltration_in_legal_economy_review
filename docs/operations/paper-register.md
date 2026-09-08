# Automatic operational paper register

Owner instruction, 8 September 2026: papers enter the register by default; the
owner subsequently analyses every paper and assigns labels or exclusions.

The operational register is the existing candidate queue, exposed through a
closed bibliographic projection. It is not another database and does not create
canonical work identities. The website shows it before the assessed corpus.
Registration does not require an eligibility decision or an already acquired PDF.
An unresolved OA check is displayed as access to verify, never as verified OA.
A known non-OA result is not admitted to the OA corpus. Scientific decisions,
labels, duplicate reconciliation and the assessed corpus remain governed.

## Intake contract

New discovery uses run and both intake manifests version 3, Exa only, with the
existing W1–W7, immutable ledger, active-cycle and idempotency rules. The marker
is `<!-- surveillance-run:v3 -->`; envelope and aggregate fields are unchanged.
The v3 run schema is `schema/surveillance-run-v3.schema.json`.

The candidate's `open_access` object is either the unchanged fully verified OA-1
receipt, or exactly `{"candidate_id":"the candidate ID","access_status":"unknown"}`.
Unknown access has no invented checksum, rights statement or verification date.
Empty author arrays are allowed when the source supplies no reliable author;
missing year/venue/DOI remain null. A real observed title and source URL are
required. Metadata not confirmed on primary evidence remain partial or unresolved.

All plausibly scholarly, potentially relevant new records enter as `pending`.
No scientific tags are inferred merely to populate the register. Keep uncertain
identity and metadata discrepancies visible; do not silently merge manifestations.
Discard no potential paper solely because a full-text acquisition fails. Do not
register an unidentified PDF as a made-up citation or a nontechnical summary as
its underlying scientific paper. Such observations remain in the search audit.

Intake v2 and snapshot v1 retain their previous strict receipt semantics.
Intake v3 creates snapshot v2, preserving either the original receipt or the
explicit unknown observation. Both versions remain immutable. Historical zero
intake runs are not rewritten when previously observed works are registered later.
New search/intake timestamps must reflect real new execution.

## Public and private fields

Public register: candidate ID, observed title/authors/year/venue/DOI, source links,
metadata status, review status, intake access status, registration date and any
topic code subsequently assigned by the curator.
The public DOI is observed metadata, not automatically independently verified.
No copied abstracts, reviewer names, internal notes, evidence quotations or
inferred topical labels are exported. The existing curator reads the same queue.

Daily and extraordinary statistics retain separate time series. Candidate counts
mean records actually persisted in intake, including v3 records awaiting access
verification; they never mean confirmed OA or scientifically included papers.
The statistics HTML also contains a deployment-time aggregate summary so the last
extra execution is readable before the separate JSON request succeeds.

## Rollback

Pause new v3 writers before rollback. Preserve original issues, snapshots and
ledger comments. Keep readers that understand v2 and v3; do not revert to a reader
that rejects retained v3 history. The public provisional projection may be hidden
without deleting the underlying register or changing scientific decisions.
