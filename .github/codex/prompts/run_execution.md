# Codex execution prompt (controlled mode)

You are running a single assigned task for `criminal_infiltration_in_legal_economy_review`.

## Must-follow constraints
1. Follow `AGENTS.md` instructions if present.
2. Execute only the assigned issue/task.
3. Use only authorised domains in `docs/domain_allowlist_registry.md`.
4. Never invent bibliographic metadata or identifiers.
5. Stage ambiguous records; do not auto-promote.
6. No automatic merge and no autonomous state promotion.

## Non-interactive orchestration contract
1. Do not request elicitation.
2. Do not ask clarification questions during automated runs.
3. If a decision is ambiguous, choose the conservative option and document it.
4. Never loop indefinitely on the same issue; terminate with a durable artifact.

## Branch creation requirement
Before editing files, create and checkout:
- `codex/<issue-id>-<short-slug>`

## Durable completion requirement
Every run must end with one of:
1. pushed PR; or
2. local commit plus `PR_DRAFT.md`; or
3. `docs/executions/<issue_id>_handoff.md` if committing is unavailable.

Fallbacks:
- If PR creation is unavailable: commit locally and write `PR_DRAFT.md`.
- If committing is unavailable: write `docs/executions/<issue_id>_handoff.md` with blocker, attempted commands, and required human actions.

## PR requirements
Include:
- counts of records changed and staged;
- validation commands with outcomes;
- unresolved decisions requiring human review;
- explicit statement if no external retrieval was performed.
