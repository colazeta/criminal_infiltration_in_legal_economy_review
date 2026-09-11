# Private extraction pilot: computational scope

Owner-directed implementation test, 11 September 2026. This amendment covers computational dependencies only; it does not change scholarly discovery providers, canonical identity, screening or publication.

## Authorised execution

Run one existing, privately retained author abstract through a local open-weight model on a standard Ubuntu GitHub Actions runner in this public repository. No paid/larger runner, model API, account upgrade or new credential is permitted. The model process listens on localhost and receives no service, repository or cloud credentials. The only authenticated remote operations are the existing narrow private enrichment service's packet and proposal operations.

The initial execution occurs on merge of the reviewed pilot implementation. Subsequent runs require explicit workflow dispatch or a reviewed change to its source/workflow. There is no model schedule in this release. Each invocation processes at most one abstract, capped at 14,000 characters without truncation, at most 2,500 output tokens, four findings, six variable descriptions and one proposed primary framework category. Multi-study inference is not supported by this pilot. Scientific batch extraction remains blocked pending calibration.

## Pinned computational dependencies

- Official `ggml-org/llama.cpp` release `b10333`, Ubuntu x64 CPU asset `llama-b10333-bin-ubuntu-x64.tar.gz`; SHA-256 `936ce04d98abe2a977e9dd2ff92659bb96947e136acee8f2bc3e21d8eaebbf23`.
- `unsloth/Qwen3-4B-Instruct-2507-GGUF`, `Qwen3-4B-Instruct-2507-Q4_K_M.gguf`; SHA-256 `3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597`.

The fixed public GitHub release and Hugging Face file locators may redirect to their ordinary public download CDNs. These software downloads carry no private text or credentials. The code verifies the complete hashes before extraction/execution and rejects an unexpected file, size or time overrun. No executable or weights are cached in the repository or published as an Actions artefact.

## Evidence and privacy gates

The source is read from the existing private store with hash-verified bytes. The complete original string is partitioned deterministically into blocks of at most 450 characters without dropping markup, punctuation or whitespace. The model selects only existing block IDs from a source-bound schema. It cannot invent quotations or offsets. The conversion verifies those IDs and derives exact UTF-16 source positions, consistent with the native validator. Reused blocks are deduplicated. A generated statement is still an unvalidated interpretation: an existing source location does not prove entailment or scientific correctness. Missing facts remain not_verifiable; they do not become negative claims. Framework assignments are analytical proposals, never author facts or approved labels.

This replaces the first pilot's model-transcribed quotation interface. It changes neither the native evidence-span contract nor the requirement for independently checked scientific accuracy. Evidence blocks may be broader than the minimal supporting phrase, so fine-grained localisation remains a review task.

The complete converted proposal must pass the existing closed schema and scope validator before private import. The importer verifies source bytes and writes immutable proposal history. Logs contain stage names, predefined engineering error codes, record counts and opaque proposal IDs only, never source text, prompts containing source text, model output, signatures or secrets. Model subprocess output is discarded; temporary private files have restricted permissions and are removed at exit. No source/proposal artefact is uploaded or committed.

A successful pilot establishes that private source → local model → grounded envelope → private proposal persistence can run. It is not the planned 12–18-paper scientific calibration, not a full-text extraction, not full variable coverage and not evidence that any paper belongs in the review.

## Observed mechanical activation preceding the pilot

Deployment run `34603354658`, job `103275779830`, on 11 September 2026 at 13:16 UTC verified exact commit `c2a6e524e60b810930c8d0a978ae8ec979979323`, private SQLite/KV readback and activation. The first successful mechanical run `592099ddeaa1ce348539f93bcead7667606f98e68cb59b5d710bb253d19b58cb` completed at 13:16:48 UTC. Readback showed 174 targets, one completed metadata job, two private sources, zero citation observations and zero proposals. Earlier failed registry attempts remain in the audit history. The deployed supervisor trigger is `7,22,37,52 * * * *`, with at most one scheduled mechanical job per UTC hour.

## First pilot result — preserved failure

Run `34604516684`, job `103279585169`, verified the private source at 13:28:45 UTC, both dependency hashes at 13:30:35 and a running local model at 13:30:38. It failed at 13:31:42 with a generic privacy-safe error and saved zero proposals. The original logs do not establish the exact failure cause. Deterministic source blocks address a fragile quotation interface, but are not retrospectively claimed to be the proven cause. The revised code adds non-sensitive stage and error categories to distinguish generation, conversion, native validation and private persistence. The last aggregate readback at 13:31:43 still showed the active mechanical runtime, 174 targets and two sources.

## Grounded-category correction — 11 September 2026

Pilot run 34606679010 failed with `pilot_framework_ungrounded` after parsing the model response. The generation schema now expresses two branches: a non-null category requires a non-null source-backed analytical rationale; abstention may leave the rationale unknown. The existing converter and source validator remain unchanged. This addresses a generator/validator mismatch, not a scientific calibration result.
