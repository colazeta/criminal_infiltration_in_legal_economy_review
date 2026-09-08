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
require documented OA; record source/query limits and this scope change in the
existing diagnostic fields. Do not change raw result totals into OA totals.

The existing Consensus + Exa daily method, W1–W7, ledger idempotency, failed/partial
day handling and 07:00 Europe/Rome schedule remain. The personal AML digest is
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

The clean restart remains operationally blocked by the existing D1 inventory
HTTP 401 and the previously documented private-resource and source-runner gates.
No reset is executed by these technical changes. Before cutover, preserve the
complete Git and external state and verify an isolated restore. Start a new
review namespace and T0 with zero decisions/codings/publications and a separately
admitted OA candidate frontier. Do not import legacy eligibility or assign it
from seed membership. Retain the entire legacy namespace, issue/PR/review and
ledger history, identifiers, evidence, automation configuration and provider
budget counters. A rollback pauses V2 writers, preserves their history and
restores the legacy read pointer; it never overwrites an active database.

The prepared research dossier is delivered privately and is not embedded in a
technical PR or static candidate export. Until cutover succeeds, it is a seed
and expansion preparation, not an activated V2 corpus or scientific decision.
