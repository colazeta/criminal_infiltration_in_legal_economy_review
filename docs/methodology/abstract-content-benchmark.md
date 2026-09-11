# Abstract content benchmark — 11 September 2026

This is one stage of the owner's requested 12–18-paper calibration, not a substitute for full-text testing or approval of a recurring scientific extractor. No benchmark result is assumed in this specification.

## Prospective scope

Test the exact model request and converter in the current abstract-only pilot on up to 18 existing registered publications. A fixed pool of 24 unique DOI-bearing records is listed in `scripts/calibration/paper_content_benchmark.py`; stop after 18 identity-matched abstracts, and do not run the model with fewer than 12. The initial AER development paper is excluded. The pool deliberately spans enforcement effects, corruption and intermediaries, network/risk methods, accounting, financial indicators, administrative interventions, business recovery, food-sector involvement and theoretical work. These are selection topics, not inferred study designs or clinical labels. Actual methodological heterogeneity must be checked from the retrieved sources.

One unauthenticated Crossref request per selected pool entry is permitted, at most 24, one second apart, bounded to three megabytes and 20 seconds, with redirects refused. DOI and normalised title must agree with the existing registry. Missing abstracts, mismatches and provider errors remain explicit. Availability determines the analysed subset and limits the generalisability of the test. No new publication enters the register, canonical corpus or approved bibliography.

The exact returned abstract is retained, including deposited markup. Its hash, retrieval time, provider and registered ID accompany the source. Benchmark IDs are explicitly namespaced `CILE-ABSTRACT-BENCHMARK-1` and are not production-source or production-proposal receipts.

## Execution and confidentiality

Use the already pinned local llama.cpp/Qwen3-4B CPU dependencies and the current source-bound prompt/decoder schema, 16,384-token context, maximum 14,000 source characters and 2,500 output tokens. There is no model API, Cloudflare account request, production service call, private database access, credential or paid runner. The engine listens only on localhost, receives no account credentials and is terminated after the bounded batch. The test does not modify or block the production :40 queue.

The previously reviewed `seal-audit.mjs` transport encrypts source-only packets and model-result packets separately to `config/enrichment-benchmark-recipient.json`. This is a newly generated transport recipient, not an account credential. Its private key remains only in the current working session. It does not replace the existing single-paper audit recipient. Expiry at 12 September 2026 00:00 UTC prevents later automatic transfers; renewal requires a reviewed change. Only two explicitly named ciphertext files may be uploaded, for one day. No source text or generated assertion appears in logs, public data, issues or source control. Model-result ciphertext is atomically checkpointed after each case, retaining earlier cases after a later failure.

A reviewed main change to the benchmark script/workflow triggers one batch; later executions require manual dispatch or another reviewed change. There is no recurrent benchmark or model schedule. Forty-five minutes is the outer job limit; interruption must not be represented as 18 completed cases.

## Reference construction and assessment

Before inspecting generated assertions, read the source-only packet and record a separate reference assessment for each paper. Identify explicitly stated question, data, sample, geography/time, method, operationalisation, principal findings and limitations; record plausible clinical categories and ambiguity. Keep unavailable details as unavailable. Save the reference file and its hash before opening model results. The reference is an analyst check independent of the Qwen generator, not a claimed human-reviewed gold standard.

Compare every generated non-null scientific assertion with the exact source. Report counts of supported, partly supported, unsupported and unverifiable assertions, identifying the affected fields. Numerical estimates, sample sizes, causal claims and the source of an infiltration label require especially strict support. Separately record salient source facts omitted by the extractor, invalid JSON/schema cases, source-span failures and framework disagreements. Field-level missingness must not be called a factual error merely because the full paper may contain more information.

For an abstract-only activation recommendation, require at least 12 analysed papers, no unsupported critical numerical/causal/identity claim, at least 95% fully supported reported assertions and no unresolved systematic framework error. Report denominators and uncertainty; do not convert a small convenience benchmark into a universal accuracy claim. These thresholds are prospective acceptance criteria, not observed results. Failure requires correction and further testing, not a weakened validator or favourable recoding. Retesting the same papers is development evidence, not new independent validation.

Even a pass would support only the tested abstract-level scope and exact model/prompt. Full-text extraction, multi-study papers, exhaustive variable coverage, inaccessible sources, citation-network completeness and production recovery remain separate tests. Benchmark structural success alone must never change `blocked_pending_calibration`, approve a framework label or enable scientific publication.
