# Curator reading and review support

The curator should never receive an unexplained candidate card. Review support has two distinct layers and neither layer is a scientific decision.

## 1. Abstract and reading support

`data/curation/abstract_coverage.csv` remains the mechanical record of whether the automatic resolver found an abstract. Abstract text is not persisted in the repository.

For every current candidate whose mechanical status is `needs_web_search`, `data/curation/reading_aids.json` records a short, source-grounded aid containing:

- the candidate ID;
- the kind of evidence available;
- a source label and HTTPS locator;
- a short paraphrased synopsis;
- the verification date;
- a note explaining limitations or identity concerns.

The allowed conceptual distinction is important:

- `verified_abstract_source`: the located source exposes an abstract or equivalent substantive abstract field;
- `publisher_summary`: the publisher exposes a description/summary but not a distinct author abstract;
- `full_text_intro`: the paper/chapter itself is available and its introductory text supports a reading synopsis;
- `review_synopsis`: a conservative curator-oriented synopsis can be generated from verified source context when no standalone abstract was located;
- `metadata_warning`: only metadata or identity evidence is sufficiently reliable, so the synopsis is limited to what is known and what cannot yet be established.

### Mandatory evidence fallback

A review card must never end at `abstract not found` with no substantive reading support. The authenticated curator follows this display cascade:

1. author abstract, when verified and retrievable;
2. exact publisher summary or description;
3. source-grounded synopsis from the full text or introduction;
4. curator-generated synthesis from verified source context;
5. metadata-bounded synthesis stating only verified identity/scope facts and the unresolved evidentiary gap.

The first available level is displayed in the **same primary reading cell** used for the abstract. The curator must not have to open a secondary diagnostic panel to discover it.

Every fallback is labelled by evidence type and source. A publisher summary, introduction, generated synthesis or metadata-bounded synthesis must never be labelled as the author's abstract. A generated synthesis must paraphrase verified evidence and may not add claims not supported by its source basis. When an actual abstract becomes available, it always supersedes the synthesis in the primary reading cell.

This rule concerns reviewability only. It does not convert weak evidence into eligibility evidence: if the available synthesis cannot support the codebook boundary, the curator should escalate to full text or use `maybe_full_text_needed` rather than infer missing facts.

## 2. Decision guidance

Every materialised curator issue receives `Review guidance — preparatory`. The section translates the current codebook into an operational checklist while preserving the human boundary.

It always restates the four-part core test:

1. identifiable criminal actor or interest;
2. legal-economy target;
3. sustained access, participation, influence, control or embeddedness;
4. substantive analysis of that relationship.

The guidance also:

- identifies the current gate (metadata, substantive screening, manual boundary review or legacy re-check);
- surfaces the candidate-specific human action already recorded in the governed queue;
- explains when `maybe_full_text_needed` is preferable to a forced binary decision;
- distinguishes `eligible_core` from `eligible_contextual`;
- reminds the curator that adjacent AML/economic-crime work may be `not_eligible` for infiltration while separately eligible for `broader_aml` routing;
- keeps duplicate, non-academic and non-retrievable decisions tied to their specific conditions;
- states explicitly that screening, canonical promotion and publication are separate gates.

The prior intake assessment or legacy signal remains triage/audit information only. It is never a recommendation that the curator must follow.

## Synchronisation

`scripts/curation/sync_issue_review_support.py` synchronises both sections into materialised curator issues. `materialize-curation.yml` runs it after candidate metadata and retrieval metadata have been reconciled, so the preparatory support appears immediately before the curator action block without modifying canonical records or publication state.
