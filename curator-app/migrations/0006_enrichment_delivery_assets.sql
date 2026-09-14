-- CILE-DELIVERY-ASSETS-1. Additive immutable document and bibliography records.
-- Same private enrichment namespace; no scientific approval or new candidates.
CREATE TABLE enrichment_documents (
 document_id TEXT PRIMARY KEY,
 target_id TEXT NOT NULL REFERENCES enrichment_targets(target_id),
 input_sha256 TEXT NOT NULL,
 source_id TEXT NOT NULL REFERENCES enrichment_sources(source_id),
 source_url TEXT NOT NULL,
 pdf_sha256 TEXT NOT NULL CHECK(length(pdf_sha256)=64),
 source_text_sha256 TEXT NOT NULL CHECK(length(source_text_sha256)=64),
 byte_length INTEGER NOT NULL CHECK(byte_length>0 AND byte_length<=4194304),
 storage_key TEXT NOT NULL,
 version_label TEXT NOT NULL,
 retention_basis TEXT NOT NULL,
 licence_status TEXT NOT NULL,
 licence_url TEXT,
 attribution TEXT NOT NULL,
 visibility TEXT NOT NULL CHECK(visibility IN ('private','public')),
 rights_verified INTEGER NOT NULL CHECK(rights_verified IN (0,1)),
 observed_at TEXT NOT NULL
);
CREATE INDEX enrichment_documents_target ON enrichment_documents(target_id,input_sha256,observed_at);
CREATE TRIGGER enrichment_documents_no_update BEFORE UPDATE ON enrichment_documents BEGIN SELECT RAISE(ABORT,'immutable document'); END;
CREATE TRIGGER enrichment_documents_no_delete BEFORE DELETE ON enrichment_documents BEGIN SELECT RAISE(ABORT,'immutable document'); END;
CREATE TABLE enrichment_bibliography_snapshots (
 bibliography_id TEXT PRIMARY KEY,
 target_id TEXT NOT NULL REFERENCES enrichment_targets(target_id),
 input_sha256 TEXT NOT NULL,
 source_id TEXT NOT NULL REFERENCES enrichment_sources(source_id),
 scope TEXT NOT NULL CHECK(scope IN ('paper_bibliography','provider_references')),
 coverage TEXT NOT NULL CHECK(coverage IN ('partial','source_complete','not_reported')),
 declared_count INTEGER,
 entries_count INTEGER NOT NULL CHECK(entries_count>=0),
 payload_json TEXT NOT NULL,
 payload_sha256 TEXT NOT NULL CHECK(length(payload_sha256)=64),
 observed_at TEXT NOT NULL
);
CREATE INDEX enrichment_bibliography_target ON enrichment_bibliography_snapshots(target_id,input_sha256,observed_at);
CREATE TRIGGER enrichment_bibliography_snapshots_no_update BEFORE UPDATE ON enrichment_bibliography_snapshots BEGIN SELECT RAISE(ABORT,'immutable bibliography'); END;
CREATE TRIGGER enrichment_bibliography_snapshots_no_delete BEFORE DELETE ON enrichment_bibliography_snapshots BEGIN SELECT RAISE(ABORT,'immutable bibliography'); END;
