# Mandatory OA evidence at intake

The owner-approved OA-1 rule already requires documented lawful open access for
repository candidate intake. The audit found that v2 manifests could pass with
only a source URL. This fix enforces that existing rule before the first v2
ledger run; it does not change the scientific four-part test.

Every v2 candidate must contain exactly one `open_access` object conforming to
`schema/intake-open-access.schema.json`. The source and candidate manifests and
the run keep version 2; historical v1 records retain their original decoder.

| Field | Required evidence |
|---|---|
| `candidate_id` | Exact candidate to which the verified copy belongs |
| `full_text_url` | HTTPS full-text locator also present in candidate `source_links` |
| `version_type` | `accepted` or `version_of_record`, established for that publication |
| `host_type` | `publisher` or `repository` |
| `license_uri` | Exact stated licence URL; empty string when no licence is stated |
| `rights_basis` | Specific licence or authorised-deposit basis for lawful access |
| `rights_evidence_url` | HTTPS page supporting that basis |
| `access_status` | `verified_open`; other states block intake |
| `verification_method` | `anonymous_full_text_verified` after actual full-text access |
| `full_text_sha256` | SHA-256 of the actual complete file bytes, not the landing page |
| `verified_at` | Actual timestamp with timezone, no later than the recorded run end |

An earlier preprint cannot establish OA for a later article. An aggregator flag,
abstract, login, PDF suffix or guessed rights basis cannot supply this object.
If the full file cannot be acquired and checked, do not invent a hash or receipt:
retain the discovery observation and omit it from intake. Raw discovery counts
remain raw counts; successful searches are not failed merely because no result
has sufficient OA evidence. Explain access limitations in the governed notes.

The importer and ledger verifier call the same validation function. No receipt
means no queue write and no valid positive-intake ledger. This is a check of
complete, consistent, attributed evidence declarations, not an independent
network verification of the supplied URL or proof that the supplied hash came
from that URL. Identity, actual file contents and rights still require source
inspection. OA never supplies scientific eligibility.

The importer preserves receipts, batch, source issue number and a SHA-256 of the
original UTF-8 issue body in
`data/curation/intake_access/ACADEMIC-YYYY-MM-DD.json`. The issue's authenticated
actor and workflow remain the attribution trail. The metadata-only snapshot is
created exclusively, never overwritten by a repeated import. The queue and
snapshot are committed together by the intake workflow. Ordinary queue-write
failure removes only the snapshot newly created by that attempt. An interrupted
local process with an orphan snapshot fails closed and requires reconciliation
before retry; it must not overwrite preserved evidence.

The ontology validator requires one receipt per active daily candidate and
rejects orphan/duplicate receipts, missing coverage and incompatible source
provenance. Later access revocation or metadata correction must not rewrite the
original intake observation. Current publication approval continues to use its
own current OA assessment, including revocation checks. Neither full text nor
these candidate receipts are copied to the public site.

No real candidate is inserted by this fix. The active archive reset has already
completed; private V2 activation has not. The external Work task remains the
active search mechanism. The batch already recorded for the reset date must not
be overwritten or reused for an extraordinary run. A full production trial
requires an unused governed daily batch; use the next scheduled day unless a
separate extraordinary-run identity policy is explicitly adopted.

Rollback must preserve every newly written receipt and candidate. Do not deploy
the older permissive importer over the new intake: pause intake and apply a
reviewed compatible repair. The scientific profile and controlled vocabulary
remain unchanged.
