# Curator UX audit — 2026-09-06

## Scope

This audit reviews the authenticated curator as a scientific screening workspace, not as a public landing page. The goal is to reduce decision friction while preserving provenance, identity checks, evidence discipline and the human decision boundary.

The visual baseline was reconstructed from the current production DOM and CSS using a representative authenticated candidate with metadata, abstract, reading aid, review guidance and the full decision form. The representative page measured about 2,694 px high at a 1,440×1,100 desktop viewport and about 4,636 px high at a 390×844 mobile viewport. These numbers are diagnostic, not product metrics.

## Principal findings

### 1. Correct information, flat hierarchy

The selected-paper surface gave title, metadata, abstract, reading aid, review guidance and form almost equal visual weight. The sequence was scientifically complete but cognitively expensive: the reviewer had to traverse multiple similarly styled cards before reaching the decision controls.

### 2. Decision controls were too far from evidence

The form appeared only after all reading-support blocks. On a normal desktop viewport this required substantial vertical travel; on mobile the flow became several screens long. The base selection behaviour also targets the decision-form scroll position, which risks visually skipping the evidence immediately above it.

The CSS now gives the decision form a large scroll margin so programmatic scrolling stops early enough to keep evidence and guidance in view before the form.

### 3. Queue and paper competed for the same canvas

The original two-column grid stretched the queue column to the height of the paper/decision column. After the queue's internal list ended, a large visually inactive left column remained. The queue also disappeared from view during long paper review.

The queue and reading surface are now separate cards. On desktop the queue is sticky and viewport-bounded; its candidate list scrolls internally. On smaller screens it becomes a short bounded queue above the selected paper.

### 4. Queue cards carried too much repeated metadata

Every card showed candidate ID, stage, title, authors, year/venue, literal DOI, DOI status, abstract status, triage and source. DOI and source were therefore represented twice. The queue is a navigation and triage surface, not the final bibliographic record.

The literal DOI line and source chip are now visually suppressed in the queue while DOI verification, abstract state and triage remain visible. Full identifiers remain available in candidate data/search and in the selected-paper identity block.

### 5. Identity data needed stronger visual semantics

Bibliographic identity and workflow state were visually similar. The selected-paper metadata now emphasises the DOI typographically and separates later workflow cells with a lighter background. The title/byline remains the primary identity anchor.

### 6. Reading aid and review guidance should work as a pair

When an abstract exists, the reading aid is supplemental rather than another primary reading block. The audit keeps the abstract full width and places reading aid and review guidance side by side on desktop. Review guidance receives a distinct green-tinted treatment because it is the operational bridge from evidence to decision.

### 7. Authenticated work should not retain landing-page chrome

Once the curator session is active, the large introductory heading and explanatory app heading are repeated context rather than working information. They are now hidden in authenticated mode, bringing the queue and selected paper much closer to the top of the viewport while leaving the unauthenticated/public explanation unchanged.

## Resulting interaction hierarchy

The intended authenticated flow is now:

1. compact session state;
2. persistent queue and selected-paper identity;
3. abstract or best available evidence;
4. reading aid + candidate-specific review guidance;
5. decision form;
6. provenance/audit details on demand.

This pass changes no eligibility rule, screening decision, canonical record or publication state.
