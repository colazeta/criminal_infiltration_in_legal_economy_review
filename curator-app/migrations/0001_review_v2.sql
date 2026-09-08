-- Additive private schema. Applying this migration does NOT create a review,
-- import the legacy corpus, approve seeds, or activate any writer.
PRAGMA foreign_keys = ON;

CREATE TABLE reviews (
  review_id TEXT NOT NULL PRIMARY KEY, title TEXT NOT NULL,
  protocol_version TEXT NOT NULL, ontology_version TEXT NOT NULL,
  phase TEXT NOT NULL CHECK (phase IN ('prepared','active','paused','legacy')),
  timezone TEXT NOT NULL CHECK (timezone = 'Europe/Rome'),
  start_date TEXT, activated_at TEXT, legacy_snapshot_id TEXT REFERENCES legacy_snapshots(snapshot_id),
  created_at TEXT NOT NULL,
  CHECK (phase <> 'active' OR (start_date IS NOT NULL AND activated_at IS NOT NULL AND legacy_snapshot_id IS NOT NULL))
);
CREATE UNIQUE INDEX one_active_review ON reviews(phase) WHERE phase = 'active';

-- Bibliography is independent of membership, eligibility and publication.
CREATE TABLE scholarly_works (
  work_id TEXT NOT NULL PRIMARY KEY, title TEXT NOT NULL,
  work_type TEXT NOT NULL CHECK (work_type IN ('journal_article','book_chapter','book','working_paper','preprint','conference_paper','report','thesis','other','unknown')),
  original_language TEXT, created_at TEXT NOT NULL
);
CREATE TABLE agents (
  agent_id TEXT NOT NULL PRIMARY KEY, agent_type TEXT NOT NULL CHECK (agent_type IN ('person','organization','software')),
  display_name TEXT NOT NULL, family_name TEXT, given_name TEXT
);
CREATE TABLE publication_venues (
  venue_id TEXT NOT NULL PRIMARY KEY, title TEXT NOT NULL,
  venue_type TEXT NOT NULL CHECK (venue_type IN ('journal','edited_book','series','conference','repository','other')),
  publisher_id TEXT REFERENCES agents(agent_id), parent_venue_id TEXT REFERENCES publication_venues(venue_id)
);
CREATE TABLE expressions (
  expression_id TEXT NOT NULL PRIMARY KEY, work_id TEXT NOT NULL REFERENCES scholarly_works(work_id),
  version_type TEXT NOT NULL CHECK (version_type IN ('preprint','submitted','accepted','version_of_record','revised','translation','unknown')),
  version_label TEXT, language TEXT, publication_date TEXT,
  date_precision TEXT CHECK (date_precision IN ('year','month','day') OR date_precision IS NULL),
  venue_id TEXT REFERENCES publication_venues(venue_id), volume TEXT, issue TEXT,
  page_start TEXT, page_end TEXT, article_number TEXT, edition TEXT,
  source_url TEXT NOT NULL, observed_at TEXT NOT NULL,
  CHECK ((publication_date IS NULL) = (date_precision IS NULL))
);
CREATE TABLE contributions (
  contribution_id TEXT NOT NULL PRIMARY KEY, expression_id TEXT NOT NULL REFERENCES expressions(expression_id),
  agent_id TEXT NOT NULL REFERENCES agents(agent_id),
  role TEXT NOT NULL CHECK (role IN ('author','editor','translator','contributor','funder')),
  position INTEGER NOT NULL CHECK (position > 0), credit_role_uri TEXT,
  affiliation_id TEXT REFERENCES agents(agent_id), source_url TEXT NOT NULL,
  UNIQUE (expression_id, role, position)
);
CREATE TABLE document_sections (
  section_id TEXT NOT NULL PRIMARY KEY, expression_id TEXT NOT NULL REFERENCES expressions(expression_id),
  section_type TEXT NOT NULL CHECK (section_type IN ('abstract','introduction','background','methods','results','discussion','conclusion','limitations','references','appendix','other')),
  heading TEXT, position INTEGER NOT NULL CHECK (position > 0),
  parent_section_id TEXT REFERENCES document_sections(section_id),
  source_url TEXT NOT NULL, locator TEXT NOT NULL,
  UNIQUE (expression_id, position)
);
CREATE TABLE publication_declarations (
  declaration_id TEXT NOT NULL PRIMARY KEY, expression_id TEXT NOT NULL REFERENCES expressions(expression_id),
  declaration_type TEXT NOT NULL CHECK (declaration_type IN ('funding','conflict_of_interest','ethics','data_availability','code_availability','acknowledgement','correction','retraction')),
  statement TEXT NOT NULL, source_url TEXT NOT NULL, locator TEXT NOT NULL, observed_at TEXT NOT NULL
);
CREATE TABLE manifestations (
  manifestation_id TEXT NOT NULL PRIMARY KEY, expression_id TEXT NOT NULL REFERENCES expressions(expression_id),
  source_url TEXT NOT NULL, media_type TEXT, content_sha256 TEXT,
  storage_key TEXT, license_uri TEXT, rights_basis TEXT,
  access_status TEXT NOT NULL CHECK (access_status IN ('open','restricted','unknown')),
  acquisition_status TEXT NOT NULL CHECK (acquisition_status IN ('locator_only','acquired','failed')),
  observed_at TEXT NOT NULL,
  CHECK (acquisition_status <> 'acquired' OR (length(content_sha256) = 64 AND storage_key IS NOT NULL AND rights_basis IS NOT NULL))
);
CREATE TABLE bibliographic_identifiers (
  identifier_id TEXT NOT NULL PRIMARY KEY,
  work_id TEXT REFERENCES scholarly_works(work_id), expression_id TEXT REFERENCES expressions(expression_id),
  manifestation_id TEXT REFERENCES manifestations(manifestation_id), agent_id TEXT REFERENCES agents(agent_id),
  venue_id TEXT REFERENCES publication_venues(venue_id),
  scheme TEXT NOT NULL CHECK (scheme IN ('doi','isbn','issn','orcid','ror','handle','arxiv','pmid','url','other')),
  value TEXT NOT NULL, source_url TEXT NOT NULL, observed_at TEXT NOT NULL,
  verification_status TEXT NOT NULL CHECK (verification_status IN ('proposed','verified','disputed')),
  CHECK ((work_id IS NOT NULL) + (expression_id IS NOT NULL) + (manifestation_id IS NOT NULL) + (agent_id IS NOT NULL) + (venue_id IS NOT NULL) = 1)
);
CREATE INDEX identifier_lookup ON bibliographic_identifiers(scheme, value);
CREATE TABLE metadata_assertions (
  assertion_id TEXT NOT NULL PRIMARY KEY, work_id TEXT NOT NULL REFERENCES scholarly_works(work_id),
  expression_id TEXT REFERENCES expressions(expression_id), field_uri TEXT NOT NULL,
  value_json TEXT NOT NULL CHECK (json_valid(value_json)), source_url TEXT NOT NULL,
  observed_at TEXT NOT NULL, attributed_to TEXT NOT NULL,
  assertion_status TEXT NOT NULL CHECK (assertion_status IN ('proposed','verified','disputed')),
  supersedes_id TEXT REFERENCES metadata_assertions(assertion_id)
);
CREATE TABLE citation_relations (
  citation_id TEXT NOT NULL PRIMARY KEY, citing_work_id TEXT NOT NULL REFERENCES scholarly_works(work_id),
  cited_work_id TEXT NOT NULL REFERENCES scholarly_works(work_id),
  expression_id TEXT REFERENCES expressions(expression_id), source_url TEXT NOT NULL,
  locator TEXT NOT NULL, observed_at TEXT NOT NULL,
  verification_status TEXT NOT NULL CHECK (verification_status IN ('proposed','verified','disputed')),
  CHECK (citing_work_id <> cited_work_id)
);
CREATE TABLE work_relations_v2 (
  relation_id TEXT NOT NULL PRIMARY KEY, subject_work_id TEXT NOT NULL REFERENCES scholarly_works(work_id),
  object_work_id TEXT NOT NULL REFERENCES scholarly_works(work_id),
  relation_type TEXT NOT NULL CHECK (relation_type IN ('duplicate_of','derived_from','corrects','retracts')),
  source_url TEXT NOT NULL, rationale TEXT NOT NULL, attributed_to TEXT NOT NULL, observed_at TEXT NOT NULL,
  CHECK (subject_work_id <> object_work_id)
);

CREATE TABLE review_candidates (
  review_id TEXT NOT NULL REFERENCES reviews(review_id), candidate_id TEXT NOT NULL,
  work_id TEXT REFERENCES scholarly_works(work_id), title TEXT NOT NULL,
  identity_state TEXT NOT NULL CHECK (identity_state IN ('unresolved','verified','conflict')),
  stage TEXT NOT NULL CHECK (stage IN ('metadata','reading','screening','extraction')),
  record_version INTEGER NOT NULL DEFAULT 1 CHECK (record_version > 0),
  origin_event_id TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (review_id, candidate_id), UNIQUE (review_id, work_id)
);
CREATE TABLE legacy_references (
  review_id TEXT NOT NULL, candidate_id TEXT NOT NULL, legacy_id TEXT NOT NULL,
  snapshot_id TEXT NOT NULL, match_basis TEXT NOT NULL,
  PRIMARY KEY (review_id, candidate_id, legacy_id),
  FOREIGN KEY (review_id, candidate_id) REFERENCES review_candidates(review_id, candidate_id)
);
CREATE TABLE retrieval_attempts (
  attempt_id TEXT NOT NULL PRIMARY KEY, review_id TEXT NOT NULL, candidate_id TEXT NOT NULL,
  source_url TEXT NOT NULL, provider TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('completed','failed','unsupported','identity_conflict')),
  http_status INTEGER, error_code TEXT, duration_ms INTEGER NOT NULL CHECK (duration_ms >= 0),
  content_sha256 TEXT, retry_parent_id TEXT REFERENCES retrieval_attempts(attempt_id),
  FOREIGN KEY (review_id, candidate_id) REFERENCES review_candidates(review_id, candidate_id)
);
CREATE TABLE evidence_sources (
  review_id TEXT NOT NULL, evidence_id TEXT NOT NULL, candidate_id TEXT NOT NULL,
  manifestation_id TEXT REFERENCES manifestations(manifestation_id),
  attempt_id TEXT REFERENCES retrieval_attempts(attempt_id), source_url TEXT NOT NULL,
  evidence_kind TEXT NOT NULL CHECK (evidence_kind IN ('abstract','publisher_summary','full_text','full_text_excerpt','metadata','triage_note','model_summary')),
  identity_state TEXT NOT NULL CHECK (identity_state IN ('unresolved','verified','conflict')),
  content_sha256 TEXT NOT NULL CHECK (length(content_sha256) = 64), storage_key TEXT NOT NULL,
  rights_basis TEXT NOT NULL, observed_at TEXT NOT NULL,
  PRIMARY KEY (review_id, evidence_id),
  FOREIGN KEY (review_id, candidate_id) REFERENCES review_candidates(review_id, candidate_id)
);
CREATE TABLE evidence_spans (
  review_id TEXT NOT NULL, span_id TEXT NOT NULL, evidence_id TEXT NOT NULL,
  locator TEXT NOT NULL, start_offset INTEGER NOT NULL CHECK (start_offset >= 0),
  end_offset INTEGER NOT NULL CHECK (end_offset > start_offset),
  text_sha256 TEXT NOT NULL CHECK (length(text_sha256) = 64),
  PRIMARY KEY (review_id, span_id),
  FOREIGN KEY (review_id, evidence_id) REFERENCES evidence_sources(review_id, evidence_id)
);
CREATE TABLE decision_proposals (
  proposal_id TEXT NOT NULL PRIMARY KEY, review_id TEXT NOT NULL, candidate_id TEXT NOT NULL,
  expected_version INTEGER NOT NULL, protocol_version TEXT NOT NULL,
  payload_json TEXT NOT NULL CHECK (json_valid(payload_json)), payload_sha256 TEXT NOT NULL CHECK (length(payload_sha256) = 64),
  proposed_by TEXT NOT NULL, created_at TEXT NOT NULL,
  FOREIGN KEY (review_id, candidate_id) REFERENCES review_candidates(review_id, candidate_id)
);
CREATE TABLE approval_receipts (
  receipt_id TEXT NOT NULL PRIMARY KEY, proposal_id TEXT NOT NULL UNIQUE REFERENCES decision_proposals(proposal_id),
  review_id TEXT NOT NULL, candidate_id TEXT NOT NULL, expected_version INTEGER NOT NULL,
  payload_sha256 TEXT NOT NULL, repository TEXT NOT NULL, pr_number INTEGER NOT NULL,
  reviewed_commit TEXT NOT NULL, human_login TEXT NOT NULL, human_review_id TEXT NOT NULL,
  approved_at TEXT NOT NULL, imported_at TEXT NOT NULL,
  FOREIGN KEY (review_id, candidate_id) REFERENCES review_candidates(review_id, candidate_id),
  UNIQUE (review_id, candidate_id, expected_version)
);
CREATE TABLE screening_decisions_v2 (
  decision_id TEXT NOT NULL PRIMARY KEY, receipt_id TEXT NOT NULL UNIQUE REFERENCES approval_receipts(receipt_id),
  review_id TEXT NOT NULL, candidate_id TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('eligible_core','eligible_contextual','needs_full_text','not_eligible','duplicate','not_academic','not_retrievable')),
  rationale TEXT NOT NULL, protocol_version TEXT NOT NULL,
  supersedes_id TEXT UNIQUE REFERENCES screening_decisions_v2(decision_id), created_at TEXT NOT NULL,
  FOREIGN KEY (review_id, candidate_id) REFERENCES review_candidates(review_id, candidate_id)
);
CREATE TABLE criterion_assessments (
  decision_id TEXT NOT NULL REFERENCES screening_decisions_v2(decision_id),
  criterion_id TEXT NOT NULL CHECK (criterion_id IN ('criminal_actor','legal_economy','sustained_relation','substantive_analysis')),
  outcome TEXT NOT NULL CHECK (outcome IN ('YES','NO','UNCERTAIN')),
  rationale TEXT NOT NULL, evidence_span_ids_json TEXT NOT NULL CHECK (json_valid(evidence_span_ids_json)),
  PRIMARY KEY (decision_id, criterion_id)
);
CREATE TABLE coding_assertions_v2 (
  coding_id TEXT NOT NULL PRIMARY KEY, decision_id TEXT NOT NULL REFERENCES screening_decisions_v2(decision_id),
  dimension TEXT NOT NULL CHECK (dimension IN ('topic','infiltration_relation','criminal_actor','legal_economy_object','method','geography','sector')),
  code TEXT NOT NULL, vocabulary_version TEXT NOT NULL, rationale TEXT NOT NULL,
  evidence_span_ids_json TEXT NOT NULL CHECK (json_valid(evidence_span_ids_json)),
  supersedes_id TEXT UNIQUE REFERENCES coding_assertions_v2(coding_id)
);
CREATE TABLE assistant_observations (
  observation_id TEXT NOT NULL PRIMARY KEY, review_id TEXT NOT NULL, candidate_id TEXT NOT NULL,
  model_id TEXT NOT NULL, prompt_version TEXT NOT NULL, protocol_version TEXT NOT NULL,
  input_sha256 TEXT NOT NULL, output_json TEXT NOT NULL CHECK (json_valid(output_json)),
  evidence_span_ids_json TEXT NOT NULL CHECK (json_valid(evidence_span_ids_json)), created_at TEXT NOT NULL,
  FOREIGN KEY (review_id, candidate_id) REFERENCES review_candidates(review_id, candidate_id)
);
CREATE TABLE publication_approvals_v2 (
  publication_id TEXT NOT NULL PRIMARY KEY, decision_id TEXT NOT NULL REFERENCES screening_decisions_v2(decision_id),
  approved_payload_json TEXT NOT NULL CHECK (json_valid(approved_payload_json)),
  payload_sha256 TEXT NOT NULL, human_login TEXT NOT NULL, reviewed_commit TEXT NOT NULL,
  pr_number INTEGER NOT NULL, approved_at TEXT NOT NULL,
  publication_status TEXT NOT NULL CHECK (publication_status IN ('published','withheld')),
  supersedes_id TEXT UNIQUE REFERENCES publication_approvals_v2(publication_id)
);

CREATE TABLE search_days (
  review_id TEXT NOT NULL REFERENCES reviews(review_id), scheduled_date TEXT NOT NULL,
  timezone TEXT NOT NULL CHECK (timezone = 'Europe/Rome'), protocol_version TEXT NOT NULL,
  query_manifest_json TEXT NOT NULL CHECK (json_valid(query_manifest_json)),
  status TEXT NOT NULL CHECK (status IN ('planned','running','completed','partial','failed','missing','cancelled_authorized')),
  deadline_at TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY (review_id, scheduled_date)
);
CREATE TABLE run_attempts (
  attempt_id TEXT NOT NULL PRIMARY KEY, review_id TEXT NOT NULL, scheduled_date TEXT NOT NULL,
  attempt_number INTEGER NOT NULL CHECK (attempt_number BETWEEN 1 AND 3),
  started_at TEXT NOT NULL, finished_at TEXT, lease_until TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('running','completed','partial','failed','expired')),
  error_code TEXT, retry_after TEXT,
  UNIQUE (review_id, scheduled_date, attempt_number),
  FOREIGN KEY (review_id, scheduled_date) REFERENCES search_days(review_id, scheduled_date)
);
CREATE UNIQUE INDEX one_running_attempt ON run_attempts(review_id, scheduled_date) WHERE status = 'running';
CREATE TABLE query_executions (
  execution_id TEXT NOT NULL PRIMARY KEY, attempt_id TEXT NOT NULL REFERENCES run_attempts(attempt_id),
  review_id TEXT NOT NULL, scheduled_date TEXT NOT NULL, provider TEXT NOT NULL, query_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('completed','failed','not_run')),
  started_at TEXT NOT NULL, finished_at TEXT NOT NULL,
  occurrences_returned INTEGER CHECK (occurrences_returned >= 0),
  result_storage_key TEXT, error_code TEXT,
  FOREIGN KEY (review_id, scheduled_date) REFERENCES search_days(review_id, scheduled_date),
  UNIQUE (attempt_id, provider, query_id),
  CHECK ((status = 'completed') = (occurrences_returned IS NOT NULL)),
  CHECK (status <> 'completed' OR result_storage_key IS NOT NULL)
);
CREATE UNIQUE INDEX one_successful_checkpoint ON query_executions(review_id, scheduled_date, provider, query_id) WHERE status = 'completed';
CREATE TABLE discovery_occurrences (
  occurrence_id TEXT NOT NULL PRIMARY KEY, review_id TEXT NOT NULL REFERENCES reviews(review_id),
  execution_id TEXT REFERENCES query_executions(execution_id), candidate_id TEXT,
  provider TEXT NOT NULL, source_url TEXT NOT NULL, rank INTEGER CHECK (rank > 0),
  metadata_json TEXT NOT NULL CHECK (json_valid(metadata_json)), observed_at TEXT NOT NULL,
  FOREIGN KEY (review_id, candidate_id) REFERENCES review_candidates(review_id, candidate_id)
);
CREATE TABLE outbox (
  outbox_id TEXT NOT NULL PRIMARY KEY, review_id TEXT NOT NULL REFERENCES reviews(review_id),
  kind TEXT NOT NULL CHECK (kind IN ('search_day','scientific_pr','public_export')),
  payload_json TEXT NOT NULL CHECK (json_valid(payload_json)), created_at TEXT NOT NULL,
  delivered_at TEXT, attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0), last_error TEXT
);
CREATE TABLE operational_events (
  event_id TEXT NOT NULL PRIMARY KEY, review_id TEXT REFERENCES reviews(review_id), event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL CHECK (json_valid(payload_json)), attributed_to TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE legacy_snapshots (
  snapshot_id TEXT NOT NULL PRIMARY KEY, git_commit TEXT NOT NULL, manifest_sha256 TEXT NOT NULL,
  storage_key TEXT NOT NULL, external_state_complete INTEGER NOT NULL CHECK (external_state_complete IN (0,1)),
  restore_verified_at TEXT, created_at TEXT NOT NULL
);

CREATE TRIGGER metadata_assertions_no_update BEFORE UPDATE ON metadata_assertions BEGIN SELECT RAISE(ABORT, 'append_only:metadata_assertions'); END;

CREATE TRIGGER metadata_assertions_no_delete BEFORE DELETE ON metadata_assertions BEGIN SELECT RAISE(ABORT, 'append_only:metadata_assertions'); END;

CREATE TRIGGER citation_relations_no_update BEFORE UPDATE ON citation_relations BEGIN SELECT RAISE(ABORT, 'append_only:citation_relations'); END;

CREATE TRIGGER citation_relations_no_delete BEFORE DELETE ON citation_relations BEGIN SELECT RAISE(ABORT, 'append_only:citation_relations'); END;

CREATE TRIGGER work_relations_v2_no_update BEFORE UPDATE ON work_relations_v2 BEGIN SELECT RAISE(ABORT, 'append_only:work_relations_v2'); END;

CREATE TRIGGER work_relations_v2_no_delete BEFORE DELETE ON work_relations_v2 BEGIN SELECT RAISE(ABORT, 'append_only:work_relations_v2'); END;

CREATE TRIGGER legacy_references_no_update BEFORE UPDATE ON legacy_references BEGIN SELECT RAISE(ABORT, 'append_only:legacy_references'); END;

CREATE TRIGGER legacy_references_no_delete BEFORE DELETE ON legacy_references BEGIN SELECT RAISE(ABORT, 'append_only:legacy_references'); END;

CREATE TRIGGER retrieval_attempts_no_update BEFORE UPDATE ON retrieval_attempts BEGIN SELECT RAISE(ABORT, 'append_only:retrieval_attempts'); END;

CREATE TRIGGER retrieval_attempts_no_delete BEFORE DELETE ON retrieval_attempts BEGIN SELECT RAISE(ABORT, 'append_only:retrieval_attempts'); END;

CREATE TRIGGER evidence_sources_no_update BEFORE UPDATE ON evidence_sources BEGIN SELECT RAISE(ABORT, 'append_only:evidence_sources'); END;

CREATE TRIGGER evidence_sources_no_delete BEFORE DELETE ON evidence_sources BEGIN SELECT RAISE(ABORT, 'append_only:evidence_sources'); END;

CREATE TRIGGER evidence_spans_no_update BEFORE UPDATE ON evidence_spans BEGIN SELECT RAISE(ABORT, 'append_only:evidence_spans'); END;

CREATE TRIGGER evidence_spans_no_delete BEFORE DELETE ON evidence_spans BEGIN SELECT RAISE(ABORT, 'append_only:evidence_spans'); END;

CREATE TRIGGER decision_proposals_no_update BEFORE UPDATE ON decision_proposals BEGIN SELECT RAISE(ABORT, 'append_only:decision_proposals'); END;

CREATE TRIGGER decision_proposals_no_delete BEFORE DELETE ON decision_proposals BEGIN SELECT RAISE(ABORT, 'append_only:decision_proposals'); END;

CREATE TRIGGER approval_receipts_no_update BEFORE UPDATE ON approval_receipts BEGIN SELECT RAISE(ABORT, 'append_only:approval_receipts'); END;

CREATE TRIGGER approval_receipts_no_delete BEFORE DELETE ON approval_receipts BEGIN SELECT RAISE(ABORT, 'append_only:approval_receipts'); END;

CREATE TRIGGER screening_decisions_v2_no_update BEFORE UPDATE ON screening_decisions_v2 BEGIN SELECT RAISE(ABORT, 'append_only:screening_decisions_v2'); END;

CREATE TRIGGER screening_decisions_v2_no_delete BEFORE DELETE ON screening_decisions_v2 BEGIN SELECT RAISE(ABORT, 'append_only:screening_decisions_v2'); END;

CREATE TRIGGER criterion_assessments_no_update BEFORE UPDATE ON criterion_assessments BEGIN SELECT RAISE(ABORT, 'append_only:criterion_assessments'); END;

CREATE TRIGGER criterion_assessments_no_delete BEFORE DELETE ON criterion_assessments BEGIN SELECT RAISE(ABORT, 'append_only:criterion_assessments'); END;

CREATE TRIGGER coding_assertions_v2_no_update BEFORE UPDATE ON coding_assertions_v2 BEGIN SELECT RAISE(ABORT, 'append_only:coding_assertions_v2'); END;

CREATE TRIGGER coding_assertions_v2_no_delete BEFORE DELETE ON coding_assertions_v2 BEGIN SELECT RAISE(ABORT, 'append_only:coding_assertions_v2'); END;

CREATE TRIGGER assistant_observations_no_update BEFORE UPDATE ON assistant_observations BEGIN SELECT RAISE(ABORT, 'append_only:assistant_observations'); END;

CREATE TRIGGER assistant_observations_no_delete BEFORE DELETE ON assistant_observations BEGIN SELECT RAISE(ABORT, 'append_only:assistant_observations'); END;

CREATE TRIGGER publication_approvals_v2_no_update BEFORE UPDATE ON publication_approvals_v2 BEGIN SELECT RAISE(ABORT, 'append_only:publication_approvals_v2'); END;

CREATE TRIGGER publication_approvals_v2_no_delete BEFORE DELETE ON publication_approvals_v2 BEGIN SELECT RAISE(ABORT, 'append_only:publication_approvals_v2'); END;

CREATE TRIGGER query_executions_no_update BEFORE UPDATE ON query_executions BEGIN SELECT RAISE(ABORT, 'append_only:query_executions'); END;

CREATE TRIGGER query_executions_no_delete BEFORE DELETE ON query_executions BEGIN SELECT RAISE(ABORT, 'append_only:query_executions'); END;

CREATE TRIGGER discovery_occurrences_no_update BEFORE UPDATE ON discovery_occurrences BEGIN SELECT RAISE(ABORT, 'append_only:discovery_occurrences'); END;

CREATE TRIGGER discovery_occurrences_no_delete BEFORE DELETE ON discovery_occurrences BEGIN SELECT RAISE(ABORT, 'append_only:discovery_occurrences'); END;

CREATE TRIGGER operational_events_no_update BEFORE UPDATE ON operational_events BEGIN SELECT RAISE(ABORT, 'append_only:operational_events'); END;

CREATE TRIGGER operational_events_no_delete BEFORE DELETE ON operational_events BEGIN SELECT RAISE(ABORT, 'append_only:operational_events'); END;

CREATE TRIGGER run_attempts_final_no_update BEFORE UPDATE ON run_attempts WHEN OLD.status <> 'running' BEGIN SELECT RAISE(ABORT, 'final_attempt_immutable'); END;
CREATE TRIGGER run_attempts_no_delete BEFORE DELETE ON run_attempts BEGIN SELECT RAISE(ABORT, 'attempt_history_immutable'); END;

CREATE TRIGGER review_activation_requires_snapshot_insert BEFORE INSERT ON reviews WHEN NEW.phase='active' AND NOT EXISTS (SELECT 1 FROM legacy_snapshots WHERE snapshot_id=NEW.legacy_snapshot_id AND external_state_complete=1 AND restore_verified_at IS NOT NULL) BEGIN SELECT RAISE(ABORT, 'verified_complete_snapshot_required'); END;
CREATE TRIGGER review_activation_requires_snapshot_update BEFORE UPDATE ON reviews WHEN NEW.phase='active' AND NOT EXISTS (SELECT 1 FROM legacy_snapshots WHERE snapshot_id=NEW.legacy_snapshot_id AND external_state_complete=1 AND restore_verified_at IS NOT NULL) BEGIN SELECT RAISE(ABORT, 'verified_complete_snapshot_required'); END;

CREATE TRIGGER legacy_snapshots_no_update BEFORE UPDATE ON legacy_snapshots BEGIN SELECT RAISE(ABORT, 'append_only:legacy_snapshots'); END;
CREATE TRIGGER legacy_snapshots_no_delete BEFORE DELETE ON legacy_snapshots BEGIN SELECT RAISE(ABORT, 'append_only:legacy_snapshots'); END;
