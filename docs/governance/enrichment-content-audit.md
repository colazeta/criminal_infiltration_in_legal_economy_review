# Independent content audit: bounded private transit

Owner-mandated implementation and content verification, 11 September 2026. This document authorises a narrow encrypted audit transfer, not publication or scientific acceptance. No authentication credential is created, exported, printed or included in a research packet.

The deployed minute-40 runtime and the unvalidated one-paper pilot remain distinct. Pilot run `34623072086`, job `103341483197`, reached model JSON parsing at 16:39 UTC but failed `pilot_summary_required`. The generation schema allowed null summary although the converter required evidence-backed summary. The correction makes summary a non-null fact in the generation schema and explicitly requests it in the prompt. Missing method, sample and other facts remain nullable. The acceptance validator still refuses a missing summary; no fabricated default or weakened evidence gate is introduced.

## Why the audit transport exists

Software checks can verify schema, source IDs and hashes but cannot demonstrate semantic accuracy. The owner requested independent checking of actual extracted content. The current working session does not possess the production authentication secret and must not receive it. A recipient-encrypted research packet allows the authorised content review without moving production credentials or publishing source text.

## Exact boundary

Each existing single-paper pilot may seal only its selected target metadata, the one verified abstract supplied to its model, model output, converted proposal and persistence receipt. It does not read or export a browser session, process environment, account credential, repository credential, other paper or unrelated reviewer note. This is not an additional paper-processing run or an unrestricted database export.

The only public artefact is authenticated ciphertext (at most two megabytes of input), encrypted before writing the upload file. Plaintext temporary files remain mode 0600 inside the already isolated temporary directory and are removed. The upload step names that single `.sealed.json` file explicitly, never a directory or wildcard containing other runner files. No private text enters workflow logs, public source, issues or Pages. Ciphertext retention is one day.

`config/enrichment-audit-recipient.json` pins the public X25519 recipient and its SHA-256 fingerprint. The newly generated matching private transport key exists only in this working session, outside GitHub and Cloudflare, and is not an account credential. Recipient expiry is 12 September 2026 at 00:00 UTC. After expiry no new audit transfer occurs; private proposal persistence can continue independently. A changed recipient requires a reviewed source change.

Encryption uses the Node.js built-in X25519 key agreement, HKDF-SHA-256 and AES-256-GCM, with fresh ephemeral keys, salt and nonce. The protocol and recipient fingerprint are authenticated additional data. No third-party cryptographic service or new package is invoked. Implementation reference: https://nodejs.org/docs/latest-v22.x/api/crypto.html . The transport envelope is a temporary cryptographic wrapper, not a new governed scientific-record field or an ontology change.

## Verification and limits

Three new Python tests verify agreement between summary generation and the unchanged acceptance gate. Three JavaScript tests cover exact roundtrip, recipient isolation, modified ciphertext rejection, fresh encryption, expiry and bounds. A synthetic cross-runtime Node-encrypt/Python-decrypt test also passed without using real papers or production credentials. Full local regression: 430 Python tests, 140 JavaScript tests and all mandatory AGENTS.md repository/ontology/build/site/syntax checks passed. The inspected corpus remains 174 candidates and zero canonical/published works; ontology 0.4.1 is unchanged.

An encrypted packet is not evidence that a proposal was saved or correct. Check its actual receipt and source hashes, then inspect content independently. The initial failure case is development evidence, not a held-out benchmark. The heterogeneous 12–18-paper scientific benchmark and acceptance decision remain outstanding. No content-quality score, gold label, full-text coverage or recurrent scientific execution is claimed by this release.
