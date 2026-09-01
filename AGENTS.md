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
7. When the owner has granted continuing maintenance authority, complete
   documentation, software, test, CI and site work through validation and merge
   without waiting for an extra ad-hoc approval. This authority never supplies a
   missing scientific judgement or curator instruction.

## Task routing and write boundaries

| Role | May write | Must not write |
|---|---|---|
| Discovery/intake | One structured intake issue when needed and one aggregate metrics-ledger comment per batch | Repository files, branches, PRs, registries, publication state |
| Metadata verifier | Candidate issue or reviewed metadata PR | Eligibility decisions, public relevance claims |
| Screener | Reviewed decision/evidence PR | Publication manifest unless the task explicitly includes curation |
| Curator | Registry and publication-manifest PR | Unverified metadata, automatic merge |
| Release maintainer | Site, release metadata, changelog and deployment | Scientific decisions not already recorded |
| Maintenance agent | Docs, tests and CI within assigned scope | Bibliographic retrieval unless explicitly assigned |

If a task spans roles, keep the stages distinguishable and preserve the explicit
curator decision before publication. Routine maintenance may proceed
autonomously when the owner has already granted that authority.

## Candidate-to-public flow

1. Search tools create an intake issue using the candidate template.
2. Metadata are verified and duplicates/identifier variants are resolved.
3. Screening records a versioned current decision with evidence basis.
4. A curator adds or updates the canonical work, identifiers, discovery event and
   approved public annotation together.
5. CI rebuilds the site and applies the full publication gate.
6. CI validates the visible change. Registry/publication changes remain
   unmerged until an authorised curator or reviewer accepts them; validated
   maintenance changes may be merged under continuing owner authority.

Intake assessments use `plausible_core`, `plausible_contextual` or `uncertain`.
Only governed screening decisions may use `eligible_core` or
`eligible_contextual`.

## Required reading by task

- Any registry/publication change: `docs/governance/data-model.md` and
  `docs/methodology/eligibility.md`.
- Retrieval or intake: `docs/methodology/discovery.md`,
  `docs/methodology/expansion.md`, the relevant sections of
  `docs/methodology/expansion-reference.md`, `docs/governance/sources.md` and
  `docs/operations/automation.md`. Daily surveillance also requires
  `docs/operations/daily-metrics.md`.
- Curator-console action: `docs/operations/curation.md`,
  `docs/operations/github-app.md`,
  `docs/governance/data-model.md` and `docs/methodology/eligibility.md`.
- Saturation work: `docs/methodology/saturation.md`.
- Release/deployment: `docs/operations/release.md` and
  `docs/operations/github-pages.md`.

Do not require unrelated documents merely to make a small maintenance change.

## Mandatory validation

Run the smallest relevant subset, and run the full set for registry, site or
workflow changes:

```bash
python3 scripts/validation/validate_repository.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/build_archive.py
python3 scripts/build_secondary_collections.py
python3 scripts/curation/build_curator_stats.py
python3 scripts/curation/build_curator_options.py
python3 scripts/validation/validate_archive.py
python3 scripts/validation/validate_site.py
node --check site/app.js
node --check site/aml.js
node --check site/stats.js
node --check site/curator.js
node --check site/curator-config.js
node --check curator-app/src/index.js
node --check curator-app/src/worker.js
node --test curator-app/test/*.test.js
python3 scripts/report_saturation.py
```

The PR body must list changed files, commands and results, record counts,
external retrieval performed, and unresolved human decisions.

## Fail-closed behaviour

Stop without writing when authentication, source authorisation, identity
resolution, evidence, issue idempotency or the publication gate cannot be
verified. A failed request is not a zero-result search. An incomplete E1–E3
cycle is not an assessable saturation cycle.
