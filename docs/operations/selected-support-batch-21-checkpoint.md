# Selected-support batch 21 checkpoint

Status: **PERSISTENCE_PENDING**

Base main at checkpoint creation: `5b2f6775b9f596e0ca8ae478f4989f5fd30f32c3`.
Owning branch: `maintenance/parallel-search-oa-batch-21`.

This is a non-decisional recovery checkpoint for candidate-bound retrieval support. It does not nominate candidates, change eligibility, canonical identity, framework labels, scientific proposals or the private evidence namespace.

## Verified candidate support

### CAND-ACADEMIC-2026-09-13-EXTRA-c71ea3b3c996-001 — Mafia's infiltration and spillover effects in the construction sector

- Existing registered identity: Massimiliano Ferraresi; Leonzio Rizzo; Riccardo Secomandi.
- Final source used for reading support: `https://lagv2019.sciencesconf.org/248734/document`.
- Retrieval provenance: Parallel Search, exact-title/author search followed by full source fetch.
- Evidence level: `full_text`.
- Proposed reading-aid kind: `full_text_intro`.
- Source-supported synopsis: the conference paper uses a geo-localised dataset of Italian firms to examine local economic spillovers around municipalities whose councils are dissolved for Mafia infiltration. It reports lower value added among construction firms in neighbouring municipalities.
- Boundary: the public paper was read through the final scholarly source; no full-text bytes were ingested into the governed private store and no OA-retention right is inferred.

### CAND-ACADEMIC-2026-09-13-EXTRA-c8d693f88061-001 — Conspiracy among the many: the mafia in legitimate industries

- Existing registered manifestation: chapter in *The Economics of Organised Crime*.
- Final publisher locator used for support: `https://www.cambridge.org/core/books/economics-of-organised-crime/conspiracy-among-the-many-the-mafia-in-legitimate-industries/408430B12EABBB42BC570DB11B2FEE51`.
- Retrieval provenance: Parallel Search, exact-title search followed by publisher-page fetch.
- Evidence level: `abstract_only` / publisher-visible summary; the full chapter body was not verified accessible.
- Proposed reading-aid kind: `publisher_summary`.
- Source-supported synopsis: the chapter examines the modes through which Mafia organisations exercise influence in legitimate industries in Sicily and the United States.
- Version boundary: search also surfaced the Springer chapter DOI `10.1007/978-1-349-62853-7_5` and a later Taylor & Francis reprint. These are not silently substituted for or merged with the currently registered Cambridge manifestation; publication-year/version reconciliation remains separate.

### CAND-ACADEMIC-2026-09-13-EXTRA-ff172108cfd0-005 — L’infiltration mafieuse dans l’économie légale

- Existing registered source: `https://www.afri-ct.org/article/l-infiltration-mafieuse-dans-l`.
- Retrieval provenance: Parallel Search, exact-title/domain search followed by authoritative Centre Thucydide page fetch.
- Evidence level: `partial_text` / authoritative article page; no separate stable PDF manifestation was established in this pass.
- Proposed reading-aid kind: `publisher_summary` unless a subsequent exact full-text manifestation is verified.
- Source-supported synopsis: the article frames organised crime as both a financial and productive phenomenon and analyses money as a link between legal and illegal economies, relating money laundering to usury and racketeering and discussing uncertainty created by Mafia infiltration of the legal economy.
- Boundary: claims beyond the authoritative page content remain `not_verifiable`; no private source ingestion or scientific decision is inferred.

## Exact persistence blocker

The current tool surface can create/update complete GitHub files but does not provide a safe patch/working-tree mutation for the existing monolithic `data/curation/reading_aid_overrides.json`. The execution container also cannot resolve `github.com`, so it cannot obtain a checked-out repository on which to run the required deterministic preparation locally. Replacing the whole override file manually from a truncated connector response would risk overwriting concurrent state and is therefore not safe.

No support projection is claimed persisted by this checkpoint. `data/curation/reading_aid_overrides.json`, `retrieval_coverage.csv`, `abstract_coverage.csv` and `site/data/*` are unchanged by this checkpoint.

## Next safe action

Reuse this same branch/PR. Starting from the then-current main, reconcile non-destructively, add the verified reading-aid records above to `data/curation/reading_aid_overrides.json`, then run:

```sh
python3 scripts/retrieval/selected_paper_delivery.py --prepare --validate
python3 scripts/retrieval/apply_verified_reading_locators.py --check
```

The expected deterministic effect is a full-text retrieval promotion only for `CAND-ACADEMIC-2026-09-13-EXTRA-c71ea3b3c996-001`; the other two must not be promoted to full text without stronger evidence. Commit the generated coverage/site projections on this same branch, inspect the exact final diff and review threads, require ordinary CI on the final head, and merge only with expected-head protection when green. Until then this branch remains `PERSISTENCE_PENDING`, not delivered support.
