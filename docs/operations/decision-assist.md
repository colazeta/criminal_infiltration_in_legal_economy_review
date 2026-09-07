# Curator decision assist

The curator console includes a non-canonical decision-assist layer for candidate screening.
Its purpose is to reduce the curator's reading and data-entry burden without replacing the
human screening decision required by the repository governance contract.

## Operating sequence

For the selected candidate the console uses, in order:

1. the materialised candidate context returned by the authenticated Worker;
2. the author abstract when it is available in the authenticated reading surface;
3. otherwise the governed reading synopsis or publisher/full-text reading aid;
4. otherwise a metadata-bounded fallback that explicitly refuses to infer eligibility.

The assist then applies the current four-part CILE test:

1. identifiable criminal actor or interest;
2. legal-economy entity or setting;
3. sustained access, participation, influence, control or embeddedness;
4. substantive analysis of that relationship.

A core recommendation requires positive evidence for all four. Missing evidence produces a
`SERVE ALTRO TESTO` recommendation rather than an inferred inclusion.

## What the curator sees

The primary assist block contains:

- recommendation family (`CORE`, `CONTEXTUAL`, `SERVE ALTRO TESTO`, etc.);
- confidence;
- whether the available evidence is sufficient;
- a reasoned assistant judgement;
- the decisive reason.

The expandable audit block adds:

- one rationale for each of the four CILE criteria;
- the strongest plausible countercase;
- what evidence would change the recommendation;
- evidence basis;
- substantive reading summary/focus.

## Human boundary

`APPLICA AL FORM` only pre-fills compatible governed controls. It never:

- checks the explicit confirmation box;
- calls `/api/decisions`;
- submits the form;
- writes candidate state;
- creates a canonical work;
- changes publication state.

The curator must review the prefilled form, explicitly confirm it and press `SALVA`.
The resulting GitHub instruction and review PR remain governed by the existing candidate
curation workflow.

The assist is ephemeral. No recommendation is written to `data/curation/`, `data/registry/`
or public exports. This keeps `assistant recommendation` distinct from the attributable
human `ScreeningDecision`, consistent with the ontology rule that automated/model
activities may recommend or prepare but do not become the final eligibility agent.

## Conservative reasoning policy

The runtime assist may use title/metadata for orientation, but never for a positive core
screening recommendation. A positive core proposal requires substantive evidence from the
abstract or a materialised screening synopsis and explicit support for all four criteria.

A contextual proposal is used only where the existing evidence and prior triage support a
specific conceptual, methodological or comparative contribution while direct infiltration
is not established.

Negative proposals are intentionally conservative. Absence of a keyword is not treated as
proof of absence. The system prefers `SERVE ALTRO TESTO` unless the available evidence
contains an explicit boundary signal or the materialised retrieval state identifies known
noise.

## `APPROFONDISCI`

`APPROFONDISCI` is a curator-triggered retrieval action. It may use the existing same-origin
free-web fallback under the repository's zero-cost provider guards. The request is bounded
in time and only concerns the currently opened candidate. A recovered author abstract
replaces the provisional synthesis in the reading surface and causes the recommendation to
be recalculated.

No retrieval result is silently persisted as an abstract or screening outcome.

## Topic limitation

Eligible decisions still require a governed topic. The assist only pre-fills a topic when
one of the existing controlled concepts is explicitly supported (currently conceptual
foundations or criminal transplantation). It does not invent a new topic. For other core or
contextual candidates the curator must select an existing appropriate topic or address the
taxonomy gap through a separate governed ontology/taxonomy change.
