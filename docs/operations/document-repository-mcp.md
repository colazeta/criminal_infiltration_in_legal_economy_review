# Document repository and read-only MCP

This implements a candidate-bound document repository in the existing private
SQLite Durable Object and content-addressed KV. It is a **release candidate**:
the production preservation failure described in the
[implementation audit](../architecture/document-repository-implementation-audit.md)
still blocks deployment and live backfill. Endpoint examples below describe the
new code; they are not claims that the endpoints are already deployed.

## Authority, identities and storage

The normative contract is `ontology/cile-review-profile.yaml` version 0.4.4.
`ontology/modules/document-repository.json` maps every new SQL column to it.
Migration 0009 is additive and its bundled SQL digest is validated before use.
The physical dictionary now contains 86 tables and 660 columns; 53 tables belong
to the configured enrichment store. The remaining V2 tables are prepared, not
verified production storage.

Candidate identity and existing input hashes remain unchanged. `paper_id` is
null for the present candidate population; callers use `candidate_id` as the
tool's lookup argument. Canonical work/alternate-identifier lookup and the
broader CSV/Pages/GitHub authority cutover are **not implemented by this change**.
Do not treat DOI/title matching, a document version, an OCR result or a proposal
as a new canonical work or a scientific inclusion decision.

| Entity | Representation and provenance |
|---|---|
| Manifestation | Stable hash of target/input/source URL/version; multiple byte receipts can bind to one embodiment. |
| SourceDocument | Existing immutable receipt: original PDF digest, size, source, time, retention basis, licence, attribution and visibility. Bytes are stored once per SHA-256. |
| ExtractedDocument | Source text hash plus PDF hash, parser attestation, native/OCR method, extractor version, page count and protocol. |
| Page/chunk | Offsets into the exact existing UTF-16 source string; page and chunk IDs are deterministic. No copied full-text database. |
| EvidenceSpan | Existing proposal-scoped source ID and offsets, joined to verified pages on demand. A revision is required when resolving public aliases. |
| Retrieval index | Derived lexical postings; no vector service or model. Bibliography cache is the existing register-sync projection. |

Native extraction uses Poppler `pdfinfo` and `pdftotext -layout`. PDF signature,
EOF, parser acceptance, encryption, page count, text quality, source and byte
digests are checked. If native extraction fails, Tesseract OCR processes the
whole document with its own method/version and text hash. Default OCR language
is `eng`; `extract_document(..., ocr_language='ita')` and `deu`, `fra`, `spa` are
supported when the corresponding language pack is installed. OCR is never mixed
silently into a native extraction. The signed maintenance service trusts the
parser attestation produced by this runner; arbitrary clients cannot attest a
PDF through the public API or MCP.

Existing source strings and evidence offsets are immutable. If re-extracting a
legacy PDF produces different text, backfill reports
`document_legacy_extraction_differs`. A curator must reconcile a new source and
its evidence; the runner cannot rewrite the old assessment.

## Rights and reader

`site/document-library.html` searches title/DOI, lists available versions, shows
the original PDF in the browser's maintained PDF renderer, navigates pages and
shows extracted page text alongside the existing structured research sheet.
Evidence links carry candidate, evidence alias and research revision. The
private reader remains in the existing authenticated curator console.

Acquisition permission and redistribution permission are separate. Public
bytes, full-text passages and page resources all require the latest rights
assertion for those bytes: public visibility, positive verification, and the
existing exact CC BY 4.0 / CC BY-SA 4.0 / CC0 licence allowlist. A later private
assertion removes public access through every new path. Other copies expose
only safe source/version/licence/attribution metadata publicly. No storage key,
private document identifier or private source body is returned.

The completion gate additionally requires every full-text source used by an
assessment to resolve to readable retained bytes and a verified page index.
The archive does not yet attest an independent `Assessment Completed` state; that value remains null even when validation acceptance is recorded. Acceptance is returned separately. Legacy completion receipts are preserved; they may be withheld until this new
prerequisite is satisfied. An acquisition, extraction, analysis proposal and
accepted assessment remain separate states.

## HTTP and MCP connection

After release, the public service is on the existing Worker origin:
`https://criminal-infiltration-curator.colazeta-research.workers.dev`.

| Route | Access and role |
|---|---|
| `/api/public-document-library` | Public GET: search, document metadata, verified page or evidence locator. |
| `/api/public-paper-assets` | Existing public PDF reader with HEAD/Range support and the same current rights gate. |
| `/mcp` | Public, stateless MCP Streamable HTTP; no credential. |
| `/api/paper-enrichment/document-library` | Existing curator authentication; private document reads. |
| `/api/paper-enrichment/mcp` | Existing curator authentication, same-origin and CSRF checks; private MCP reads. |

The private route uses the existing curator bearer session, allowed origin and
CSRF header. It is intended for the curator application. It does **not** provide
an OAuth discovery/login flow for arbitrary external MCP clients. Do not put a
curator session or machine-service secret into public client configuration.

Configure a client that supports Streamable HTTP with the public `/mcp` URL.
POST `application/json` with `Accept: application/json, text/event-stream`.
Initialize using protocol `2025-11-25`; `2025-06-18` and `2025-03-26` are also
accepted. Subsequent requests should include `MCP-Protocol-Version`. There is
no session ID or persistent SSE stream; GET returns 405 and supported
notifications return 202. Unexpected browser origins are rejected.

Example initialization body:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"cile-reader","version":"1.0"}}}
```

Example bounded read:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_full_text","arguments":{"query":"procurement company","top_k":5}}}
```

| Tool | Parameters and limits |
|---|---|
| `search_papers` | Title/DOI query, author, year interval, geography, method, dataset, variable, framework category, review status, source coverage; max 25 records, candidate cursor. |
| `get_paper` | One current candidate lookup; bibliography, versions and bounded research overview. |
| `search_full_text` | Max 300 characters / 12 unique tokens, optional max 20 candidate IDs, `top_k` 1–20. All query tokens must occur in the same chunk. |
| `get_evidence` | Candidate, 1–10 evidence IDs and exact revision from `get_review_data`; up to 800 source characters per span. |
| `get_review_data` | Candidate and selected fields; collection offset and limit 1–20; revision required beyond the first page. |
| `compare_papers` | Up to 5 candidates and selected recorded fields; max 5 items per collection; no generated ranking. |
| `get_corpus_stats` | Receipt counts with explicit scope. Canonical totals and unattested completion are not inferred. |

Resources include `cile://taxonomy`, `cile://methodology`, `cile://corpus/stats`,
`cile://papers/{paper_id}`, and its `assessment`, `manifestations`, `fulltext`,
`findings`, `methods`, `variables`, `evidence` views. A page resource is
`cile://papers/{paper_id}/fulltext/{document_id}/{page}`. The fulltext root is a
manifest, not an unrestricted corpus export. Use tool pagination for complete
recorded collections. Source text is labelled untrusted data.

Tool schemas disallow unknown fields and bound identifiers, arrays and numbers.
The read service has no network fetch, URL acquisition, arbitrary SQL, storage
path or write operation. Transport/request failures are closed codes without
private traces. Tool annotations advertise read-only behavior; the actual
implementation enforces it independently of those annotations.

## Limits and resumable audit

| Bound | Current value |
|---|---|
| PDF / exact source | 4 MiB PDF; 2 million source characters in the private store. |
| Extraction | 500 pages native; OCR at most 30 pages, 120 dpi. |
| Index | 1,800 UTF-16 units/chunk; at most 2,500 chunks / 60,000 postings per document. |
| Preservation admission | Existing 100,000 rows/table and 16 million JSON-character aggregate snapshot. Actual post-write population is checked transactionally; excess rolls back the index. |
| Public source output | Search passage 500 characters; evidence 800; one page at most 32,000. |
| MCP envelope | Request 16 KiB; serialized result 180,000 characters; no unbounded bulk resource. |
| Coverage runner | 25 candidates/page; 1–20 pages per invocation with explicit continuation offset. |

The preservation budget may prevent a large-corpus backfill. This change does
not waive it or claim that 294 full texts fit it. A measured, reviewed extension
of the backup protocol is needed if `document_preservation_capacity` occurs.
Local synthetic tests do not establish production latency or capacity.

Use the existing signed-service environment and an exact deployed commit.
Write the private inventory outside the public checkout:

```sh
python3 -m scripts.enrichment.document_coverage \
  --expected-commit "$GITHUB_SHA" --pages 20 \
  --output "$RUNNER_TEMP/cile-document-coverage-before.json"
python3 -m scripts.enrichment.document_coverage \
  --expected-commit "$GITHUB_SHA" --pages 20 --reindex \
  --output "$RUNNER_TEMP/cile-document-backfill.json"
python3 -m scripts.enrichment.document_coverage \
  --expected-commit "$GITHUB_SHA" --pages 20 \
  --output "$RUNNER_TEMP/cile-document-coverage-after.json"
```

Use `--offset` from `next_offset` and `--revision` from `identity_revision` if a run is incomplete. Candidate/input changes invalidate continuation. Counts describe per-candidate observations during the run, not an atomic archive snapshot. Output uses exclusive
creation, mode 0600 and rejects paths inside the public repository. Reindexing
reads retained bytes, never a fresh URL, and replays deterministic receipts.
New acquisitions continue through the existing source allowlist, input/identity
checks, B-shard claim and retention runner; the audit does not add a scheduler.
Never publish the private report or upload it as a public workflow artifact.

## Release evidence still required

1. Resolve the existing predeploy backup catalogue HTTP 503 and pass the archive
   preservation/restore gate. No production mutation is justified by local tests.
2. Validate migration 0009 on the preserved deployed archive and its exact commit.
3. Audit, backfill eligible retained PDFs, rerun the inventory, and record actual
   acquired/indexed/public/private/unresolved/accepted counts. Record each
   inaccessible or incompatible document with its blocker.
4. Exercise the viewer, evidence links, rights withdrawal and all seven MCP
   tools against deployed data; record cold/warm query timings and byte limits.
5. Complete the separately governed canonical identity/authority cutover and
   external private-client authentication before claiming the full requested
   platform transition is complete.
