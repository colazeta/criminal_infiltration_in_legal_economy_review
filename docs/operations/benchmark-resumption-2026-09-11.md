# Benchmark resumption — 11 September 2026

This continues PR #332 and the owner-requested content validation. The production queue, first-slot epoch, current :40 tickets, ontology, source matching, extractor and native validator are unchanged.

## Observed interruption and scope

The working session that held the former benchmark transport private key was replaced. That key was deliberately never in the repository or a workflow. Existing ciphertext cannot now be used for content scoring in this session. The former batch `34626941549` is left running, not cancelled. Its eventual structural results can be reported, but they are not an independently checked content benchmark. No attempt is made to weaken encryption or reconstruct a missing key.

A separate staged transfer on `implementation/enrichment-content-benchmark`, run `34628721934`, failed before applying any source change: its base64 payload was malformed. This continuation uses the existing readable benchmark code from PR #332, not that incomplete patch. No migration or production receipt is taken from the failed transfer.

## Bounded repeat

The benchmark keeps the same declared pool of 24 DOI-bearing registered records, the same source-bound model request, original-source hashes, native validator, CPU model and prospective assessment thresholds. Three disjoint partitions use every third DOI, with at most eight anonymous Crossref requests and six analysed abstracts each. Each partition requires at least four matching abstracts: all three successful partitions therefore yield 12–18 distinct cases. Availability and the changed partition selection are reported; this is a repeated convenience-pool assessment, not a new independent holdout.

Sources are collected and encrypted before inference. Source-only ciphertext is uploaded first, so reference assessments can be saved and hashed before generated assertions are opened. A restricted local input file is retained only on that runner for inference and is removed in the finally/cleanup paths. The existing audit transport is reused with a newly generated, session-held recipient expiring at 12 September 00:00 UTC. This changes no Cloudflare, GitHub or model-account credential. Only named source/result ciphertext files are uploaded, one pair per partition, for one day. No private production service is accessed. No raw source, generated assertion or credential is printed or committed.

The workflow preserves any currently running batch (`cancel-in-progress: false`). Its three standard CPU jobs have `fail-fast: false`; a failed case/partition cannot cancel another. Model results are encrypted and checkpointed after each case. The old batch and new batch cannot share an execution ticket, overwrite production evidence or hold the production scheduler lock.

## Acceptance

The six added synthetic tests verify partition uniqueness/coverage, integrity checks, insufficient-source reporting, restricted local files and the source-first secret-free workflow. Full exact-PR repository/ontology/Python/JavaScript/archive/site checks remain required. No model call or content accuracy result is asserted by this code change.

Assessment follows `docs/methodology/abstract-content-benchmark.md`: separately saved source-only references, all non-null assertions checked for entailment, critical numerical/causal/identity claims, omissions and framework disagreements. Structural validity never opens the scientific calibration gate. A pass could support only abstract-level proposals with the tested model and request, not full-text or exhaustive-variable extraction, citation completeness, accepted clinical labels or publication.
