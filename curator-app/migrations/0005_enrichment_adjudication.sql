-- CILE-ENRICH-ADJUDICATION-1: additive immutable scientific calibration/adjudication receipts.
-- This migration adds no candidate, proposal, source, classification or automatic approval.
CREATE TABLE enrichment_calibration_receipts (
 calibration_id TEXT PRIMARY KEY,
 protocol_version TEXT NOT NULL,
 codebook_version TEXT NOT NULL,
 model TEXT NOT NULL,
 prompt_sha256 TEXT NOT NULL CHECK(length(prompt_sha256)=64),
 benchmark_sha256 TEXT NOT NULL CHECK(length(benchmark_sha256)=64),
 metrics_sha256 TEXT NOT NULL CHECK(length(metrics_sha256)=64),
 benchmark_size INTEGER NOT NULL CHECK(benchmark_size BETWEEN 12 AND 18),
 reference_checked_cases INTEGER NOT NULL CHECK(reference_checked_cases=benchmark_size),
 full_text_cases INTEGER NOT NULL CHECK(full_text_cases BETWEEN 1 AND benchmark_size),
 hard_cases INTEGER NOT NULL CHECK(hard_cases BETWEEN 1 AND benchmark_size),
 manifest_sha256 TEXT NOT NULL CHECK(length(manifest_sha256)=64),
 repository TEXT NOT NULL,
 pr_number INTEGER NOT NULL CHECK(pr_number>0),
 reviewed_commit TEXT NOT NULL CHECK(length(reviewed_commit)=40),
 human_login TEXT NOT NULL,
 human_review_id TEXT NOT NULL,
 approved_at TEXT NOT NULL,
 imported_at TEXT NOT NULL
);
CREATE TABLE enrichment_adjudication_receipts (
 receipt_id TEXT PRIMARY KEY,
 target_id TEXT NOT NULL REFERENCES enrichment_targets(target_id),
 input_sha256 TEXT NOT NULL CHECK(length(input_sha256)=64),
 proposal_id TEXT NOT NULL REFERENCES enrichment_proposals(proposal_id),
 proposal_sha256 TEXT NOT NULL CHECK(length(proposal_sha256)=64),
 source_snapshot_sha256 TEXT NOT NULL CHECK(length(source_snapshot_sha256)=64),
 reference_snapshot_sha256 TEXT NOT NULL CHECK(length(reference_snapshot_sha256)=64),
 calibration_id TEXT NOT NULL REFERENCES enrichment_calibration_receipts(calibration_id),
 checklist_sha256 TEXT NOT NULL CHECK(length(checklist_sha256)=64),
 manifest_sha256 TEXT NOT NULL CHECK(length(manifest_sha256)=64),
 repository TEXT NOT NULL,
 pr_number INTEGER NOT NULL CHECK(pr_number>0),
 reviewed_commit TEXT NOT NULL CHECK(length(reviewed_commit)=40),
 human_login TEXT NOT NULL,
 human_review_id TEXT NOT NULL,
 approved_at TEXT NOT NULL,
 imported_at TEXT NOT NULL,
 UNIQUE(target_id,input_sha256,proposal_id)
);
CREATE TRIGGER enrichment_calibration_receipts_no_update BEFORE UPDATE ON enrichment_calibration_receipts BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_calibration_receipts_no_delete BEFORE DELETE ON enrichment_calibration_receipts BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_adjudication_receipts_no_update BEFORE UPDATE ON enrichment_adjudication_receipts BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER enrichment_adjudication_receipts_no_delete BEFORE DELETE ON enrichment_adjudication_receipts BEGIN SELECT RAISE(ABORT,'append_only'); END;
