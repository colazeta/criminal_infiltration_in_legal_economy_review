-- Candidate-bound observations; no work reconciliation or scientific decision.

CREATE TABLE enrichment_candidate_records (
 
 candidate_id TEXT NOT NULL, cycle_id TEXT NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(candidate_id,cycle_id)
);

CREATE TABLE enrichment_candidate_revisions (
 
 revision_id TEXT NOT NULL PRIMARY KEY, candidate_id TEXT NOT NULL, cycle_id TEXT NOT NULL,
 domain TEXT NOT NULL CHECK(domain IN ('bibliography','abstract','retrieval','access')),
 source_commit TEXT NOT NULL CHECK(length(source_commit)=40),
 content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64),
 storage_key TEXT NOT NULL UNIQUE, observed_at TEXT NOT NULL,
 UNIQUE(revision_id,candidate_id,cycle_id,domain),
 FOREIGN KEY(candidate_id,cycle_id) REFERENCES enrichment_candidate_records(candidate_id,cycle_id)
);

CREATE TABLE enrichment_candidate_heads (
 
 candidate_id TEXT NOT NULL, cycle_id TEXT NOT NULL, domain TEXT NOT NULL,
 revision_id TEXT NOT NULL, record_version INTEGER NOT NULL CHECK(record_version>=1),
 state TEXT NOT NULL CHECK(state IN ('active','withdrawn')), updated_at TEXT NOT NULL,
 PRIMARY KEY(candidate_id,cycle_id,domain),
 FOREIGN KEY(revision_id,candidate_id,cycle_id,domain)
 REFERENCES enrichment_candidate_revisions(revision_id,candidate_id,cycle_id,domain)
);

CREATE TABLE enrichment_candidate_receipts (
 
 receipt_id TEXT NOT NULL PRIMARY KEY, candidate_id TEXT NOT NULL, cycle_id TEXT NOT NULL,
 domain TEXT NOT NULL, revision_id TEXT NOT NULL, previous_revision_id TEXT,
 action TEXT NOT NULL CHECK(action IN ('initialise','observe','supersede','withdraw')),
 expected_version INTEGER NOT NULL CHECK(expected_version>=0), persisted_at TEXT NOT NULL,
 FOREIGN KEY(revision_id,candidate_id,cycle_id,domain)
 REFERENCES enrichment_candidate_revisions(revision_id,candidate_id,cycle_id,domain),
 FOREIGN KEY(previous_revision_id) REFERENCES enrichment_candidate_revisions(revision_id)
);

CREATE TABLE enrichment_candidate_values (
 
 revision_id TEXT NOT NULL REFERENCES enrichment_candidate_revisions(revision_id),
 field TEXT NOT NULL CHECK(field IN ('providers_tried','resolution_sources','source_links','source_query_id','source_urls')), position INTEGER NOT NULL CHECK(position>=0),
 value TEXT NOT NULL CHECK(length(value)>0), PRIMARY KEY(revision_id,field,position)
);

CREATE TABLE enrichment_candidate_bibliography (
 revision_id TEXT NOT NULL PRIMARY KEY REFERENCES enrichment_candidate_revisions(revision_id),
 title TEXT NOT NULL,
 doi TEXT NOT NULL,
 authors TEXT NOT NULL,
 year TEXT NOT NULL,
 venue TEXT NOT NULL,
 work_type TEXT NOT NULL,
 source TEXT NOT NULL,
 other_identifiers TEXT NOT NULL,
 verification_status TEXT NOT NULL,
 metadata_confidence TEXT NOT NULL,
 intake_assessment TEXT NOT NULL,
 intake_reason TEXT NOT NULL,
 possible_duplicate TEXT NOT NULL,
 metadata_conflict TEXT NOT NULL,
 required_human_action TEXT NOT NULL,
 origin TEXT NOT NULL,
 legacy_scope_fit TEXT NOT NULL,
 legacy_recommendation TEXT NOT NULL,
 legacy_reason TEXT NOT NULL,
 legacy_priority TEXT NOT NULL,
 review_stage TEXT NOT NULL CHECK(review_stage IN ('metadata_fix','manual_review','abstract_full_text_review','legacy_rejection_review','seed_validation','title_abstract','full_text','data_extraction','appraisal')),
 current_status TEXT NOT NULL CHECK(current_status IN ('pending','screened_eligible_core','screened_eligible_contextual','needs_full_text','screened_not_eligible','duplicate_confirmed','screened_not_academic','screened_not_retrievable')),
 current_decision TEXT NOT NULL,
 exclusion_reason_code TEXT NOT NULL,
 topic_code TEXT NOT NULL,
 duplicate_target_id TEXT NOT NULL,
 secondary_collection_code TEXT NOT NULL,
 secondary_collection_rationale TEXT NOT NULL,
 last_action_id TEXT NOT NULL,
 materialised_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 provenance TEXT NOT NULL
);

CREATE TRIGGER candidate_bibliography_scope BEFORE INSERT ON enrichment_candidate_bibliography WHEN NOT EXISTS(SELECT 1 FROM enrichment_candidate_revisions WHERE revision_id=NEW.revision_id AND domain='bibliography') BEGIN SELECT RAISE(ABORT,'candidate_domain_mismatch'); END;

CREATE TABLE enrichment_candidate_abstract (
 revision_id TEXT NOT NULL PRIMARY KEY REFERENCES enrichment_candidate_revisions(revision_id),
 observed_title TEXT NOT NULL,
 observed_doi TEXT NOT NULL,
 coverage_status TEXT NOT NULL CHECK(coverage_status IN ('available','needs_web_search','unresolved','unavailable')),
 abstract_source TEXT NOT NULL,
 article_url TEXT NOT NULL,
 match_type TEXT NOT NULL,
 match_score TEXT NOT NULL,
 provider_errors TEXT NOT NULL,
 checked_at TEXT NOT NULL,
 notes TEXT NOT NULL
);

CREATE TRIGGER candidate_abstract_scope BEFORE INSERT ON enrichment_candidate_abstract WHEN NOT EXISTS(SELECT 1 FROM enrichment_candidate_revisions WHERE revision_id=NEW.revision_id AND domain='abstract') BEGIN SELECT RAISE(ABORT,'candidate_domain_mismatch'); END;

CREATE TABLE enrichment_candidate_retrieval (
 revision_id TEXT NOT NULL PRIMARY KEY REFERENCES enrichment_candidate_revisions(revision_id),
 observed_title TEXT NOT NULL,
 observed_doi TEXT NOT NULL,
 resolution_status TEXT NOT NULL,
 best_url TEXT NOT NULL,
 best_url_kind TEXT NOT NULL,
 full_text_url TEXT NOT NULL,
 open_access_url TEXT NOT NULL,
 landing_url TEXT NOT NULL,
 doi_url TEXT NOT NULL,
 resolved_doi TEXT NOT NULL,
 match_method TEXT NOT NULL,
 match_confidence TEXT NOT NULL,
 checked_at TEXT NOT NULL,
 notes TEXT NOT NULL
);

CREATE TRIGGER candidate_retrieval_scope BEFORE INSERT ON enrichment_candidate_retrieval WHEN NOT EXISTS(SELECT 1 FROM enrichment_candidate_revisions WHERE revision_id=NEW.revision_id AND domain='retrieval') BEGIN SELECT RAISE(ABORT,'candidate_domain_mismatch'); END;

CREATE TABLE enrichment_candidate_access (
 revision_id TEXT NOT NULL PRIMARY KEY REFERENCES enrichment_candidate_revisions(revision_id),
 observed_title TEXT NOT NULL,
 observed_doi TEXT NOT NULL,
 access_status TEXT NOT NULL CHECK(access_status IN ('open','restricted','unknown')),
 access_kind TEXT NOT NULL,
 access_url TEXT NOT NULL,
 evidence_source TEXT NOT NULL,
 evidence_detail TEXT NOT NULL,
 checked_at TEXT NOT NULL,
 notes TEXT NOT NULL
);

CREATE TRIGGER candidate_access_scope BEFORE INSERT ON enrichment_candidate_access WHEN NOT EXISTS(SELECT 1 FROM enrichment_candidate_revisions WHERE revision_id=NEW.revision_id AND domain='access') BEGIN SELECT RAISE(ABORT,'candidate_domain_mismatch'); END;

CREATE INDEX candidate_revision_identity ON enrichment_candidate_revisions(candidate_id,cycle_id,domain);

CREATE TRIGGER candidate_head_cas BEFORE UPDATE ON enrichment_candidate_heads WHEN NEW.candidate_id<>OLD.candidate_id OR NEW.cycle_id<>OLD.cycle_id OR NEW.domain<>OLD.domain OR NEW.record_version<>OLD.record_version+1 BEGIN SELECT RAISE(ABORT,'candidate_head_concurrency'); END;

CREATE TRIGGER candidate_no_republication BEFORE UPDATE ON enrichment_candidate_heads WHEN OLD.state='withdrawn' BEGIN SELECT RAISE(ABORT,'candidate_restore_requires_reviewed_procedure'); END;

CREATE TRIGGER enrichment_candidate_records_no_update BEFORE UPDATE ON enrichment_candidate_records BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_records_no_delete BEFORE DELETE ON enrichment_candidate_records BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_revisions_no_update BEFORE UPDATE ON enrichment_candidate_revisions BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_revisions_no_delete BEFORE DELETE ON enrichment_candidate_revisions BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_heads_no_delete BEFORE DELETE ON enrichment_candidate_heads BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_receipts_no_update BEFORE UPDATE ON enrichment_candidate_receipts BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_receipts_no_delete BEFORE DELETE ON enrichment_candidate_receipts BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_values_no_update BEFORE UPDATE ON enrichment_candidate_values BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_values_no_delete BEFORE DELETE ON enrichment_candidate_values BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_bibliography_no_update BEFORE UPDATE ON enrichment_candidate_bibliography BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_bibliography_no_delete BEFORE DELETE ON enrichment_candidate_bibliography BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_abstract_no_update BEFORE UPDATE ON enrichment_candidate_abstract BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_abstract_no_delete BEFORE DELETE ON enrichment_candidate_abstract BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_retrieval_no_update BEFORE UPDATE ON enrichment_candidate_retrieval BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_retrieval_no_delete BEFORE DELETE ON enrichment_candidate_retrieval BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_access_no_update BEFORE UPDATE ON enrichment_candidate_access BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_candidate_access_no_delete BEFORE DELETE ON enrichment_candidate_access BEGIN SELECT RAISE(ABORT,'append_only'); END;
