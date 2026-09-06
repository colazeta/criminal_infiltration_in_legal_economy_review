# Targeted reading retrieval

When the mechanical abstract cascade or first-pass assisted search does not expose a reliable abstract, the review may run a targeted per-record retrieval pass using exact DOI, exact title, author, book or venue metadata, publisher pages, institutional repositories, book previews and verified alternate manifestations.

The goal is to improve curator reading support without changing eligibility. Higher-confidence results may replace an earlier preparatory aid through `data/curation/reading_aid_overrides.json`.

An override may upgrade a `metadata_warning` or `review_synopsis` to a `publisher_summary`, `full_text_intro` or `verified_abstract_source` only when the exact work identity and source support that label. A source that verifies only identity must not be represented as an author abstract.

Targeted retrieval remains non-decisional. Screening, canonicalisation and publication require their existing human-governed gates.
