# Classic site UI contract

The entire public review website uses a deliberately utilitarian 1990s database-management visual language.

## Scope

The contract applies to:

- `site/index.html` — core archive;
- `site/database.html` — read-only browser over the already governed public projections;
- `site/aml.html` — broader AML collection;
- `site/stats.html` — research statistics;
- `site/method.html` — public methodology;
- `site/404.html` — not-found surface;
- `site/curate.html` — authenticated curator workstation;
- `site/model.html` — scientific model explorer;
- `site/enrichment.html` and `site/review-v2.html` — authenticated research workspaces.

All ten entry documents load the same versioned `site/application.css` **last**. It owns the palette, typography, spacing, controls, focus treatment and application navigation. Component styles load first and own only their specialised structure. Do not redefine `--classic-*` tokens in a component stylesheet.

Public pages retain `styles.css` and `classic-site.css` for structural compatibility. `database.css`, `bibliometrics.css` and `method.css` retain their table/chart/document layouts; `model.css` retains the index/detail split. The curator retains its dedicated fullscreen CSS and internal scrolling, without importing the public skin.

## Visual rules

The site is an information system, not a marketing page.

Required characteristics:

- full-width working area;
- navy application title bars and grey menu bars;
- Arial/Helvetica for UI text and Courier for identifiers/status values;
- rectangular 1px borders where interface chrome or data structure requires them;
- white data panes on a grey application background;
- dense filters and tables;
- publication records presented as database rows with expandable details;
- the standalone methodology page presented as a plain linear HTML reference document: ordinary headings, paragraphs, numbered or bulleted lists, horizontal rules and underlined text links;
- statistics presented as flat tables/panels, with charts retained only where they convey actual data;
- the database browser presented as a dense object explorer, grid and record inspector, with no marketing cards.

The methodology page must not use a card grid, dashboard tiles, split hero, boxed criterion cards or repeated panel containers. It should resemble a basic university/project documentation page from the 1990s, while retaining the shared application header and navigation.

Forbidden characteristics:

- rounded cards or pills;
- decorative gradients;
- drop shadows;
- hover translation/motion;
- oversized editorial hero typography;
- marketing-style spacing;
- decorative dashboard cards whose content can be represented as text, lists, tables or status cells.

## Behavioural boundary

This is a presentational contract only. It does not alter:

- archive JSON/CSV data;
- filtering/sorting semantics;
- public publication eligibility;
- surveillance statistics;
- curator authentication, retrieval or decision workflows;
- ontology, registry or publication state.

`styles.css` remains loaded first where required for structural compatibility; `application.css` is the final visual authority. Use its tokens for component typography and borders. Native checkboxes/radios retain their intrinsic dimensions and must not inherit the minimum height or width of text fields. Statistics grids accommodate their actual number of indicators, without empty decorative cells.

The database browser is read-only presentation. It may consume only existing public static projections and the existing unauthenticated public research projection. It must not query private enrichment endpoints, machine routes, source bodies, private identifiers or reviewer material, and it must not create a parallel persistence layer.

## Curator consistency

The curator remains a dedicated fullscreen workstation and does not load `classic-site.css`, avoiding conflicting layout systems. Its title/menu chrome follows the same classic navigation language.

The fullscreen contract and internal scrolling remain governed by the curator-specific CSS and `CURATOR_FULLSCREEN_SHELL_V1`.

## Regression tests

`tests/test_classic_site_ui.py` checks that:

- all public pages load the classic design layer after the legacy base stylesheet;
- the classic stylesheet is full-width and flat;
- publication cards are visually converted into database records;
- `method.html` remains a plain linear document and does not regress to cards, grids or split hero panels;
- `method.css` remains free of grid/card/shadow styling;
- statistics retain flat table/panel patterns;
- the database browser remains read-only, uses text-node rendering, and is barred from private enrichment routes;
- curator navigation follows the same application language without importing the public skin;
- the 404 page is rendered as a classic application error window.


## Cross-section delivery contract — 2026-09-29

- Use the same six destinations, in order: Archivio, Database, Statistiche,
  Metodo, Modello, Curatore. The active destination has `aria-current="page"`.
  The retained AML and 404 routes do not invent a selected main section.
- Private workspaces link public destinations to the Pages origin; Curatore
  stays on the current console origin. Adding navigation does not grant access
  to private data. Authentication and the Worker asset allowlist are unchanged.
- Title bars use navy, section headings use grey, content panes use white.
  Compact table density may differ from long-form reading, but type, borders,
  control states and outer gutters use the shared contract.
- Place page identity before local section shortcuts. The methodology remains a
  linear document, with ordinary headings and horizontal rules.
- All entrypoints use one explicit `application.css` cache revision. Update it
  together; changed component styles receive the same revision.
- The 404 document uses absolute public resource and recovery URLs so that its
  chrome still works at nested missing paths; it requires no JavaScript redirect.
- `tests/test_shared_application_design.py` checks the common stylesheet, palette
  ownership, menu completeness, private/public navigation origins and delivery
  coverage. Existing reader, fullscreen, model, database and scientific-boundary
  regressions remain required.
- The existing post-Pages `verify_published_register.py` receipt now compares all
  ten entry documents and their static styles, as well as the reader and database
  renderer bytes. A stale section fails verification instead of silently passing
  because the home page was current. This is **Pages shell delivery** only: it
  cannot attest Worker deployment, authentication or private research readback.

Maintenance changes no candidate, metadata, source, document, annotation, proposal,
completion, validation or corpus record. No ontology concept or persistence path
is introduced.


The deployed visual check also tests document overflow against
`document.documentElement.clientWidth` (the usable viewport, excluding its
scrollbar). The method's main pane must retain its gutter-subtracting width:
its component selector includes both `classic-site` and `classic-method`, so
the later shared default cannot restore `width: 100%` on top of outer margins.
This preserves the linear document without a page-wide horizontal scrollbar.

The retired centred-grid 404 body/main layout is removed from `classic-site.css`.
Its residual `place-items: center` must not shrink the shared application header;
404 page geometry now belongs to `application.css` alone.
