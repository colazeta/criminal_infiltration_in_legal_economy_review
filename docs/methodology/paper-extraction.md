# Scientific extraction and clinical contribution coding

This is an operational adaptation of the owner's Cincimino-based framework,
not a verbatim reproduction of the source framework. The controlled definitions
are in `ontology/vocabularies/clinical-contribution.json`.

## Extraction unit and source basis

A publication can report several studies. A study can use multiple datasets and
analyses. Variables are **uses within an analysis**, not global paper attributes.
A finding belongs to an analysis; referenced variables must belong to that same
analysis. Qualitative categories and conceptual propositions are represented in
the appropriate fields without inventing dependent/independent variables.

The private envelope covers the research question, contribution, summary,
conceptual definition and operational identification of infiltration, authors'
limitations and analyst observations. Studies have population, geography, period
and design. Datasets retain origin, selection, sample size and observation unit.
Analyses retain question, method, identification, comparison and validation.
Variable uses retain original name, measured concept, operationalisation, source,
unit, time window, transformations and analysis-specific role. Findings retain
statement, kind, direction, estimate, uncertainty, comparator, population/time
scope and caveats. Numeric-looking values remain faithful source strings; no
unreported precision, causality or statistical significance is generated.

Every populated fact has a status, value, origin (`source` or `analyst`) and
source-span IDs. Offsets are **UTF-16 code units** of the exact preserved string,
as in browser text selection. A page/table/section locator explains the context.
A model summary is not a source. Metadata alone cannot support scientific facts.
Abstract-only extraction stays labelled abstract-only. `not_reported` means not
reported in the consulted source, never absence from an unread full paper.
`not_verifiable`, `not_applicable` and `ambiguous` remain distinct; ambiguity has
an explanation. Null results and counter-evidence are not omitted on purpose.

## Classification

**Aetiology:** conditions and mechanisms explaining criminal participation.
**Diagnosis:** observed characteristics describing or recognising its presence.
**Screening:** a procedure selecting potential previously unrecognised cases.
**Therapy:** interruption and recovery of affected economic activity.
**Prognosis:** subsequent trajectory, recoverability or recurrence after identification.
**Prevention:** reducing vulnerability to entry.

Assign the primary category to the substantive main contribution, not keywords or
a generic concluding policy implication. A secondary category needs a separate
substantive contribution and grounded rationale. Prediction is not automatically
prognosis; review-eligibility screening is not the scientific screening category.
`insufficient_evidence` and `outside_framework` are distinct abstentions, not
seventh/eighth scientific categories. A classification is an analyst proposal;
no confidence percentage is invented and no curator-approved label is overwritten.

## Calibration record required before machine activation

Use 12–18 **real** already-registered publications spanning qualitative and
quantitative research, theory/review, multiple studies, abstract-only/full-text
coverage, DOI-less identity and disputed classification. Availability and selection
are recorded without assuming they are eligible. Store reference extractions
privately with independent checks. Report correctness, unsupported additions,
omissions and coding disagreements by field and source coverage. Document
adjudication, source hashes, model, prompt and codebook versions and explicit
acceptance. Unit-test fixtures verify software, not scientific extraction quality.
