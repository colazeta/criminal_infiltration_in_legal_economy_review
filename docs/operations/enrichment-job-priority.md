# Mechanical work priority

Owner-directed continuation, 11 September 2026. This is an execution-order change, not identity resolution, a new field, a new schedule or scientific approval.

The first actual :40 ticket was delivered but selected a record without the DOI required by both configured adapters. That record and its failed receipt remain intact. To avoid consuming successive hourly slots on known-unusable inputs while other work is available, due jobs whose registered input contains a DOI are considered before due jobs with an empty DOI. Within each group, oldest due time and the existing deterministic target/kind order remain unchanged.

This is only a priority hint. A non-empty DOI is not automatically valid or canonical. The adapter still checks the DOI syntax and exact DOI/normalised-title agreement before acquiring evidence. No identifier is inferred from a title or written to a candidate by this change. Jobs that are not yet due cannot run early. No new provider or paid fallback is enabled.

Records without a DOI remain in the private target register and queue. Their jobs are not marked complete or deleted. When no due DOI-bearing work is available, the existing explicit identifier-resolution block remains observable. A corrected register input retains prior snapshots and creates its normal new version. No historical failure is rewritten.

This priority improves acquisition throughput under the existing one-operation-per-ticket budget. It does not solve the unresolved-identifier backlog or guarantee full abstract/citation coverage. Source-resolution work remains a separate required extension. The hourly plan, tickets, leases, retry deadlines, model calibration gate and immutable scientific proposals are unchanged.

Synthetic regression tests demonstrate that a due DOI-bearing paper is selected ahead of an older DOI-less paper, both targets remain registered, no proposal is invented and no provider call is made before its due time. Production effects must be checked in actual subsequent ticket receipts; software tests are not such receipts.
