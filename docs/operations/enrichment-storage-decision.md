# Private enrichment storage — implementation decision, 11 September 2026

## Evidence and decision

Read-only run 34599570774 verified a valid Cloudflare deployment token and access to the existing Worker. D1 inventory returned HTTP 401/code 10000, R2 inventory returned HTTP 403/code 10000, and Workers AI catalogue returned HTTP 403/code 10000. The optional OpenAI secret was absent. These are not missing paper results.

Use an **explicitly selected isolated SQLite-backed Durable Object** within the already deployed Workers service for enrichment. Do not change token scopes, request broader credentials, bind to a denied D1 database, subscribe to a plan, or reuse another project's storage. The original D1/R2 adapter remains available but is not a prerequisite for this independent module. No D1/R2 migration is executed in this deployment mode.

The new `PaperEnrichmentStore` class has its own namespace and object identity. It does not reuse the curator submission coordinator, and it cannot access or change the canonical corpus. The SQL is byte-identical to migration 0003; SQLite transactions preserve the same foreign keys, append-only triggers and proposal atomicity. Sources remain linked by the same content hashes and storage keys. Their private text is chunked into bounded KV values inside the same object. No source text, proposal, secret or reviewer note is published through Pages, GitHub, logs or artefacts.

This is a physical storage implementation, not a new scientific ontology or an implicit migration of existing research. `ontology/modules/paper-enrichment.json` records both backends. The generated SQL bundle must match the normative migration byte-for-byte. SQL and its migration receipt are initialised in one private transaction.

## Readiness, activation and rollback

The code-level flag permits activation but is insufficient by itself. Activation requires an authenticated storage read/write/readback check and a receipt bound to the exact deployed commit. A new deployment invalidates an earlier receipt. Scheduled work checks that receipt at each invocation. The deployment workflow activates only mechanical metadata/citation acquisition after the live verification. Scientific proposals do not become approved labels.

Use `scripts/enrichment/service_client.py verify`, then `activate`, or `deactivate` to pause. These operations use an HMAC key derived with a dedicated domain separator from the existing curator session secret; the session secret is never transmitted. Requests bind the body, timestamp and one-use nonce and reject stale commits. The service exposes only fixed domain operations, not general SQL, shell execution, arbitrary URLs or scientific publication.

`run` records a distinct, real-time extraordinary execution (never a fabricated past/future hourly slot), with at most 12 extraordinary attempts per UTC day. Scheduled work remains at most one job per actual UTC hour; the four supervisor checks per hour recover missed triggers without duplicating a job. An absent activation or changed commit results in a disabled runner, not a successful extraction.

Pause through the authenticated service or set the master flag false and deploy. Preserve the namespace, its SQL data and private KV source text. Do not delete the Durable Object namespace to roll back software. Cloudflare's native point-in-time recovery covers both its SQLite and KV contents; any restoration must be separately authorised and reconciled with immutable research receipts.

## Source documentation

Cloudflare Durable Objects SQLite storage API: https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/

Cloudflare Durable Objects limits: https://developers.cloudflare.com/durable-objects/platform/limits/

The service is bounded to the project's existing Workers plan. No paid AI endpoint or account upgrade is introduced by this adapter. These statements are not a guarantee about aggregate account billing from unrelated workloads.
