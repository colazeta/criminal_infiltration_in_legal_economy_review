# criminal_infiltration_in_legal_economy_review

This repository stores the protocol, registries, scripts, and outputs for a systematic snowballing literature review on criminal infiltration in the legal economy.

## Structure
- `docs/`: methodological protocol, codebook, execution protocol, domain governance, saturation metrics.
- `data/registry/`: core CSV registries for papers, discovery events, screening decisions, coding, and execution metrics.
- `data/raw`, `data/interim`, `data/processed`: pipeline data layers.
- `scripts/`: setup, seeding, deduplication, and metric-computation scripts.
- `outputs/`: generated tables, figures, and logs.


## Workflow order
1. Protocol setup
2. E0 seed-set construction
3. E1 database/API discovery
4. E2 backward snowballing
5. E3 forward snowballing
6. Repeated executions until saturation criteria are met


## Symphony orchestration
Symphony is an external orchestrator (not a Codex extension) that polls a tracker, creates isolated workspaces, and runs Codex in app-server mode.

For this repository:
- the reference setup is **Linear-first** (recommended);
- direct GitHub Issues orchestration requires a tracker adapter/wrapper.

See `docs/SYMPHONY_SETUP.md` for the decision tree, required states/labels, secret handling, and dry-run rollout steps.

