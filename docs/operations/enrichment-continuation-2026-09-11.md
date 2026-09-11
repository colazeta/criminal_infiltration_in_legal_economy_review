# Enrichment continuation — 11 September 2026

Owner mandate: continue the existing system, retain every due :40 ticket and verify scientific content before general model activation. This change does not approve papers, labels or publication.

## Verified starting point

The inspected main commit is `8acdd497762caf885508724f962858806867a8e2`, with ontology 0.4.1 and the existing CILE-HOUR40-1 queue. Migration 0004 and its three scheduling tables are already present. No new queue, namespace, database or first-slot epoch is created by this continuation.

Pilot run `34623072086`, job `103341483197`, reached `model_json_parsed` at 16:39 UTC and then failed with `pilot_summary_required`. Its final private aggregate readback showed: enabled mechanical runtime, 174 targets, three sources, zero citation observations and zero proposals. The schedule first slot was 16:40 UTC, so the absence of tickets in that earlier readback was not itself a missed run.

## Changes and acceptance checks

The generator allowed a null summary although the unchanged converter required a supported summary. The generation schema now requires the summary object and the prompt explicitly describes that requirement. The exact source-bound JSON schema is supplied to the model as well as to the constrained decoder. In llama.cpp, the output grammar alone does not show the schema to the model (official `b10333/grammars/README.md`, JSON-schema support). The 16,384-token local context accommodates the explicit schema; the 14,000-character abstract and 2,500-output-token limits are unchanged. The provenance hash now covers the exact request, source blocks and decoding parameters.

The scheduler now reconciles a previously persisted failed paper receipt after acknowledgement loss, just as it already reconciled a successful receipt. A confirmed failed paper operation must not be silently replaced by work on another paper. Its failure remains visible. Failures without a selected paper remain recoverable pending tickets.

The existing readiness workflow becomes an hourly observer at :45 and runs after deployment. It reads actual scheduling receipts and checks the persisted watermark. It never processes a paper, activates a model or approves scientific content. The :40 Cloudflare trigger, persistent tickets, catch-up watermark and alarms remain the delivery system; GitHub's observer is not a substitute scheduler.

Regression tests must cover mandatory source-backed summary, model-visible schema, exact request hashing and acknowledgement loss after a failed paper operation, together with the existing duplicate/overlap/crash/catch-up tests. Full repository, ontology, Python, JavaScript and site validation must pass before merge. The one-off public-source snapshot workflow is removed before release.

## Unchanged scientific gate

A successful one-paper pilot is only a private unreviewed proposal with abstract-only coverage. It does not establish full-text access, completeness of methods/variables, a 12–18-paper benchmark, or accuracy of the clinical classification. General scientific scheduling must remain blocked until independent reference extractions, field-level errors/omissions and coding disagreements have actually been checked. Do not manufacture benchmark labels, counters, source material or historical :40 executions. Observe subsequent real tickets separately from controlled-clock software tests.
