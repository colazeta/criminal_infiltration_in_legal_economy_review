# Start here: repository index

This page is the shortest route through the project. The repository maintains a
living, searchable archive of research on criminal infiltration in the legal
economy. Discovery, scientific screening and public release are deliberately
separate steps.

## In one minute

- **Browse the public corpus:** [GitHub Pages archive](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/)
- **Understand the scientific scope:** [protocol](docs/methodology/protocol.md) and [eligibility codebook](docs/methodology/eligibility.md)
- **See how the corpus will grow:** [literature expansion strategy](docs/methodology/expansion.md)
- **Suggest a paper:** [open a candidate intake issue](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/new?template=candidate_intake.yml)
- **Understand the data:** [registry index](data/registry/README.md)
- **Publish or troubleshoot the website:** [GitHub Pages guide](docs/operations/github-pages.md)

The public archive can legitimately contain zero records while screening or
independent publication review is incomplete. That is a safety state, not a
technical failure and not a claim that no relevant literature exists.

## What do you want to do?

| Goal | Start here | Expected result |
|---|---|---|
| Browse approved papers | [Public archive](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/) | Searchable cards plus JSON/CSV downloads |
| Understand what counts as infiltration | [Eligibility codebook](docs/methodology/eligibility.md) | A four-part inclusion test and exclusion vocabulary |
| Expand the literature | [Expansion strategy](docs/methodology/expansion.md) | A complete E1–E3 search cycle with auditable coverage |
| Run a search cycle | [E1–E3 cycle issue](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/new?template=review_cycle.yml) | Frozen queries, citation frontier, failures and metrics |
| Propose one candidate | [Candidate intake issue](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/new?template=candidate_intake.yml) | A staged lead, not an inclusion decision |
| Correct metadata | [Metadata issue](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/new?template=metadata_correction.yml) | A source-backed correction for human review |
| Review eligibility evidence | [Screening issue](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/new?template=screening_review.yml) | A proposed versioned screening decision |
| Understand the source of truth | [Data model](docs/governance/data-model.md) | Keys, histories and the fail-closed publication gate |
| Release a corpus version | [Release runbook](docs/operations/release.md) | A reviewed version, deterministic export and deployment |
| Put the site online | [GitHub Pages guide](docs/operations/github-pages.md) | A deployment from `main` through GitHub Actions |
| Check project limitations | [Reporting standard](docs/methodology/reporting.md) | PRISMA-oriented evidence and missing elements |

## How one paper moves through the project

1. A search or a person creates a **candidate intake issue**.
2. Metadata and identifiers are verified; duplicate manifestations are linked.
3. A human screener records an evidence-backed, versioned decision.
4. A curator prepares a separate publication change and public annotation.
5. The validators rebuild the archive from governed registries only.
6. A person reviews and merges the change; GitHub Pages deploys from `main`.

No search tool can skip a step, assign eligibility or publish a record.

## Repository map

| Area | Contents |
|---|---|
| [`data/registry/`](data/registry/README.md) | Canonical works, identifiers, discovery events, decisions, codes and versioned publication state |
| [`data/legacy/`](data/legacy/) | Retired pilot evidence retained only for audit |
| [`docs/methodology/`](docs/README.md#methodology) | Scope, eligibility, discovery, expansion, saturation and reporting |
| [`docs/governance/`](docs/README.md#governance) | Data contract and authorised sources/connectors |
| [`docs/operations/`](docs/README.md#operations) | Automation, release and GitHub Pages runbooks |
| [`scripts/`](scripts/) | Deterministic build, validation and saturation reporting |
| [`tests/`](tests/) | Negative publication-gate and search-cycle tests |
| [`site/`](site/) | Static public interface and generated JSON/CSV |
| [`.github/`](.github/) | Issue forms, CI, Pages deployment and dependency updates |

## Non-negotiable boundaries

- Candidate discovery is not screening.
- Screening is not publication.
- Similarity is not automatic deduplication.
- A failed source is not a zero-result search.
- An incomplete E1–E3 cycle cannot support a saturation judgement.
- Registry and publication changes are never auto-merged.

For the complete automation contract, read [`AGENTS.md`](AGENTS.md).
