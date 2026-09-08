# Open-access scope — OA-1

Owner instruction of 2026-09-08 changes the target to an **open-access evidence
map**. It authorises preparation of a fresh OA seed frontier and, after verified
preservation and operational readiness, clean restart. It does not substitute
for an individual four-part screening or publication approval.

## Admission rule

An included publication must have a lawful, complete, anonymously accessible
copy on a publisher or repository service. Verify the publication identity,
version, actual full text and the host's licence or authorised-deposit statement.
Accepted author manuscripts and versions of record qualify. A repository copy
does not create another Work. Record differences between publication dates,
repository deposit dates and manuscript versions; never silently reconcile them.

This is an access-to-reading criterion. Record a stated Creative Commons or
other licence exactly; lawful repository access does not imply unrestricted
reuse, and an absent licence stays unknown. Do not infer rights from a search
engine badge, an aggregator OA flag or a filename ending in PDF.

Free abstracts, metadata, previews, supplements without the article, temporary
personal sharing links, unverified uploads, login-only access and paywalled
copies do not pass. An earlier working paper/preprint does not make a later
journal article open. A working paper can only be considered under its own
document identity and published version, with its review status explicit.

Access is independent of the four scientific criteria. `unknown`, `restricted`
and `revoked` block OA admission without inventing a scientific NO or changing
legacy exclusions. `verified_open` does not approve scientific eligibility.

## Evidence and implementation

- Legacy public builders read only the new, initially empty governed
  `data/registry/open_access_assessments.csv`. Each assessment binds one Work to
  the verified copy, declared version, rights evidence, anonymous full-text
  verification, byte checksum and dated observation. Supersession is linear and
  preserved; a revoked latest assessment blocks both public collections.
- Private V2 uses additive migration `0002_open_access.sql`. An attributed
  access assessment must refer to the same candidate's verified full-text
  evidence. The API verifies the retained source hash before recording the
  curator's anonymous-access attestation. This is an explicit human verification
  workflow, not an automatic proof that any pasted text came from its URL.
- V2 proposals under `CILE-4PT-OA-v3` bind the exact current access assessment.
  Approval import revalidates it; a database trigger closes the race if it has
  been superseded. A separate database publication gate requires current OA.
- The public record exposes only access status, full-text link, version, host,
  stated licence and observation time. Internal evidence bodies, attribution,
  notes and assessment IDs remain outside the public export.

The ontology is version 0.3.0. Existing scientific classifications and controlled
domain codes are not recoded by the access-policy change. The former migration
and historical decisions remain intact.

## Expansion and daily surveillance

Search broadly enough to find green OA copies; do not rely solely on an API's OA
filter. Preserve raw occurrences before applying the admission check. A retained
discovery occurrence with unverified access is not an included publication.
For the repository intake lane, candidate hits and proposed seed admissions now
require a structured `open_access` attestation under
[intake-open-access.md](../operations/intake-open-access.md). Both the queue importer
and metrics verifier reject absent or incomplete receipts. Record source/query
limits and this scope change in the existing diagnostic fields. Do not change raw result totals into OA totals.

Following the owner's source amendment of 2026-09-08, daily discovery uses only
Exa for W1–W7. Ledger idempotency, failed/partial day visibility and the
07:00 Europe/Rome schedule remain. The personal AML digest is
separate from this archive scope. Access observations may be revisited if a
legal repository copy appears; do not erase the failed or restricted observation.

## Coverage and freshness limits

Report this as an OA evidence map, not exhaustive coverage of all scholarship.
Older books, particular disciplines, countries and languages may be less visible.
Report document version and OA host, and assess that selection bias in synthesis.

Access is observed at a time; links and permissions can change. Recheck a copy
before admission/publication and when a broken link or rights change is found;
append revocation or a new verification. The current static publication process
does not perform scheduled network revalidation of every existing OA link. A
periodic link/rights revalidation worker remains required for freshness monitoring;
neither an old receipt nor a successful deployment guarantees perpetual access.

## Restart and rollback

The active archive reset was completed on 2026-09-08 in release 0.3.0 under the
owner's explicit instruction. Registries and the candidate queue started empty;
legacy snapshots and scientific histories were preserved. See
[archive-reset.md](../operations/archive-reset.md) for the exact scope and rollback.

Private D1 Review V2 activation is a separate, unfinished operation. The earlier
D1 inventory HTTP 401 was an observed access blocker, not evidence that the
already completed archive reset was undone. The deployment explicitly keeps the
V2 runner disabled. Provisioning, inventory, restore, access and queue readiness
must be verified before any activation; this intake fix does not activate it.

Rollback of the active archive follows the reset runbook. Future V2 rollback
must first pause its writers and preserve new history before switching readers;
it never overwrites an active database.

The prepared research dossier is delivered privately and is not embedded in a
technical PR or static candidate export. It remains seed and expansion preparation, not an activated private V2 corpus
or a scientific decision.


## Same-day extraordinary execution amendment — 2026-09-08

The owner-approved [extraordinary-run policy](../operations/extraordinary-runs.md) adds independently identified manual executions and
explicit publisher/repository acquisition origins. It supersedes the former
requirement to wait until the next calendar day and the Zenodo-only acquisition
restriction. Daily IDs, schedules, historic records and scientific approval gates
remain unchanged. Public statistics v3 shows extraordinary executions separately;
they never fill scheduled-day gaps. Read that policy before a manual run.

## Superseding operational registration instruction — 2026-09-08

The owner requires papers to enter the visible operational register before individual analysis and labelling. New intake uses run/manifest v3 and may record access as unknown. The mandatory verified-OA rule above applies to historical v2 intake and to admission into the assessed OA corpus, not to provisional registration. See [the registration contract](../operations/paper-register.md). No scientific approval is implied.
