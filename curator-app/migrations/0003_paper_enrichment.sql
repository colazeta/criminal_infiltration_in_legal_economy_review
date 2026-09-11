-- CILE-ENRICH-1: independent, private enrichment of existing registered records.
-- No scientific decisions, corpus reset, review activation or public text export.
CREATE TABLE enrichment_targets (
 target_id TEXT PRIMARY KEY, cycle_id TEXT NOT NULL, record_namespace TEXT NOT NULL CHECK(record_namespace IN ('candidate','canonical')),
 record_id TEXT NOT NULL, input_sha256 TEXT NOT NULL CHECK(length(input_sha256)=64), record_json TEXT NOT NULL,
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)), first_seen_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(cycle_id,record_namespace,record_id)
);
CREATE TABLE enrichment_inputs (
 input_id TEXT PRIMARY KEY, target_id TEXT NOT NULL REFERENCES enrichment_targets(target_id),
 input_sha256 TEXT NOT NULL CHECK(length(input_sha256)=64), record_json TEXT NOT NULL, observed_at TEXT NOT NULL,
 UNIQUE(target_id,input_sha256)
);
CREATE TABLE enrichment_jobs (
 job_id TEXT PRIMARY KEY, target_id TEXT NOT NULL REFERENCES enrichment_targets(target_id),
 input_sha256 TEXT NOT NULL CHECK(length(input_sha256)=64), kind TEXT NOT NULL CHECK(kind IN ('metadata','citations','extraction','classification')),
 protocol_version TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('pending','running','completed','blocked','exhausted','superseded')),
 failure_streak INTEGER NOT NULL DEFAULT 0 CHECK(failure_streak BETWEEN 0 AND 3), attempts_total INTEGER NOT NULL DEFAULT 0,
 due_at TEXT, lease_until TEXT, lease_token TEXT, checkpoint_json TEXT NOT NULL DEFAULT '{}', error_code TEXT, updated_at TEXT NOT NULL,
 UNIQUE(target_id,input_sha256,kind,protocol_version)
);
CREATE INDEX enrichment_due ON enrichment_jobs(status,due_at);
CREATE TABLE enrichment_runs (
 run_id TEXT PRIMARY KEY, cycle_id TEXT NOT NULL, scheduled_slot TEXT NOT NULL, started_at TEXT NOT NULL,
 finished_at TEXT, lease_until TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('running','completed','partial','failed','empty')),
 selected_job_id TEXT, error_code TEXT, UNIQUE(cycle_id,scheduled_slot)
);
CREATE UNIQUE INDEX enrichment_single_active_run ON enrichment_runs(cycle_id) WHERE status='running';
CREATE TABLE enrichment_attempts (
 attempt_id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES enrichment_jobs(job_id), run_id TEXT NOT NULL REFERENCES enrichment_runs(run_id),
 started_at TEXT NOT NULL, finished_at TEXT NOT NULL, outcome TEXT NOT NULL, error_code TEXT
);
CREATE TABLE enrichment_sources (
 source_id TEXT PRIMARY KEY, target_id TEXT NOT NULL REFERENCES enrichment_targets(target_id), input_sha256 TEXT NOT NULL,
 provider TEXT NOT NULL, source_url TEXT NOT NULL, evidence_kind TEXT NOT NULL CHECK(evidence_kind IN ('abstract','metadata','full_text','full_text_excerpt','publisher_summary')),
 content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64), storage_key TEXT NOT NULL,
 version_label TEXT NOT NULL, language TEXT, retention_basis TEXT NOT NULL, licence_status TEXT NOT NULL,
 observed_at TEXT NOT NULL, UNIQUE(target_id,input_sha256,provider,source_url,evidence_kind,content_sha256)
);
CREATE TABLE enrichment_citation_observations (
 observation_id TEXT PRIMARY KEY, target_id TEXT NOT NULL REFERENCES enrichment_targets(target_id), input_sha256 TEXT NOT NULL,
 provider TEXT NOT NULL, direction TEXT NOT NULL CHECK(direction IN ('outgoing','incoming')),
 citing_identifier TEXT NOT NULL, cited_identifier TEXT NOT NULL, snapshot_id TEXT NOT NULL, source_url TEXT NOT NULL,
 observed_at TEXT NOT NULL, UNIQUE(target_id,provider,direction,citing_identifier,cited_identifier,snapshot_id)
);
CREATE TABLE enrichment_citation_coverage (
 coverage_id TEXT PRIMARY KEY, target_id TEXT NOT NULL REFERENCES enrichment_targets(target_id), input_sha256 TEXT NOT NULL,
 provider TEXT NOT NULL, direction TEXT NOT NULL CHECK(direction IN ('outgoing','incoming')), snapshot_id TEXT NOT NULL,
 source_url TEXT NOT NULL, returned_count INTEGER NOT NULL CHECK(returned_count>=0), provider_count INTEGER,
 next_cursor TEXT, status TEXT NOT NULL CHECK(status IN ('partial','provider_complete','not_returned')), observed_at TEXT NOT NULL
);
CREATE TABLE enrichment_proposals (
 proposal_id TEXT PRIMARY KEY, target_id TEXT NOT NULL REFERENCES enrichment_targets(target_id), input_sha256 TEXT NOT NULL,
 protocol_version TEXT NOT NULL, codebook_version TEXT NOT NULL, payload_sha256 TEXT NOT NULL CHECK(length(payload_sha256)=64),
 payload_json TEXT NOT NULL, generated_by TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(target_id,input_sha256,payload_sha256)
);
CREATE TABLE enrichment_studies (
 proposal_id TEXT NOT NULL REFERENCES enrichment_proposals(proposal_id), study_id TEXT NOT NULL, payload_json TEXT NOT NULL,
 PRIMARY KEY(proposal_id,study_id)
);
CREATE TABLE enrichment_datasets (
 proposal_id TEXT NOT NULL, study_id TEXT NOT NULL, dataset_id TEXT NOT NULL, payload_json TEXT NOT NULL,
 PRIMARY KEY(proposal_id,dataset_id), FOREIGN KEY(proposal_id,study_id) REFERENCES enrichment_studies(proposal_id,study_id)
);
CREATE TABLE enrichment_analyses (
 proposal_id TEXT NOT NULL, study_id TEXT NOT NULL, analysis_id TEXT NOT NULL, payload_json TEXT NOT NULL,
 PRIMARY KEY(proposal_id,analysis_id), FOREIGN KEY(proposal_id,study_id) REFERENCES enrichment_studies(proposal_id,study_id)
);
CREATE TABLE enrichment_variable_uses (
 proposal_id TEXT NOT NULL, analysis_id TEXT NOT NULL, variable_use_id TEXT NOT NULL, payload_json TEXT NOT NULL,
 PRIMARY KEY(proposal_id,variable_use_id), FOREIGN KEY(proposal_id,analysis_id) REFERENCES enrichment_analyses(proposal_id,analysis_id)
);
CREATE TABLE enrichment_findings (
 proposal_id TEXT NOT NULL, analysis_id TEXT NOT NULL, finding_id TEXT NOT NULL, payload_json TEXT NOT NULL,
 PRIMARY KEY(proposal_id,finding_id), FOREIGN KEY(proposal_id,analysis_id) REFERENCES enrichment_analyses(proposal_id,analysis_id)
);
CREATE TABLE enrichment_framework_proposals (
 proposal_id TEXT PRIMARY KEY REFERENCES enrichment_proposals(proposal_id), primary_category TEXT,
 classification_status TEXT NOT NULL CHECK(classification_status IN ('proposed','insufficient_evidence','outside_framework')),
 payload_json TEXT NOT NULL,
 CHECK(primary_category IS NULL OR primary_category IN ('aetiology','diagnosis','screening','therapy','prognosis','prevention'))
);
CREATE TRIGGER enrichment_inputs_no_update BEFORE UPDATE ON enrichment_inputs BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_inputs_no_delete BEFORE DELETE ON enrichment_inputs BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_attempts_no_update BEFORE UPDATE ON enrichment_attempts BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_attempts_no_delete BEFORE DELETE ON enrichment_attempts BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_sources_no_update BEFORE UPDATE ON enrichment_sources BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_sources_no_delete BEFORE DELETE ON enrichment_sources BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_citation_observations_no_update BEFORE UPDATE ON enrichment_citation_observations BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_citation_observations_no_delete BEFORE DELETE ON enrichment_citation_observations BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_citation_coverage_no_update BEFORE UPDATE ON enrichment_citation_coverage BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_citation_coverage_no_delete BEFORE DELETE ON enrichment_citation_coverage BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_proposals_no_update BEFORE UPDATE ON enrichment_proposals BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_proposals_no_delete BEFORE DELETE ON enrichment_proposals BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_studies_no_update BEFORE UPDATE ON enrichment_studies BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_studies_no_delete BEFORE DELETE ON enrichment_studies BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_datasets_no_update BEFORE UPDATE ON enrichment_datasets BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_datasets_no_delete BEFORE DELETE ON enrichment_datasets BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_analyses_no_update BEFORE UPDATE ON enrichment_analyses BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_analyses_no_delete BEFORE DELETE ON enrichment_analyses BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_variable_uses_no_update BEFORE UPDATE ON enrichment_variable_uses BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_variable_uses_no_delete BEFORE DELETE ON enrichment_variable_uses BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_findings_no_update BEFORE UPDATE ON enrichment_findings BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_findings_no_delete BEFORE DELETE ON enrichment_findings BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_framework_proposals_no_update BEFORE UPDATE ON enrichment_framework_proposals BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_framework_proposals_no_delete BEFORE DELETE ON enrichment_framework_proposals BEGIN SELECT RAISE(ABORT,'append_only'); END;
