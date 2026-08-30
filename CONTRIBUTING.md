# Contributing

Contributions are welcome as candidate suggestions, metadata corrections,
screening evidence, methodology changes or software fixes.

## Literature candidates

Open a **Candidate literature intake** issue. Supply stable metadata and source
links; do not paste copyrighted full text. A candidate issue is not an inclusion
decision and must not assign a canonical `paper_id`.

For a full corpus-expansion round, open an **E1–E3 review cycle** issue and
follow the [expansion strategy](docs/methodology/expansion.md). Do not present a
single search, a fixed top-N result list or a surveillance batch as a completed
review cycle.

## Metadata or screening changes

Use the corresponding issue form. Registry changes should be one auditable unit:
canonical work, identifiers, discovery event, current decision and publication
annotation are updated together where applicable. Preserve earlier decisions by
marking them non-current rather than deleting them.

Repository owners may use the [curator desk](docs/operations/curation.md) for
three routine, explicit actions: changing a primary topic, excluding a reviewed
work and joining a confirmed duplicate. The workflow prepares the coordinated
registry changes and runs the complete validation set.

## Code and documentation

Create a focused branch/PR, follow `AGENTS.md`, and report the validation commands
you ran. Registry, workflow and site changes require the full validation set.

## Evidence and rights

- Do not invent missing fields or eligibility rationales.
- Do not commit secrets, private reviewer data or unlicensed full text.
- Link to lawful access locations; a DOI or search result does not establish reuse rights.
- Declare external retrieval and the exact sources used in the PR.

All publication changes require human review and are never auto-merged.
