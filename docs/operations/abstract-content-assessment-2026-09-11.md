# Abstract content assessment — 11 September 2026

**Decision: fail. The general scientific extraction gate remains closed.** This is an observed content assessment, not a promised benchmark or a software-only test.

## Traceable inputs and assessment

Source commit: `8d296b2b812d430d90fc3b58bf8e98a3148acc89`.
Benchmark run: `34630484399`; three disjoint partitions, four distinct publications each.
Source artefacts: `10276466821`, `10275314664`, `10276376992`.
Result artefacts: `10276474063`, `10277180059`, `10276019750`.

All twelve original Crossref abstracts were read before generated outputs were opened. The source-first reference was saved at 18:09:10 UTC with SHA-256 `601c1b0eb0903ee55f490ea316aaa168563bc03d71e8ce7bc0d7f8bd2c41e822`; its separate receipt is retained in this directory. The generated results were first opened after that reference was saved. The completed field-by-field assessment was saved at 18:25:59 UTC with SHA-256 `9c2ace009ac6d6c6efd9f9f0aec8cc1d2c8c3cf1b46e9b6398ee5fee6a9c0b16`.

The assessor was a source-first ChatGPT analysis distinct from the Qwen generator, not an independent human gold standard. The private reference and assessment retain source hashes, field values, cited blocks, reasons and omissions; neither document nor any source quotation is published here. No canonical identity, eligibility, source text or scientific approval record was modified.

## Observed results

| Measure | Observed result |
| --- | ---: |
| Distinct real publications with matched abstracts | 12 |
| Structurally valid generated proposals | 11 |
| Failed cases retained in the denominator | 1 |
| Reported non-null fact fields assessed | 182 |
| Fields supported in their assigned field and cited blocks | 125 |
| Fields requiring correction | 57 |
| Supported field-quality fraction | 68.7% |
| Critical numerical, causal or label-origin field errors | 10 |
| Proposed framework labels assessed | 11 |
| Labels consistent with the source-first permissible set | 2 |
| Quantitative variable-use records returned | 3 |
| Returned variable operationalisations invented rather than reported | 3 |
| Benchmark proposals written to production | 0 |

A reviewed field passes only if **every clause**, its assigned role and all necessary cited blocks are supported. The duplicate paper/study research-question field is counted once. The 68.7% is therefore a conservative field-quality fraction, **not** an estimate of pure factual precision or universal model accuracy. Some failures are misassigned information, missing qualifiers, insufficient citation scope or false representations of missingness rather than fabricated prose. The ten critical errors are ten fields, not ten independent papers. Framework concordance is with the AI source-first reference; ambiguous permissible categories were retained rather than forced.

The third partition's first case did not produce a usable output. Its generic error does not establish a specific root cause. It remains a failed case, not an empty or omitted success.

## Repeated failure patterns

The assessment found eight invented author-limitation fields; eleven missing facts represented as reported strings such as “not specified”; three invented variable formulas; confusion between financial/predictive features and the source of true criminal-connection labels; incorrect observation/analysis units; omitted approximation qualifiers; and findings that were actually motivation, method construction or policy implications. Source citations sometimes stopped at a block boundary before the required evidence.

Framework placement was systematically unreliable: known-case descriptions were called screening, post-confiscation recovery was called screening, and financial effects were recast as causes of entry or prevention without support. These disagreements cannot be repaired by declaring every machine label acceptable.

Omissions also matter. Only one output contained variable-use records, despite named outcomes or financial indicators in multiple sources. Several outputs omitted explicit sample or case counts. A precision threshold cannot be met by silently replacing all difficult fields with null and concealing those omissions.

## Engineering response and bounded development re-test

The existing one-shot pilot is no longer automatically triggered by deployment. Manual dispatch remains available only as an explicitly unvalidated pilot. The mechanical :40 queue, alarms, catch-up watermark, sources and previous private proposals are unchanged; no iteration is cancelled or reset.

A separate focused extractor is introduced for **development benchmarking only**. The same pinned Qwen CPU model receives three independent source-grounded requests: content/data/methods; variables; and framework. Each receives the original blocks, not the previous stage's generated assertions. Total output cap is 3,700 tokens (2,200 + 1,000 + 500), at most three model requests per case with no automatic repair loop. Each request has a 300-second limit and 100-kilobyte response cap. The full request bundle is hashed. Standard runners and the existing expiring research-only encryption transport remain in use; no provider API key, production service, paid runner or new account is involved.

Critical literal fields (declared limitations, definition/operationalisation, sample size, period, variable name and formula) must appear exactly within the cited original blocks. Reported “not specified/unknown/N/A” placeholders are rejected rather than silently converted to success. This is an additional fidelity check, not proof that a passage belongs in a particular scientific field. Other facts and clinical rationale remain subject to content assessment. Outside-framework and insufficient-evidence abstentions are distinct existing states.

The same twelve-source pool may be re-tested with the unchanged prospective thresholds: at least twelve cases, at least 95% supported reported assertions, zero critical errors and no unresolved systematic framework error, with omissions reported separately. **A re-test after these corrections is development evidence, not an untouched holdout.** The earlier failed results are retained. No result from the new extractor has been assumed, and this engineering release does not activate scientific scheduling or approve labels.
