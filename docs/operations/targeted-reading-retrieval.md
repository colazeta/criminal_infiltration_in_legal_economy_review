# Targeted reading retrieval

When the mechanical abstract cascade or first-pass assisted search does not expose a reliable abstract, the review may run a targeted per-record retrieval pass using exact DOI, exact title, author, book or venue metadata, publisher pages, institutional repositories, book previews and verified alternate manifestations.

The goal is to improve curator reading support without changing eligibility. Higher-confidence results may replace an earlier preparatory aid through `data/curation/reading_aid_overrides.json`.

An override may upgrade a `metadata_warning` or `review_synopsis` to a `publisher_summary`, `full_text_intro` or `verified_abstract_source` only when the exact work identity and source support that label. A source that verifies only identity must not be represented as an author abstract.

Targeted retrieval remains non-decisional. Screening, canonicalisation and publication require their existing human-governed gates.

## Parallel Search assisted OA retrieval

For already-registered candidates, Parallel Search is a normal targeted-retrieval channel under the 2026-09-12 owner instruction. Query exact DOI first; otherwise use a strict title/author/year formulation. Prefer publisher, institutional repository, recognised scholarly repository/preprint and direct OA PDF manifestations. Verify the final source before writing any locator or synopsis.

A search excerpt is not a substitute for an accessible paper. If only the author/publisher abstract is actually verified, mark the reading basis `abstract_only`; if only selected substantive passages are verified, treat it as partial text; use `full_text` only when the whole scholarly manifestation is actually available to the retrieval step. Information absent from the available evidence remains `not_verifiable`. Public reading aids contain concise paraphrases and provenance only, never copied full text or long abstracts.

This lane may improve methods/findings/variable reading support only when those claims are supported by the final OA scholarly source. It does not convert such support into a scientific decision or an approved extraction proposal.
