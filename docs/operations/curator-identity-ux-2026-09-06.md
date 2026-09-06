# Curator identity and decision UX — 2026-09-06

## Objective

The curator should never make the reviewer infer whether a problem is bibliographic or scientific. Identity resolution and eligibility screening are distinct gates and must look and behave differently.

## Identity diagnostic

The selected-paper surface now derives a non-decisional identity state from the metadata already visible in the governed candidate issue: author/year/venue/DOI completeness, review stage, daily verification status, duplicate/conflict notes and persistent retrieval state.

The available preparatory states are:

- `verified`: identity is sufficiently resolved for screening;
- `partial`: the work is readable but one or more identity signals remain weaker than desired;
- `metadata_repair`: bibliographic repair is required before screening;
- `manifestation_ambiguity`: work identity is recognisable but version/date/manifestation remains unresolved;
- `duplicate_risk`: provenance contains a possible same-work signal that requires comparison.

These states are operational diagnostics only. They are never written as eligibility, duplicate or canonicalisation decisions.

## Hard gate

The existing governed definition of `metadata_fix` says metadata must be repaired before screening. The UI now enforces that separation: `metadata_repair` and `manifestation_ambiguity` block submission of a scientific screening decision and direct the curator to the best available source, DOI and audit record.

A `duplicate_risk` signal does not block screening automatically and does not choose `duplicate`. It only makes the exceptional-record controls more visible so the curator can compare work identity first.

## Guided decision composer

The original governed decision select remains the authoritative value submitted to the existing API, but it is represented through two visual groups:

1. normal screening outcomes: core, contextual, more text needed, outside scope;
2. exceptional record handling: duplicate, non-academic, non-retrievable.

No scientific outcome is preselected. Selecting a visual card writes the same code to the existing select and dispatches the existing change event, preserving all current conditional fields and backend validation.

The composer also exposes a three-step progress model — identity, evidence, outcome — so the reviewer can see which gate is actually incomplete.

## Scientific boundary

This pass changes no eligibility rule, exclusion reason, controlled topic, canonical record, publication record or surveillance logic. It only changes how already-governed states are diagnosed and presented to the curator.
