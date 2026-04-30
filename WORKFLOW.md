---
# NOTE: Symphony reference implementation is Linear-first.
# This file is setup-only and does NOT start autonomous execution by itself.
tracker:
  kind: linear
  project_slug: criminal-infiltration-review-orchestrator-23ae33cee32b
  api_key: $LINEAR_API_KEY

  active_states:
    - Todo
    - In Progress
  terminal_states:
    - In Review
    - Done
    - Canceled
    - Duplicate

polling:
  interval_ms: 30000

workspace:
  root: ~/code/symphony-workspaces/criminal_infiltration_in_legal_economy_review

hooks:
  after_create: |
    git clone --depth 1 https://github.com/colazeta/criminal_infiltration_in_legal_economy_review.git .
    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install --upgrade pip
  before_run: |
    git fetch origin
    git checkout main
    git reset --hard origin/main
  after_run: |
    echo "Run completed for Linear issue {{ issue.identifier }}"

  timeout_ms: 60000

agent:
  max_concurrent_agents: 1
  max_turns: 20

codex:
  command: codex app-server
  approval_policy: never
  thread_sandbox: workspace-write
  turn_timeout_ms: 3600000
  stall_timeout_ms: 300000

server:
  port: 4010
---

# Symphony workflow contract for this repository

## Scope
Execute only the assigned issue/task. Do not branch into unrelated repository improvements.

## Mandatory run mode (non-interactive)
1. Automated runs must be non-interactive: do not request elicitation and do not ask clarification questions.
2. If a decision is ambiguous, choose the conservative option and document the decision in the PR body or handoff note.
3. Never loop indefinitely on the same issue. If progress is blocked, terminate with a durable fallback artifact.

## Branching contract
1. Before making any file change, create and checkout a branch named:
   - `codex/<issue-id>-<short-slug>`
2. Branch creation is mandatory for every automated run.

## Durable final state contract
Every run must finish in one of these auditable states:
1. a pushed PR; or
2. a local commit plus `PR_DRAFT.md`; or
3. `docs/executions/<issue_id>_handoff.md` that explains the blocker when committing is unavailable.

Fallback expectations:
- If PR creation is unavailable, create a local branch, commit local changes, and write `PR_DRAFT.md`.
- If committing is unavailable, write `docs/executions/<issue_id>_handoff.md` with blocker details, attempted commands, and required human actions.

## Governance
1. Follow `AGENTS.md` if present.
2. Validate every domain against `docs/domain_allowlist_registry.md` before retrieval.
3. Never invent bibliographic metadata, identifiers, or screening outcomes.
4. Stage ambiguous records for human review; do not auto-promote them.
5. Do not introduce new external domains without explicit approval.
6. No automatic merge, no automatic state promotion beyond configured terminal states.

## Required output in PR
- Counts of records touched (added/updated/rejected/staged).
- Validation commands run with outcomes.
- Explicit unresolved decisions and required human action.
- Explicit statement if no external retrieval was performed.

## Run checklist
1. Restate task and touched files.
2. Create and checkout `codex/<issue-id>-<short-slug>` before edits.
3. Apply minimal patch set.
4. Run relevant checks.
5. End in a durable state (PR, or local commit + `PR_DRAFT.md`, or handoff file).
