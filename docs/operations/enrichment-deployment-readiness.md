# Deployment readiness is not paper completion

Engineering follow-up, 11 September 2026. No corpus, source, scientific decision or ontology concept changes.

## Observed production results

PR #328 was merged as `4586070ad763416c3f1e20b79e69eada5643635c`. Deployment run `34621624748` passed the full 421-Python/137-JavaScript regression suite, published the Worker and both supervisor and `40 * * * *` triggers. Its first private check received `409:stale_deployment`, despite the public version endpoint already reporting the new commit. The existing exact-deployment check prevented activation of the mismatched instance.

The second attempt, job `103338474119`, at 16:28:33 UTC, verified the exact private commit and storage readback, then activated the persistent schedule. The returned plan was `cile-hour40-v1`, protocol `CILE-HOUR40-1`, first_slot and next_slot `1789144800000` (11 September 2026, 16:40:00 UTC), with zero minute-40 iterations yet. The existing storage contained 174 targets, three source receipts, two completed metadata jobs and no scientific proposals or citation observations. No previous hour was backdated into the new schedule.

The following random mechanical paper job failed with `identifier_resolution_required`, correctly retaining its failed receipt. This was not a deployment or schedule-activation failure. However, including it in the deployment workflow made the whole workflow fail and prevented the independent pilot workflow from starting. The failed history must remain visible.

## Corrected release check

`scripts/enrichment/deployment_check.py` verifies the exact expected commit, private storage and schedule contract. Its optional activation is the existing signed activation operation. It does not execute any paper job and explicitly reports `paper_work_executed_by_check=false`. The expected commit is fixed throughout; only the exact stale-deployment verification error is retried, at most 19 attempts with ten-second waits. Authentication, storage and contract failures are not concealed or converted into success. No secret or source body is logged.

A readiness success means the versioned runtime and schedule are ready, not that a paper, reference list or scientific extraction is complete. The authenticated console and independent runtime/pilot receipts retain their individual failures. The existing service CLI continues to exit unsuccessfully when a requested `run` reports failure; that safeguard is unchanged.

Cloudflare documents short-lived version skew between Workers and globally unique Durable Objects during eventually consistent code updates: https://developers.cloudflare.com/durable-objects/platform/known-issues/#code-updates . This is consistent with the first observation, not proof of an otherwise unobserved account configuration.

## Verification boundaries

Six new synthetic tests check fixed-commit retries, finite retry budgets, refusal of authentication/storage errors, retained paper failures, disabled/mismatched schedule rejection and invalid expected versions. Locally, all 427 Python tests and 137 JavaScript tests and the full mandatory repository/ontology/build/site/syntax checks passed. Public candidates remain 174, canonical works zero, publication rows zero; saturation remains NOT SATURATED.

Actual minute-40 execution receipts, readable private proposals and the heterogeneous independently checked content benchmark still require observation. Neither the readiness result nor the existing abstract-only pilot supplies calibrated scientific accuracy or approves a framework category.
