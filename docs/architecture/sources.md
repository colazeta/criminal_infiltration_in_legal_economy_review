# Current storage authorities and data flows

Status is based on inspected code/configuration and the separately identified live
receipts, not on directory names. This is the pre-cutover state, not the desired
claim that all sources have already been consolidated. Paths below enumerate the
active families; the generated SQL dictionary lists every physical table/column.

| Location | Contents / identity | Writer and update | Reader | Current role |
|---|---|---|---|---|
| `data/curation/review_queue.csv` | Candidate bibliography, origin, provisional status; `candidate_id` | Sole automatic intake recovery, reviewed metadata/identity repairs, curation PRs | Register builder, enrichment target synchroniser, curation scripts | Active authority for operational candidates |
| `data/curation/actions.csv` | Attributed append-only candidate actions; `action_id` and candidate FK | Reviewed `apply_candidate_decision.py` | Queue validation/curation | Decision history; empty in baseline |
| `data/curation/intake_access/*.json` | Immutable intake receipts; run/candidate identity | Terminal-driven intake importer | Intake-history validation, coverage recovery | Original ingest evidence, not current eligibility |
| `abstract_coverage.csv`, `retrieval_coverage.csv`, `access_coverage.csv` under `data/curation/` | Candidate-bound coverage/locator observations | Backfill/retrieval/access scripts and reviewed repairs | Support builder, curator surface | Active current projections with partially independent update paths |
| `data/curation/access_evidence.csv` | Candidate-bound verified access provenance | Reviewed access evidence | Coverage reconciliation | Authority for its access assertions; baseline empty |
| `reading_aids.json`, `reading_aid_overrides.json` | Paraphrase/support and source provenance; candidate IDs | Reviewed reading-support/reconciliation scripts | `build_paper_support.py` | Active support sources; overrides currently replace by candidate key |
| `residual_abstract_resolution.json` | Candidate-bound assisted resolution observations | Reviewed resolution process | Resolver/support scripts | Source observation ledger |
| `verified_candidate_metadata_repairs.json`, `verified_source_link_repairs.json`, `verified_identity_resolutions.json` | Reviewed, bounded repair declarations | Reviewed PRs | Dedicated reconciliation workflows | Governed input instructions; not independent current bibliography |
| `data/registry/papers.csv`, `work_identifiers.csv`, `work_relations.csv` | Canonical works, alternative IDs, curator identity relations | Reviewed curator PRs | Core/secondary builders, identity validators | Canonical authority; current work population empty |
| `screening_decisions.csv`, `paper_codes.csv`, `publications.csv`, `secondary_publications.csv`, `open_access_assessments.csv` under `data/registry/` | Versioned decisions, coding, publication and access | Explicit reviewed curator actions | Publication gates and deterministic exports | Scientific/publication authority; baseline rows empty |
| `discovery_events.csv`, `execution_metrics.csv` under `data/registry/` | Canonical provenance and historical E1–E3 metrics | Governed review operations | Archive/saturation builder | Separate work-level history; current baseline empty |
| `taxonomy.csv`, `exclusion_reasons.csv`, `secondary_collections.csv` | Controlled codes / definitions | Reviewed contract changes | Validators/curator/builders | Controlled-domain authority |
| `archive_versions.csv`, `editorial_summary.csv` | Version manifest / aggregate editorial state | Release/curation maintainer | Public builds | Release/aggregate metadata; not candidate or study identity |
| `PaperEnrichmentStore` SQL (`cile-enrichment-1`) | 38 configured tables; the dated initial census proved 22. Targets, immutable inputs, sources, jobs/attempts, proposals, scoped facts and joins, receipts, documents/bibliography | Signed domain operations, private console, Worker schedule; validated atomic SQLite transactions | Private enrichment APIs and closed public projections use normalized extractions after migration 0007 | Active private enrichment authority; target bibliography is still copied from Pages |
| Immutable extraction `payload_json` columns | Original closed-schema submissions and child snapshots; proposal ID and content digest | Written atomically once with the normalized graph; old proposals backfilled with a verified receipt | Migration and integrity audit only; ordinary private/public readers reconstruct the graph | Retained input/audit history, no independent mutable current extraction source |
| Same object's `evidence:*`, `document:*` KV | Chunked private source strings and original PDF bytes; storage key/content digest | Private adapters, readback before SQL reference | Extraction validation, public redacted projection, rights-gated document delivery | Private content authority; document bytes are not in Pages/Git |
| Same object's schema/activation/nonce/checkpoint keys | Migration digests, exact-deployment activation, one-use nonces, private calibration checkpoints | Store service and schedule | Readiness/authentication/resumption | Operational state; not scientific records |
| `SubmissionCoordinator` Durable Objects | Submission coordination, idempotency and provider budget usage | Existing curator Worker/coordinator | Curator submission and provider guards | Active operational state; separate from research facts |
| Optional `REVIEW_DB` / `REVIEW_EVIDENCE` D1/R2 | Prepared V2 tables / source objects | Optional provisioning, gated V2 APIs | V2 runner/console when enabled | Deployment/use not established by repository migrations; do not label active |
| GitHub candidate issues and annotation comments | Issue body snapshots, manual support, source references, review instructions; GitHub IDs and embedded candidate IDs | Existing automation and curator | Private curator; currently also `paper-sheet-manual.js` in public browser | Active input **and competing reading source**; must be acquired into governed archive |
| GitHub intake issues / ledger #30 | Completed/failed search terminals and intake manifests; run IDs | Discovery task under idempotency rules | Recovery and metrics workflows | Ingress/operational audit; not proof of candidate persistence |
| GitHub checkpoints #696 / #727 and related operational issues | Non-decisional query checkpoints / asserted sheet-coverage progress | Authorised tasks | Task resume logic | Operational history; coverage assertions require independent archive readback |
| GitHub PR bodies, reviews, commits, workflow artifacts/logs | Proposed changes, human approval evidence, deployment receipts | Maintainers, authenticated reviewers, Actions | Import approval verification, release audit | Governance/audit; logs alone do not establish saved paper content |
| ChatGPT scheduled-task configuration | Prompt, schedule, enabled state, task IDs | Owner-authorised task configuration | Task runtime | Active operational instructions; must agree with repository writer contract |
| `site/data/*.json`, `site/data/*.csv`, `site/paper-support.json`, generated inline HTML | Closed register/corpus/metrics/support projections | Python build/release scripts | Public browser and **current Worker target sync** | Derived exports; reverse ingestion into Worker is an authority-cycle defect |
| Public Worker research/index/completion/assets APIs | Allowlisted projections of private enrichment | Runtime projectors | Sheets/filters/category/geography/statistics scripts | Derived live API, presently not the same snapshot as all static sources |
| PR #773 `reading-snapshot.json` preview / build artifacts | Aggregation of GitHub, support and research API reads | Proposed preview builder | Proposed reading adapter | Unmerged derived preview; not an archive migration or authority |
| Browser in-memory maps / pending fetches | Temporary support, annotation and research responses | Page code | Current page only | Cache/transport; never a scientific state or durable receipt |
| `data/legacy/**`, preserved Git branch/history | Pre-reset corpus, decisions, retired issues, original versions | Preservation process; no current rewriting | Historical audit only | Historical evidence; excluded from active corpus |
| `config/*.json`, ontology, schemas, calibration manifests | Source policy, limits, seeds, model/protocol contracts | Reviewed technical/scientific changes | Validators, acquisition, gates | Configuration/governance; existence does not establish executed acquisition or approval |

## Contradictions and precedence

- `docs/governance/data-model.md` historically says curation is never public.
  The later owner-authorised provisional register and public support projections
  supersede that statement for their closed allowlists. Notes/evidence stay private.
- `review-v2-model.md` historically cites profile 0.2.0. The machine normative
  current profile is 0.4.3; historical text does not select the active storage engine.
- Source documents have Exa-first historical clauses, while the later two-lane
  owner amendment selects Parallel Search. Preserve the clauses as history and
  apply the later explicit owner amendment; do not infer source rights from a name.
- Two-lane documents, the active :10 task, the disabled :40 task and the Worker's
  :40 schedule are different records. Check actual enabled state. No new scheduler
  is required to reconcile them.
- A task statement that sheet coverage is finished is not an authoritative count.
  Marker coverage, eight-section support, schema-valid extraction, assessment
  completion, accepted validation and corpus inclusion have separate definitions.
- The override dictionary's current last-key replacement and the browser's latest
  matching comment selection must become explicit version/supersession decisions.
  Contradictory assertions should be retained, not erased by dictionary update.

These clarifications preserve historical documents. The current governing order is:
the owner's explicit current mandate; the normative ontology/profile and its
amendments; current domain contracts; dated historical implementation notes.
No precedence rule supplies missing scientific identity or publication approval.
