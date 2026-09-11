# Enrichment continuation — 11 September 2026

Owner mandate: continue the existing system, retain every due :40 ticket and verify scientific content before general model activation. This change does not approve papers, labels or publication.

## Verified starting point and concurrent release

The inspected starting main was `8acdd497762caf885508724f962858806867a8e2`, ontology 0.4.1, with the existing CILE-HOUR40-1 queue. Migration 0004 and its three scheduling tables were already present. No new queue, namespace, database or first-slot epoch is created by this continuation.

Pilot run `34623072086`, job `103341483197`, reached `model_json_parsed` at 16:39 UTC and failed with `pilot_summary_required`. Its private aggregate readback showed: enabled mechanical runtime, 174 targets, three sources, zero citation observations and zero proposals. The first scheduled slot was 16:40 UTC; no tickets in that earlier readback was therefore not itself a missed run.

While this continuation was being prepared, main advanced to `242824c1d5d445ab8782db741f43743782eccc32`. Its mandatory-summary correction, confidential audit transport and associated workflow/tests/configuration were inspected and preserved. The merge reconciliation starts from that full main tree and layers only the continuation changes; it does not overwrite the concurrent audit work.

The ensuing production pilot `34624868660`, job `103347411586`, saved private proposal `d2401868e8cb4795d66eac21af2062c6afed12f4d618431e8d1e34ed6bceeffd` at 17:00:18 UTC. Logs show abstract-only coverage, three proposed findings, zero variable uses, a proposed framework category and three source blocks. These are observed structural counts, not verified scientific content. Final aggregate readback at 17:00:20 UTC showed one persisted proposal, 174 targets and three sources. No content audit or benchmark score is inferred from that successful pilot.

The same readback showed the real 16:40 UTC ticket: materialised at 16:40:00.001, finished at 16:40:00.095, failed with `identifier_resolution_required`, with next slot 17:40 UTC. This demonstrates a recorded real scheduled attempt, not successful paper enrichment. The failure is retained and must not be relabelled as completion.

## Changes and acceptance checks

The generator allowed a null summary although the unchanged converter required a supported summary. Generation now requires the summary object and the prompt explicitly describes that requirement. The exact source-bound JSON schema is supplied to the model as well as to the constrained decoder. In llama.cpp, the output grammar alone does not show the schema to the model (official `b10333/grammars/README.md`, JSON-schema support). The 16,384-token local context accommodates the explicit schema; the 14,000-character abstract and 2,500-output-token limits are unchanged. The provenance hash covers the exact request, source blocks and decoding parameters.

The scheduler now reconciles a previously persisted failed selected-paper receipt after acknowledgement loss, just as it already reconciled a successful receipt. A confirmed failed paper operation must not be silently replaced by work on another paper. Its failure remains visible. Failures without a selected paper remain recoverable pending tickets.

A separate `enrichment-observer.yml` reads actual scheduling receipts after deployment and hourly at :45 and checks the persisted watermark. It never processes a paper, activates a model or approves scientific content. The existing `enrichment-readiness.yml` remains manual-only, with its provider checks unchanged. The :40 Cloudflare trigger, persistent tickets, catch-up watermark and alarms remain the delivery system; GitHub's observer is not a substitute scheduler.

Regression tests cover mandatory source-backed summary, model-visible schema, exact request hashing, acknowledgement loss after a failed paper operation and read-only observer separation, together with the existing duplicate/overlap/crash/catch-up tests. Full repository, ontology, Python, JavaScript and site validation must pass before merge. The one-off public-source snapshot workflow was removed before release.

## Unchanged scientific gate

A successful one-paper pilot is only a private unreviewed proposal with abstract-only coverage. It does not establish full-text access, completeness of methods/variables, a 12–18-paper benchmark, or accuracy of the clinical classification. General scientific scheduling remains blocked until independent reference extractions, field-level errors/omissions and coding disagreements have actually been checked. Do not manufacture benchmark labels, counters, source material or historical :40 executions. Observe subsequent real tickets separately from controlled-clock software tests.
