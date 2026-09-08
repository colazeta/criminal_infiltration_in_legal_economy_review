# Shared interface

The public archive, AML collection, statistics, model browser and secure curator
console share `site/application.css`, loaded after their component styles. The
visual language follows a restrained 1990s desktop application: navy title bar,
neutral grey toolbars, white working panes, square controls and ruled tables.

Use the same five primary destinations, in this order: Archivio, Raccolta AML,
Statistiche, Modello, Curatore. Keep downloads, documentation and the optional
V2 entry near the relevant working surface. Public links from the Worker use
absolute Pages URLs; session and curator operations remain on the secure origin.
The active section must have `aria-current="page"`.

Body and control text uses Tahoma/Arial at 13px, supporting copy at 11–12px, and
clear larger headings. Avoid 8–10px body text, decorative cards and rounded
status pills. Keep visible focus, text labels for status, a skip link and all
existing hidden/authentication states. Scientific text, access requirements,
record counts and decisions are not style concerns.

The model retains its index/detail split. The curator retains its master table
and record panel, with independent overflow. On narrow screens the primary menu
wraps, filters use fewer columns and model panels stack. Long tables scroll
within their section. Page styles own geometry; the shared sheet owns common
colours, typography, navigation, controls and spacing.

`application.css` is in the Worker asset allowlist and deployment path triggers,
so subsequent shared-style changes reach both public and authenticated surfaces.
