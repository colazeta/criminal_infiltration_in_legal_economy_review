# Classic site UI contract

The entire public review website uses a deliberately utilitarian 1990s database-management visual language.

## Scope

The contract applies to:

- `site/index.html` — core archive;
- `site/aml.html` — broader AML collection;
- `site/stats.html` — research statistics;
- `site/method.html` — public methodology;
- `site/404.html` — not-found surface;
- `site/curate.html` — authenticated curator workstation.

The public static pages share `site/classic-site.css`. The methodology page adds the narrowly scoped `site/method.css` after the shared styles only to enforce its deliberately plain document layout. The curator keeps its dedicated fullscreen CSS because it has stronger application-layout requirements, while its title/menu chrome follows the same visual language.

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
- statistics presented as flat tables/panels, with charts retained only where they convey actual data.

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

`styles.css` remains loaded first for existing structural compatibility. `classic-site.css` provides the shared public visual layer; `method.css` is a presentation-only extension for the standalone method document.

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
- curator navigation follows the same application language without importing the public skin;
- the 404 page is rendered as a classic application error window.
