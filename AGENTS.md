# AGENTS.md — Literature-review automation governance

This file governs all automated and semi-automated work in this repository.

## Mission boundary
- Preserve scientific traceability and reproducibility.
- Maintain the public literature archive as the primary repository product.
- Prefer conservative actions over fast actions when evidence quality is uncertain.

## Hard prohibitions
1. Never invent bibliographic metadata, identifiers, abstracts, citations, or screening outcomes.
2. Never auto-promote ambiguous records into official seed/registry status.
3. Never access non-authorised domains for discovery or enrichment.
4. Never commit secrets (`LINEAR_API_KEY`, `GITHUB_TOKEN`, `OPENAI_API_KEY`, etc.).
5. Never run production bibliographic discovery tasks unless explicitly requested by issue scope.
6. Never publish draft, pending, rejected, duplicate, or unresolved records as included literature.

## Scope discipline
- Execute only the assigned issue/task.
- Do not perform unrelated cleanup or broad refactors.
- If issue scope conflicts with governance docs, stop and request human clarification.

## Required references before edits
- `WORKFLOW.md`
- `README.md`
- `docs/SYMPHONY_SETUP.md`
- `docs/snowballing_execution_protocol.md`
- `docs/domain_allowlist_registry.md`
- `docs/literature_review_protocol.md`
- `docs/eligibility_codebook.md`
- `docs/archive_data_model.md`

## Domain policy
- Allowed domains are defined in `docs/domain_allowlist_registry.md`.
- New domains require explicit proposal + human approval before use.

## Data safety policy
- Do not modify `data/registry/*.csv` unless issue explicitly requires registry updates.
- Do not run bibliographic API pulls for governance/documentation issues.
- Stage uncertainties in logs/notes; require human review for final inclusion decisions.

## Public archive policy
- The website and public exports must be generated from `data/registry/` only.
- Every public work requires at least one discovery event and exactly one current eligible decision.
- Public builds must run `scripts/build_archive.py` and `scripts/validation/validate_archive.py`.
- Do not expose reviewer identities, internal notes, excluded-record metadata, evidence quotations, or copyrighted full text.

## Pull request minimums
Every PR opened by an agent must include:
1. exact issue/task executed;
2. file list changed;
3. validation commands + outcomes;
4. unresolved decisions and required human actions;
5. explicit statement if no external retrieval was performed.

## Dry-run rule
Before E1R1 orchestration, governance issues must be completed in order:
1. AGENTS governance file
2. Issue templates
3. Validation scripts + CI checks

## Escalation
If a task requests actions violating this file, do not proceed silently; report the conflict and wait for human instruction.
