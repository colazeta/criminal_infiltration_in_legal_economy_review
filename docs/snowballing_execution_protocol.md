# Snowballing Execution Protocol

Each execution must be fully documented for traceability.

## Required execution fields
- `execution_id`
- `execution_date`
- `execution_type` (seed, backward, forward, mixed)
- `input_set` (paper IDs / query sets)
- `feeds_used`
- `queries_used`
- `source_paper_ids`
- `retrieval_logs`
- `screening_stage`
- `reviewer`
- `notes`

## Mandatory process
1. Validate domains against `docs/domain_allowlist_registry.md`.
2. Run retrieval and log discovery events.
3. Deduplicate and update canonical paper registry.
4. Run screening stage and store decisions + exclusion reasons.
5. Update execution metrics and saturation status.

## Governance rule
If a new domain is needed, propose it in the registry candidate table and obtain user approval before any access.
