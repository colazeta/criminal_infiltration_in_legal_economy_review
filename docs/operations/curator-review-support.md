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
- `review_synopsis`: a conservative curator-oriented synopsis can be made from verified source context, but no standalone abstract was located;
- `metadata_warning`: the record appears noisy, misidentified or insufficiently resolved, so the aid warns the curator instead of inventing an abstract.

A publisher summary, introduction or review synopsis must never be labelled as the author's abstract. When an actual abstract is available, the authenticated curator may retrieve and display it ephemerally at review time.

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
