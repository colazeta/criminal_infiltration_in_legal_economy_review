# Curator visual/layout audit

## Audit scope

This audit treats the curator as a desktop-style data-entry application, not as a responsive marketing page. The required geometry is therefore a strict viewport contract:

`browser viewport -> application shell -> queue master table + record/detail pane -> internal scrolling only`.

## Findings

### 1. Fullscreen geometry depended on runtime component CSS

The base site stylesheet still contains public-site rules such as a centred `main` constrained to 1180 px, editorial margins/padding and an old `.editorial-console` minimum height. The curator-specific CSS overrides those rules, but it was loaded by JavaScript component initialisation.

That meant the application shell could temporarily or persistently fall back to page-style geometry when component CSS was delayed or not initialised. A desktop workstation must not depend on JavaScript for its viewport dimensions.

### 2. The critical CSS arrived after first paint

`curator-reading.css` and `curator-queue.css` were dynamically inserted. This creates avoidable layout shift and makes the initial geometry sensitive to script execution and cache state.

### 3. Remaining-height allocation was implicit

The console was a flex child with `flex: 1 1 auto`. The stronger contract is to make the console consume exactly the remaining application height with `flex: 1 1 0%`, `height: 0` and `min-height: 0`, while fixed/status rows remain non-shrinking.

### 4. Scrolling must belong to panes, not to the page

The application shell should never acquire document scroll. Queue and detail remain the only scroll owners, with contained overscroll.

## Remediation

`curate.html` now loads the classic reading and queue styles statically before JavaScript. It also carries a small critical `CURATOR_FULLSCREEN_SHELL_V1` block that:

- fixes `main#main-content` to the viewport with `inset: 0`;
- removes all inherited width/max-width/margin/padding constraints from the shell;
- propagates `width: 100%` and `height: 100%` through the app hierarchy;
- makes the editorial console the exact remaining-height flex child;
- enforces the one-column master-table-above-detail geometry before JavaScript runs;
- suppresses document scrolling;
- assigns scrolling to the queue/detail panes;
- keeps explicit low-height and narrow-viewport geometry.

The component JavaScript still checks for the static `data-curator-reading` / `data-curator-queue` links, so it does not duplicate the stylesheets.

## Non-goals

This change does not alter screening logic, recommendations, candidate state, retrieval, identity resolution, publication state or scientific governance.
