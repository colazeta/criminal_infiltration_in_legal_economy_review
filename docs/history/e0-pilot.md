# Retired E0/E0R1 pilot (2026-04-29)

The first identifier-first pilot was retired from the active pipeline. It sent
queries to sources other than those assigned in the plan, used a fixed top-five
limit, discarded abstracts and discovery-event multiplicity, and represented
request failures as empty responses. It therefore cannot support recall,
coverage or saturation claims.

Two compact audit tables remain under `data/legacy/e0/`:

- `candidate_outcomes.csv` — 53 reviewed candidate outcomes;
- `promotion_audit.csv` — the 13-row pre-import staging decision set.

They are non-authoritative and are never read by the public build. The original
raw snapshots and execution notes remain recoverable in Git at commit `9d32106`.

Candidate rows C001, C002 and C003 were later resolved as three DOI
manifestations of canonical work P000002. The pilot promoted C002 using
title-level evidence while C001 remained pending abstract review. Because the
preserved Crossref snapshot contains no abstract, release 0.2.0 retains the
bibliographic work and its identifiers but withholds it from the public archive
pending substantive human screening.

Key preserved checksums:

| Artifact at `9d32106` | SHA-256 |
|---|---|
| `data/raw/e0_identifier_first_raw/crossref_Q01.json` | `7b29fb4c83d0e71553d589830100a71aea014cbcd8f267519d4cdb9943219159` |
| `data/raw/e0_verified_seed_candidates_reviewed.csv` | `8336f4ee5e2a29b5f3ccad0ebe31981643473a2a363f90281115247f2cacb583` |
| `data/raw/e0_seed_promotion_staging_audited.csv` | `ad17097e385f85da06f184f8578862fd7dd4c802aab10e8c76d11fa8b6c3ae22` |

Current canonical imports are governed only by `data/registry/`. Future searches
must follow the source-specific discovery protocol and preserve explicit failure
states.
