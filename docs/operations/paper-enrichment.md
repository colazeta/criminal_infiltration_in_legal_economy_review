# Paper enrichment: operational contract

Protocol **CILE-ENRICH-1** · ontology **0.4.0** · clinical codebook **1.0.0**.
Owner implementation mandate: 11 September 2026. This authorises engineering and
mechanical enrichment, not scientific inclusion or the approval of machine labels.

## Implemented boundary

The candidate register is the input, not a new search. The Worker reads the fixed
published `data/paper-register.json` endpoint, validates the entire projection and
synchronises stable candidate references into private D1. No canonical work ID is
created. The original registry and daily-discovery runner are not written.

Fifteen additive private tables store targets, immutable input snapshots, jobs,
run receipts, attempts, sources, directed citation observations, provider coverage,
immutable extraction proposals and their studies, datasets, analyses, variable
uses, findings and framework proposals. Every SQL field and every JSON-envelope
property is mapped in the ontology. The migration starts empty.

The source and proposal APIs are available only to the authenticated repository
curator. The interface is `enrichment.html` on the dedicated Worker origin; first
sign in through `curate.html`. The HTML/JavaScript shell contains no paper content.
No abstract, source quotation, proposal, researcher note or secret enters Pages,
GitHub issues, workflow artefacts or source control.

## What the initial runner does — and does not do

When `PAPER_ENRICHMENT_ENABLED=true` and both private bindings exist, the existing
15-minute Cloudflare supervisor checks a persistent hourly slot. At most **one
job** is attempted per hour. A failed or missed daily-discovery run cannot suppress
it. This first capacity limit is intentionally conservative, not a throughput claim.

* **Metadata/abstract:** one candidate-bound Crossref lookup. Exact DOI and
  punctuation/diacritic-normalised title must agree. The exact returned abstract,
  including JATS/XML when supplied, is retained privately with its own hash.
  Missing abstract means `not_returned`, not that the publication lacks one.
* **Citations:** one resumable OpenAlex stage, at most 100 outgoing identifiers or
  one page of 50 incoming identifiers. A graph snapshot is checkpointed before
  edges are written. Citations are external bibliographic identifiers, not new
  review members or canonically resolved works. Their full metadata/contexts are
  not yet resolved by this adapter. `provider_complete` means exhausted for that
  provider, direction and snapshot only; it never means a complete real-world graph.
* **Scientific extraction/classification:** jobs are explicitly
  `blocked/model_calibration_required`. A source-grounded proposal can already be
  imported and inspected, but no model, API key or synthetic gold labels are
  supplied by this implementation. Source acquisition and a working schedule do
  not constitute validation of extraction quality.

Crossref refreshes after 30 days; completed citation snapshots after seven days.
Incomplete citation pages are due after an hour, subject to older queued jobs.
Three consecutive transient failures exhaust a job, with exponential backoff and
`Retry-After` respected. Identity conflicts, missing DOI, authentication refusal
and absent provider records block only that job. They do not become empty success.
No paid fallback, credential creation or unrestricted crawl is authorised.

No-DOI records are retained but require an identity-resolution adapter or curator
correction before these two DOI-based adapters can work. This is visible workload,
not a reason to drop a paper. Adding more sources is an independently tested adapter
change, not an implicit promise that the current two providers cover the corpus.

## Persistence and recovery

Targets are keyed by cycle, namespace and register ID. Input versions are
content hashes, not execution times. Source changes supersede old jobs without
erasing their results. Restoring an earlier exact input reactivates mechanically
superseded jobs; scientific proposals remain immutable.

A database-enforced single active run and ten-minute leases prevent overlap.
The next supervisor call recovers an expired run and job. Normal attempts have terminal receipts; interrupted attempts are also identifiable
from the expired run and job lease records. Source storage follows R2 write, hash-checked R2 readback,
D1 receipt and D1 readback. A proposal and all its normalised objects are written
in one transaction (maximum 90 statements), never partial scientific batches.

A scheduled slot is an observation of actual work, not a promise of punctuality.
A missed hour leaves work in the queue. Network requests have a complete-request
12-second timeout and a three-megabyte response limit; source snapshots are limited
to two million UTF-16 code units. Repository synchronisation failures still allow
previously persisted valid jobs, but their run is labelled partial.

## Readiness and activation

The default example configuration is **disabled**. Production may enable only
mechanical jobs after the additive migration, private R2 access, an isolated live
provider smoke test, authenticated reads and scheduler configuration are checked.
The flag must not be set merely because unit tests pass. Production deployment
must report each blocker, not conceal a failed migration behind a green build.

Scientific automation requires a separate recorded calibration: 12–18 real papers
with heterogeneous designs and source availability; an independently checked
reference extraction; field-level accuracy/omissions, source fidelity, coding
agreement and disagreements; selected model and exact prompt; tested cost/call
limits; and explicit acceptance. Synthetic software fixtures are not calibration.
Until then, the interface must continue to display the block.

## Authenticated API

All endpoints share `/api/paper-enrichment/` and the existing curator session and
CSRF controls. `GET status` gives execution counts and remaining blocks; `GET
 targets` lists up to 500 active targets. `GET target?id=...` shows jobs, source
metadata and proposal history; `GET source?id=...&source=...` verifies and returns
private source text. `GET citations?id=...&offset=...` returns 100 directed
observations with `next_offset` and provider coverage. Historical snapshots may
contain the same edge; count distinct edges when studying network size.

`POST source?id=...` accepts the closed source envelope (current input hash,
source URL, kind, exact text, version, language, retention basis and licence status).
It does not visit the URL or certify rights, OA, identity or eligibility. `POST
proposal?id=...` validates `schema/paper-enrichment.schema.json` plus source scope,
hashes, spans, study/analysis relations and coding rules. Replays return the same
proposal ID. New corrections create a new proposal, not an overwrite.

## Monitoring and rollback

Inspect runs **and** jobs. A functioning trigger with only blocked/exhausted jobs
is not productive enrichment. Report last attempted hour, actual selected job,
new source count, pending/blocked/exhausted work and citation coverage separately.
The interface reports these private metrics; it does not equate an HTTP response
with scientific completion. No monitoring notification service is configured.

Pause with `PAPER_ENRICHMENT_ENABLED=false` and redeploy. Preserve D1/R2 and all
receipts. Revert software through a normal reviewed revert; never run destructive
migration rollback. Profile 0.3.0 scientific records remain supported by the
additive 0.4.0 application. Original migration hashes and old decisions are unchanged.

## Implementation readiness observation — 11 September 2026

The production-environment preflight (GitHub Actions run `34596980260`, job
`103254908996`, 12:03 UTC) successfully read the existing deployment credential
without displaying it, resolved the unique account, then received **HTTP 401**
from the D1 inventory request. Thus private database readiness was not verified;
no new paper extraction or hourly runner was enabled. The blank optional account
variable was not the observed failure: unique-account discovery had already passed.
The D1 authorisation/account scope of the existing deployment token needs checking.
R2/queue readiness cannot be inferred from this failed D1 request. A storage-only
fallback is now available so this enrichment module need not depend on discovery
queue permissions. Neither path changes account permissions or subscribes to a plan.
