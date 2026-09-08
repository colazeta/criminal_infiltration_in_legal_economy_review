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
local process can resume using a byte-identical orphan snapshot; a different
snapshot fails closed and must not be overwritten.

The ontology validator requires one receipt per active daily candidate and
rejects orphan/duplicate receipts, missing coverage and incompatible source
provenance. Later access revocation or metadata correction must not rewrite the
original intake observation. Current publication approval continues to use its
own current OA assessment, including revocation checks. Neither full text nor
these candidate receipts are copied to the public site.

No real candidate is inserted by this fix. The active archive reset has already
completed; private V2 activation has not. The external Work task remains the
active search mechanism. The batch already recorded for the reset date must not
be overwritten or reused. The owner-approved [extraordinary-run policy](extraordinary-runs.md)
now supplies a distinct identity for an additional post-reset execution today.

Rollback must preserve every newly written receipt and candidate. Do not deploy
the older permissive importer over the new intake: pause intake and apply a
reviewed compatible repair. The scientific profile and controlled vocabulary
remain unchanged.

## Second audit hardening — 2026-09-08

The former Zenodo-only automated acquisition boundary was extended by the
owner-approved [extraordinary-run and OA amendment](extraordinary-runs.md).
Use the exact-host policy in `config/oa-acquisition.json` and the bounded
`oa_acquisition.py` client. Unknown origins still require a reviewed amendment;
identity, version, full content and lawful rights must still be verified.

The production import now requires the authenticated issue creation timestamp
and a completed, validated ledger run. Verification must precede issue creation,
which must fall inside that run window and on its Rome batch date. Issue number,
reset timestamp and scheduled start date enforce the active cycle. Extraordinary
IDs may use the reset day only after the actual reset timestamp. The pure
manifest parser checks syntax and evidence fields; it is not the production
lifecycle gate. The CLI requires run context and the workflow obtains it from
the authenticated ledger reader. Discovery must write its terminal ledger
without waiting for queue import. Only absent ledger data are polled: eight
checks at 15-second intervals (105 seconds total waiting). Invalid evidence or
authentication fails immediately. If the ledger arrives later, reopen the owner
issue after repair; do not create a second issue or rerun discovery for that batch.

Receipts are written completely to a temporary file and atomically published
without overwriting an existing path. A byte-identical orphan from a killed
attempt is reused; a different orphan blocks retry. Committed receipts cannot
be modified or deleted: `validate_intake_history.py` compares their actual bytes
against the authenticated PR base or pre-push revision, with full Git history in
CI. The staging workflow compares against HEAD before committing. A missing Git
base fails closed. The ordinary snapshot validator checks internal structure;
it does not independently recover an issue body from its SHA-256. The history
gate supplies cross-revision immutability, not proof of scholarly truth.

The ontology module now declares explicit physical transformations: the integer
issue number becomes one repository issue URI; schema version becomes text;
receipts are structural containment of individual AccessAssessment records,
not a scalar `prov:wasDerivedFrom` value. The validator checks range and
cardinality and rejects undeclared transformations. No scientific class,
controlled vocabulary or screening decision changes.

Calendar validation derives absent-day status from its timezone-aware clock,
rejects fabricated completed/planned states, and recalculates totals only after
that check. The website flags a projection older than 26 hours (24-hour cadence
plus two hours of refresh grace), including an empty pre-start baseline. This
client-clock warning does not invent ledger rows for later days. Intake counts
mean issues created, not successful queue import; queue import still has a
separate workflow outcome. Neither scheduled execution nor successful external
provider calls are guaranteed by these repairs.

### Review corrections

The PR review additionally identified that globally declared receipt slots were
not attached to the normative AccessAssessment class. The compatible profile
erratum attaches those existing slots to that existing operational class, and
the validator now follows inherited class slots. This correction is versioned
in Git with the repair; profile identifier 0.3.0, all scientific concepts,
controlled states and screening criteria remain unchanged. No new ontology
concept or data schema is introduced.

The ledger gate also rereads the authenticated live issue and requires its body,
title and creation timestamp to equal the queued event before producing import
context. Distinct candidate manifests cannot substitute for one another merely
because aggregate counts agree. Both live and event content must validate.
