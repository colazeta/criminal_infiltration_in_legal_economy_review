# CILE Review Ontology Profile

**Current profile:** `0.4.0`

This directory is the semantic contract for the living systematic review on **Criminal Infiltration in the Legal Economy (CILE)**. The contract is normative: physical CSV/JSON structures may evolve, but every governed artifact must remain mapped to this ontology and must pass `scripts/ontology/validate_ontology.py`.

## Design rule

Do not invent a local concept when a maintained standard already models it.

The profile therefore reuses:

- SynthScholar **SLR Ontology** for systematic-review structure and review/model events;
- **W3C PROV-O** for Entity / Activity / Agent provenance;
- **SPAR FaBiO** and **BIBO** for bibliographic expressions and identifiers;
- **W3C Web Annotation** for grounded evidence spans;
- **SKOS** for controlled vocabularies;
- **RIPE-O** for evidence-backed assessment provenance.

The project namespace is reserved for the concepts those ontologies do not adequately cover, especially candidate governance, access/abstract coverage and the criminal-infiltration domain.

## The identity rule

`ScholarlyWork` is the canonical intellectual work. It is **not** a DOI, PDF, publisher page, repository copy or working-paper series entry.

One work may have many `Manifestation` objects and many `Identifier` objects. For example, an IZA PDF, a CESifo working paper, an RFBerlin revision, an SSRN DOI and a publisher version may all belong to one `ScholarlyWork` when identity is curator-confirmed. A new manifestation must never create a second canonical work merely because it has a different URL or DOI.

The existing `papers.csv` table is the canonical work registry. `work_identifiers.csv`, retrieval coverage and access coverage describe identifiers or manifestations around that work/candidate.

## Candidate boundary

A `CandidateRecord` is deliberately different from a `ScholarlyWork`.

Discovery automation may create or enrich candidates, retrieval attempts, access assessments and abstract-availability assessments. It may **not** create a canonical `paper_id`, an eligibility decision or a publication state. Promotion remains an explicit, attributed curator action.

## Decision provenance

A final screening decision must be represented as an evidence-backed `ScreeningDecision` and attributed to a human agent. Automated systems may create search/retrieval/model activities and evidence records; they may recommend or prepare, but they do not become the final eligibility agent.

Historical decisions remain entities in their own right. Supersession is represented as provenance/versioning rather than destructive replacement.

## Evidence rule

Evidence is a first-class entity. A decision should point to an evidence locator or source basis rather than silently embedding an unsupported claim. Evidence spans should use the Web Annotation model when source offsets or passages are available.

The abstract/access coverage ledgers are metadata-only assessments. They must not persist copied abstract/full-text bodies.

## Access rule

Access is assessed at manifestation level whenever possible.

- `open`: a public full-text/OA manifestation is positively verified;
- `restricted`: positive closed-access evidence exists and there is no conflicting **positively verified open** manifestation;
- `unknown`: evidence is insufficient or conflicting.

A full-text locator is **not itself evidence of open access**: it may point to a paywalled publisher PDF/XML manifestation. Conversely, a work can have a restricted publisher manifestation and an open repository manifestation at the same time. Work-level UI labels are projections of the best verified manifestation, not intrinsic properties of the intellectual work.

## Controlled concepts

`data/registry/taxonomy.csv`, `data/registry/exclusion_reasons.csv` and `data/registry/secondary_collections.csv` are governed SKOS-like concept schemes. They remain the operational source of truth for their applied codes.

The CILE profile additionally defines the review's core infiltration-relation vocabulary:

`access → participation → influence → control / ownership → embeddedness`

The terms are analytical relations, not an ordinal severity scale. More than one may apply to one study.

## Physical-artifact mapping

`mappings/artifact-contracts.json` maps every CSV under `data/registry/` and `data/curation/` to its ontological class, primary key, foreign keys, controlled fields and critical semantic properties.

The validator fails when:

- a new governed CSV has no ontology contract;
- a declared artifact disappears;
- a primary/foreign key violates identity;
- a controlled value is outside its ontology enum;
- a field introduces an undeclared semantic family;
- canonical DOI identity is inconsistent with `work_identifiers.csv`;
- a manifestation identifier is treated as a primary canonical identifier;
- coverage ledgers drift from the candidate queue;
- `restricted` conflicts with a verified OA location, an anonymously retrieved PDF, or assisted positive open-access evidence;
- a decided candidate lacks attributable append-only provenance;
- abstract/full-text bodies enter metadata-only coverage ledgers.

## Files

- `cile-review-profile.yaml` — **normative LinkML source of truth** (JSON-compatible YAML, so stdlib CI can parse it without a package install).
- `cile-review-profile.ttl` — OWL/RDF view of the core classes and mappings.
- `mappings/external-vocabularies.json` — upstream ontology dependencies and reuse policy.
- `mappings/artifact-contracts.json` — physical-to-semantic contracts.
- `vocabularies/` — human-readable controlled vocabularies whose codes are checked against the profile.
- `../schema/cile-review-record.schema.json` — closed JSON Schema for portable CILE semantic records.

The public namespace is the Pages-hosted Turtle resource:

`https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/vocab/cile-review.ttl#`

## Change discipline

Ontology changes are versioned. Any PR that adds a new governed table, a new decision/access/review state, a new identity relation or a new domain concept must change the ontology/profile in the same PR. A data change that requires an undeclared concept is therefore rejected before publication.

## Review V2 implementation

The [publication and review model](../docs/governance/review-v2-model.md) separates Work, Expression and Manifestation, with ordered contributors, venues, sections, declarations and evidence-grounded review records. The private D1 contract is `modules/review-v2.json`. See the [model explorer](../site/model.html). Migration alone creates no review or scientific data. Historical profile 0.1.0 is preserved in `legacy/0.1.0/`.

## Open-access mapping

The owner-approved OA-1 access scope is specified in [open-access.md](../docs/methodology/open-access.md). Both public collections require a current verified lawful full-text assessment. V2 records access history separately from scientific screening.

## Discovery source amendment — 2026-09-08

The owner retired Consensus. Exa-only run/intake schema v2 and operational
protocol CILE-DAILY-v3 reuse `SearchActivity.source_name`, the existing
`SearchDay` source-count projection and V2 provider/protocol slots. The mapping
and historical/current restrictions are recorded in `modules/daily-calendar.json`
and checked by the ontology validator. Scientific classes, four-part criteria,
controlled vocabularies and profile 0.4.0 do not change. Historical two-source
telemetry is decoded under its original v1 contract and kept out of the OA cycle.

## OA intake evidence

`modules/intake-open-access.json` maps the mandatory candidate receipt and
metadata-only snapshots to existing CandidateRecord, AccessAssessment and
Evidence concepts. The ontology validator checks those mappings and requires
one preserved receipt per active daily candidate. Scientific profile 0.4.0 and
controlled vocabulary are unchanged; an intake attestation is not a curator
publication receipt. See `../docs/operations/intake-open-access.md`.

## Operational register amendment

The owner instruction of 2026-09-08 authorises a visible bibliographic projection of CandidateRecord before screening. See modules/paper-register.json and ../docs/operations/paper-register.md. This reuses existing candidate, unknown-access and provenance concepts; no scientific vocabulary is changed. The old mandatory verified-OA intake rule remains only for v2 history. New v3 intake allows explicit unknown access.

## Scientific enrichment — profile 0.4.0

`modules/paper-enrichment.json` maps every property of the closed private
`schema/paper-enrichment.schema.json`, alongside the 15 additive tables in
`0003_paper_enrichment.sql`. The six clinical contribution categories are
proposed classifications, not eligibility decisions. See
[the operational contract](../docs/operations/paper-enrichment.md) and
[the extraction guide](../docs/methodology/paper-extraction.md).
The previous 0.3.0 scientific application remains backward-compatible; no
existing decisions or source snapshots are recoded.
