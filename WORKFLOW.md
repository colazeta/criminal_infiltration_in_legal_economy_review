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

## Run checklist
1. Restate task and touched files.
2. Apply minimal patch set.
3. Run relevant checks.
4. Open PR summary with counts, validations, unresolved decisions.
