# Classic site UI contract

The entire public review website uses a deliberately utilitarian 1990s database-management visual language.

## Scope

The contract applies to:

- `site/index.html` — core archive;
- `site/aml.html` — broader AML collection;
- `site/stats.html` — daily research statistics;
- `site/404.html` — not-found surface;
- `site/curate.html` — authenticated curator workstation.

The first four pages share `site/classic-site.css`. The curator keeps its dedicated fullscreen CSS because it has stronger application-layout requirements, but its title/menu chrome follows the same visual language.

## Visual rules

The site is an information system, not a marketing page.

Required characteristics:

- full-width working area;
- navy application title bars and grey menu bars;
- Arial/Helvetica for UI text and Courier for identifiers/status values;
- rectangular 1px borders;
- white data panes on a grey application background;
- dense filters and tables;
- publication records presented as database rows with expandable details;
- methodology/definitions presented as reference panels rather than promotional cards;
- statistics presented as flat tables/panels, with charts retained only where they convey actual data.

Forbidden characteristics:

- rounded cards or pills;
- decorative gradients;
- drop shadows;
- hover translation/motion;
- oversized editorial hero typography;
- marketing-style spacing;
- decorative dashboard cards whose content can be represented as table/status cells.

## Behavioural boundary

This is a presentational contract only. It does not alter:

- archive JSON/CSV data;
- filtering/sorting semantics;
- public publication eligibility;
- surveillance statistics;
- curator authentication, retrieval or decision workflows;
- ontology, registry or publication state.

`styles.css` remains loaded first for existing structural compatibility. `classic-site.css` is loaded afterwards and is the authoritative public visual layer.

## Curator consistency

The curator remains a dedicated fullscreen workstation and does not load `classic-site.css`, avoiding conflicting layout systems. It uses the same classic chrome through a static menu bar:

`ARCHIVE | AML | STATS | CURATOR | REPOSITORY`

The fullscreen contract and internal scrolling remain governed by the curator-specific CSS and `CURATOR_FULLSCREEN_SHELL_V1`.

## Regression tests

`tests/test_classic_site_ui.py` checks that:

- all public pages load the classic design layer after the legacy base stylesheet;
- the new stylesheet is full-width and flat;
- publication cards are visually converted into database records;
- methodology/statistics use reference-panel/table patterns;
- curator navigation follows the same application language without importing the public skin;
- the 404 page is rendered as a classic application error window.
