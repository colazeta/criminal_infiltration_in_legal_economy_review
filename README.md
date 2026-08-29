# Criminal Infiltration Literature Archive

A governed, reproducible archive of scholarly work on **criminal infiltration in
the legal economy**.

**Public archive:**
[colazeta.github.io/criminal_infiltration_in_legal_economy_review](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/)

The repository has two connected purposes:

1. maintain an auditable review pipeline, from discovery to screening and coding;
2. publish a searchable archive generated only from canonical included records.

It is a **living curated evidence map**, not yet a completed or saturated
systematic review.

## Publication boundary

The public site is built from `data/registry/` only. A work appears online only
when it has:

- a canonical paper record;
- at least one discovery event;
- exactly one current screening decision;
- an included status and a public relevance note.

Files under `data/raw/` are evidence and editorial inputs. Candidates, unresolved
records, duplicates and exclusions are never silently promoted or published as
relevant literature.

| Repository layer | Purpose | Published on the site |
|---|---|---|
| `data/registry/` | Canonical works, provenance, decisions and codes | Yes, after validation |
| `data/raw/` | Immutable retrieval and audit inputs | No |
| `docs/executions/` | Execution and decision logs | No |
| `site/data/` | Deterministic public JSON and CSV exports | Yes |

## Browse and build the archive

The site is static and has no live API dependency. From a clean checkout:

```bash
python3 scripts/build_archive.py
python3 scripts/validation/validate_repo_governance.py
python3 scripts/validation/validate_archive.py
python3 -m http.server 8000 --directory site
```

Open `http://localhost:8000`. The same build runs in continuous integration
before GitHub Pages deployment.

## Review workflow

1. protocol and governance setup;
2. E0 precision-first seed construction;
3. E1 database/API discovery;
4. E2 backward citation snowballing;
5. E3 forward citation snowballing;
6. title/abstract and, where needed, full-text screening;
7. canonical inclusion, coding and repeated executions until the documented
   saturation rule can be assessed.

E0 establishes the initial nucleus and cannot establish saturation.

## Repository map

- `docs/literature_review_protocol.md`: authoritative review protocol;
- `docs/eligibility_codebook.md`: inclusion boundary and decision vocabulary;
- `docs/archive_data_model.md`: public-data contract and publication rules;
- `data/registry/`: source of truth for the public corpus;
- `data/raw/`: retrieval snapshots, screening inputs and audit staging;
- `scripts/build_archive.py`: deterministic public export builder;
- `scripts/validation/`: governance, registry and public-output checks;
- `site/`: accessible static archive and generated data exports;
- `.github/workflows/deploy-pages.yml`: build and GitHub Pages deployment;
- `WORKFLOW.md` and `docs/SYMPHONY_SETUP.md`: optional issue orchestration,
  separate from the scientific workflow.

## Scientific safeguards

- Bibliographic metadata, identifiers and screening outcomes must never be
  invented.
- Retrieval heuristics can create leads but cannot make inclusion decisions.
- Core infiltration evidence is kept separate from contextual and methodological
  literature.
- Money laundering, corruption, facilitation, passive criminal investment and
  corporate offending are not treated as infiltration unless the study provides
  evidence of sustained criminal access, influence, participation, control or
  organisational embeddedness in the legal economy.
- No full texts are redistributed by the site; it publishes metadata,
  classifications, provenance and lawful external links.

See `AGENTS.md` for repository-wide automation governance.
