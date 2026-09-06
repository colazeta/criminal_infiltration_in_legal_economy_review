# Residual abstract resolution

`data/curation/abstract_coverage.csv` answers a deliberately narrow question: has a reliable abstract-bearing source been verified by the governed retrieval process?

It must not be used as a proxy for whether a candidate is reviewable.

## Assisted residual registry

`data/curation/residual_abstract_resolution.json` covers exactly the candidates whose current abstract coverage is `needs_web_search`.

The registry is non-decisional and uses four controlled classes:

- `full_text_or_intro_ready` — the exact work/chapter text or a directly readable substantive source surface is available even though no standalone abstract has been verified;
- `publisher_summary_ready` — an exact publisher/institutional description or chapter context is sufficient to begin screening, with escalation to full text only if the eligibility boundary remains unresolved;
- `metadata_only` — identity is resolved but substantive source text remains insufficient, so retrieval can still be warranted;
- `known_noise` — the record is verified legacy retrieval/identifier noise and should move to controlled exclusion review rather than consume additional abstract-search effort.

`standaloneAbstractStatus=not_verified_after_targeted_search` is intentionally weaker than “no abstract exists”. It records only the outcome of the current targeted search. A later authoritative abstract-bearing source should replace this status and allow the candidate to leave the residual registry.

## Invariants

1. The registry candidate IDs must exactly equal the current `needs_web_search` set. CI fails if either side changes without the other.
2. Abstract text is never persisted in this registry.
3. Review readiness never changes eligibility, canonical metadata, duplicate status or publication status.
4. `known_noise` is limited to records whose identity has already been resolved as legacy retrieval noise.
5. Assisted resolution is materialised in curator issues under `## Abstract resolution — assisted` and is removed automatically when the candidate leaves the residual registry.

## Current 2026-09-06 state

The current residual set contains 23 candidates:

- 5 `full_text_or_intro_ready`;
- 12 `publisher_summary_ready`;
- 2 `metadata_only`;
- 4 `known_noise`.

Therefore 17 of 23 residual abstract cases are already substantively review-ready without pretending that a publisher summary or chapter introduction is an author abstract. The remaining retrieval effort should be concentrated on the two `metadata_only` records; the four `known_noise` records should proceed to controlled exclusion review.
