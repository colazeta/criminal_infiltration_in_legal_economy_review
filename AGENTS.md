# Agent contract

This file governs every automated or semi-automated action in the repository.

## Mission

Maintain a trustworthy public literature archive while preserving a strict
boundary between discovery, editorial judgement and publication.

## Non-negotiable rules

1. Never invent or silently repair metadata, identifiers, abstracts, citations,
   evidence or screening outcomes.
2. Never promote, publish, merge or mark a candidate eligible automatically.
3. Never expose candidate metadata, reviewer identity, internal notes, evidence
   quotations, secrets or copyrighted full text in public exports.
4. Never use an unapproved source, connector or returned domain. Check
   `docs/governance/sources.md` before retrieval.
5. Never overwrite decision history. Add a new decision and retire the former
   current row in the same reviewed change.
6. Never auto-merge a registry or publication change.

## Task routing and write boundaries

| Role | May write | Must not write |
|---|---|---|
| Discovery/intake | One structured GitHub intake issue | Repository files, branches, PRs, registries, publication state |
| Metadata verifier | Candidate issue or reviewed metadata PR | Eligibility decisions, public relevance claims |
| Screener | Reviewed decision/evidence PR | Publication manifest unless the task explicitly includes curation |
| Curator | Registry and publication-manifest PR | Unverified metadata, automatic merge |
| Release maintainer | Site, release metadata, changelog and deployment | Scientific decisions not already recorded |
| Maintenance agent | Docs, tests and CI within assigned scope | Bibliographic retrieval unless explicitly assigned |

If a task spans roles, keep the stages in separate commits or PRs and preserve a
human review boundary before publication.

## Candidate-to-public flow

1. Search tools create an intake issue using the candidate template.
2. Metadata are verified and duplicates/identifier variants are resolved.
3. Screening records a versioned current decision with evidence basis.
4. A curator adds or updates the canonical work, identifiers, discovery event and
   approved public annotation together.
5. CI rebuilds the site and applies the full publication gate.
6. A person reviews and merges; deployment follows `main`.

Intake assessments use `plausible_core`, `plausible_contextual` or `uncertain`.
Only governed screening decisions may use `eligible_core` or
`eligible_contextual`.

## Required reading by task

- Any registry/publication change: `docs/governance/data-model.md` and
  `docs/methodology/eligibility.md`.
- Retrieval or intake: `docs/methodology/discovery.md`,
  `docs/governance/sources.md` and `docs/operations/automation.md`.
- Saturation work: `docs/methodology/saturation.md`.
- Release/deployment: `docs/operations/release.md`.

Do not require unrelated documents merely to make a small maintenance change.

## Mandatory validation

Run the smallest relevant subset, and run the full set for registry, site or
workflow changes:

```bash
python3 scripts/validation/validate_repository.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/build_archive.py
python3 scripts/validation/validate_archive.py
python3 scripts/validation/validate_site.py
node --check site/app.js
python3 scripts/report_saturation.py
```

The PR body must list changed files, commands and results, record counts,
external retrieval performed, and unresolved human decisions.

## Fail-closed behaviour

Stop without writing when authentication, source authorisation, identity
resolution, evidence, issue idempotency or the publication gate cannot be
verified. A failed request is not a zero-result search. An incomplete E1–E3
cycle is not an assessable saturation cycle.
