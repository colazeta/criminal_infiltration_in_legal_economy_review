# Symphony setup guide (for this repository)

## Important framing
Symphony is an external orchestrator service. It polls a tracker, creates an isolated workspace per issue, runs Codex in app-server mode, and expects Codex to produce a PR.

## Decision point: tracker mode
The reference implementation is **Linear-first**. For this repo there are two supported setup paths:

### A) Linear-first (recommended)
Use Linear as control plane and GitHub as code/artifact plane.

Flow:
1. Linear issue enters `codex-ready` state.
2. Symphony polls Linear and creates isolated workspace.
3. Codex runs against this repo in that workspace.
4. Codex opens GitHub PR.
5. Human review drives merge and any domain/record approvals.

Required environment variables (never commit to repo):
- `LINEAR_API_KEY`
- `GITHUB_TOKEN`
- `OPENAI_API_KEY`

Required Linear config:
- `project_slug` set in `WORKFLOW.md`.
- States at minimum: `codex-ready`, `human-review`, `done`.
- Labels (recommended): `execution`, `needs-domain-approval`, `ambiguous-records`, `human-review`.

Mapping guidance (Linear -> GitHub PR):
- Linear issue identifier and title should appear in branch and PR title/body.
- PR body should include: record counts, validation results, unresolved decisions.

### B) GitHub Issues-first (advanced)
If you must orchestrate directly from GitHub Issues, this is **not** the reference path.
You need a tracker adapter/wrapper that maps GitHub issue events/states to Symphony tracker semantics.

Minimum adapter capabilities:
- poll open issues and state labels;
- claim/lock an issue;
- create one workspace per issue;
- post status back to issue and/or labels;
- handle terminal transitions and retries.

## Safety defaults for this repo
- Keep `max_concurrent_agents: 1` until dry-run is stable.
- No autonomous execution for E1R1+ until a successful technical dry-run issue is completed.
- Keep ambiguous bibliographic records staged for manual review.
- Domain expansion requires explicit approval per `docs/domain_allowlist_registry.md`.

## Bring-up checklist
1. Complete repository agent-readiness files first:
   - `AGENTS.md` (if used)
   - issue templates
   - validation actions
   - `docs/NEXT_ACTION.md`
   - `.github/codex/prompts/run_execution.md`
2. Set env vars in runtime secrets manager.
3. Update `WORKFLOW.md` with real `project_slug` and verify Linear states.
4. Dry-run on a small technical issue (documentation or validation script), not a production execution.
5. Review PR output quality before enabling broader runs.
