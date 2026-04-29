# NEXT_ACTION

## Current phase
Symphony setup and governance hardening (no autonomous production runs).

## Next concrete steps
1. Decide tracker mode:
   - Linear-first (recommended), or
   - GitHub Issues via custom adapter.
2. If Linear-first, set `LINEAR_API_KEY` and `project_slug`, then verify states:
   - `codex-ready`
   - `human-review`
   - `done`
3. Run one dry-run technical issue (docs/validation only).
4. Review PR quality for:
   - domain compliance;
   - staged ambiguities;
   - validation completeness.
5. Only then evaluate enabling E1R1 automation.

## Explicitly deferred
- Autonomous E1R1 execution.
- Automatic promotion/merge flows.
