# Open scholarly reconciliation stack

## Purpose

The curator uses multiple zero-cost scholarly services because no single provider is authoritative for every field. The stack is designed to improve bibliographic identity, abstract recovery, manifestation resolution and citation-frontier construction without allowing provider metadata to become a scientific decision.

## Zero-cost providers added in this layer

| Provider | Primary role | Authentication | Automatic use |
|---|---|---|---|
| OpenCitations Meta | DOI-linked bibliographic corroboration | none required | yes |
| OpenCitations Index | backward/forward DOI citation links | none required | formal E2/E3 engine |
| arXiv | preprint metadata, abstract, versions and published DOI | none | yes |
| Zenodo | repository records, descriptions, files and related identifiers | none for public records | yes |
| HAL | repository metadata, identifiers and locators | none | yes |
| DOAJ | OA article metadata, abstract, DOI/ISSN and full-text locator | none | yes |

The existing core remains OpenAlex, Crossref, Semantic Scholar, DataCite, Unpaywall, CORE and Europe PMC. ORCID is deliberately not activated here because its Public API requires client credentials; it can be added later without changing the reconciliation contract.

## Provider contract

Each adapter returns a normalised observation rather than writing directly to the candidate or registry:

- provider;
- matched title;
- matched year;
- matched DOI;
- authors when exposed;
- venue when exposed;
- abstract when exposed;
- best public article/repository URL;
- provider-specific source identifier;
- version/relationship identifiers when exposed;
- match type and score.

The observation is preparatory evidence. Raw provider shape never becomes the canonical schema.

## Field-level reconciliation

`curator-app/src/metadata-reconciliation.js` reconciles title, DOI, year, authors and venue separately. For each field it retains:

- selected value;
- status (`verified`, `resolved_conflict`, `conflict`, `missing`);
- confidence;
- providers supporting the selected value;
- alternative values and their providers;
- provider-weighted support score.

Authority is field-specific. For example, Crossref/OpenCitations Meta/DataCite are weighted strongly for DOI identity, while Crossref/OpenAlex are weighted strongly for authors and venue. Weighting may resolve a weak disagreement for display, but a material DOI/title/year conflict remains explicit.

The reconciler never changes `data/registry/` and never closes a queue issue.

## Manifestation handling

A single scholarly work can have several manifestations: preprint, working paper, repository copy, accepted manuscript or version of record. The reconciler therefore preserves provider IDs, DOI variants and explicit relation fields from Crossref, arXiv and Zenodo.

Two strongly title-matching records with distinct DOI manifestations, or explicit version relations, produce `manifestation_ambiguity`. They are not silently deduplicated. The curator must decide how the manifestations relate before canonicalisation.

## E2/E3 citation chasing

`curator-app/src/citation-chasing.js` implements a DOI-bound two-provider citation frontier:

- **E2 backward:** OpenCitations references + Semantic Scholar references;
- **E3 forward:** OpenCitations citations + Semantic Scholar citations.

Candidates are reconciled mechanically by exact DOI when present. The output retains provider overlap and provider-unique records. Provider disagreement is evidence about graph coverage, not an error to hide.

The command-line entry point is:

```bash
node scripts/expansion/citation_frontier.mjs --doi 10.x/example --output frontier.json
```

Multiple `--doi` arguments or a line-oriented `--doi-file` are supported. The resulting JSON contains each seed frontier plus merged unique E2 and E3 candidate sets and unresolved seed failures.

The command does **not** mutate the review queue, registry, screening state or publication state. Newly found works must still enter the governed candidate/reconciliation/screening workflow.

## Runtime cost boundary

All providers in this extension are public zero-cost read APIs. Rate limits and provider failures are treated as bounded failures. There is no paid fallback and no automatic escalation to web search because a scholarly provider is unavailable.

OpenAlex is separately governed as a free-daily-credit provider under its current access model; this extension does not increase OpenAlex calls beyond the existing primary lookup path.

## Provenance and publication boundary

The enrichment response may expose `metadataResolution`, compact `metadataObservations` and, when explicitly requested, `citationFrontier`. These data exist to support the authenticated curator and formal expansion tooling. They are not copied into the public corpus as decisions.

Eligibility remains entirely separate from bibliographic confidence. A perfectly identified paper can still be ineligible; an interesting paper with unresolved identity remains blocked from canonical promotion until the identity problem is resolved.
