-- CILE-DOCUMENT-REPOSITORY-1. No Work or scientific decision is created.
CREATE TABLE enrichment_manifestations (
 manifestation_id TEXT NOT NULL PRIMARY KEY,
 target_id TEXT NOT NULL REFERENCES enrichment_targets(target_id),
 input_sha256 TEXT NOT NULL,
 source_url TEXT NOT NULL,
 version_label TEXT NOT NULL,
 UNIQUE(target_id,input_sha256,source_url,version_label)
);
CREATE TABLE enrichment_document_bindings (
 document_id TEXT NOT NULL PRIMARY KEY REFERENCES enrichment_documents(document_id),
 manifestation_id TEXT NOT NULL REFERENCES enrichment_manifestations(manifestation_id)
);
CREATE TRIGGER enrichment_document_binding_scope BEFORE INSERT ON enrichment_document_bindings
WHEN NOT EXISTS (
 SELECT 1 FROM enrichment_documents d JOIN enrichment_manifestations m
 ON d.target_id=m.target_id AND d.input_sha256=m.input_sha256
 AND d.source_url=m.source_url AND d.version_label=m.version_label
 WHERE d.document_id=NEW.document_id AND m.manifestation_id=NEW.manifestation_id
) BEGIN SELECT RAISE(ABORT,'document manifestation scope'); END;
CREATE TABLE enrichment_document_extractions (
 extraction_id TEXT NOT NULL PRIMARY KEY,
 document_id TEXT NOT NULL REFERENCES enrichment_documents(document_id),
 source_id TEXT NOT NULL REFERENCES enrichment_sources(source_id),
 text_sha256 TEXT NOT NULL CHECK(length(text_sha256)=64),
 text_length INTEGER NOT NULL CHECK(text_length>0 AND text_length<=4000000),
 page_count INTEGER NOT NULL CHECK(page_count BETWEEN 1 AND 500),
 method TEXT NOT NULL CHECK(method IN ('native','ocr')),
 extractor_version TEXT NOT NULL,
 offset_unit TEXT NOT NULL CHECK(offset_unit='utf16'),
 protocol_version TEXT NOT NULL CHECK(protocol_version='CILE-DOCUMENT-TEXT-1'),
 observed_at TEXT NOT NULL,
 UNIQUE(document_id,protocol_version)
);
CREATE TRIGGER enrichment_document_extraction_scope BEFORE INSERT ON enrichment_document_extractions
WHEN NOT EXISTS (
 SELECT 1 FROM enrichment_documents d JOIN enrichment_sources s ON s.source_id=d.source_id
 WHERE d.document_id=NEW.document_id AND s.source_id=NEW.source_id
 AND s.content_sha256=NEW.text_sha256 AND d.source_text_sha256=NEW.text_sha256
 AND s.target_id=d.target_id AND s.input_sha256=d.input_sha256 AND s.evidence_kind='full_text'
) BEGIN SELECT RAISE(ABORT,'document extraction scope'); END;
CREATE TABLE enrichment_document_pages (
 extraction_id TEXT NOT NULL REFERENCES enrichment_document_extractions(extraction_id),
 page_number INTEGER NOT NULL CHECK(page_number>0),
 start_offset INTEGER NOT NULL CHECK(start_offset>=0),
 end_offset INTEGER NOT NULL CHECK(end_offset>=start_offset),
 PRIMARY KEY(extraction_id,page_number)
);
CREATE TABLE enrichment_document_chunks (
 chunk_id TEXT NOT NULL PRIMARY KEY,
 extraction_id TEXT NOT NULL,
 page_number INTEGER NOT NULL,
 start_offset INTEGER NOT NULL CHECK(start_offset>=0),
 end_offset INTEGER NOT NULL CHECK(end_offset>start_offset AND end_offset-start_offset<=1800),
 text_sha256 TEXT NOT NULL CHECK(length(text_sha256)=64),
 FOREIGN KEY(extraction_id,page_number) REFERENCES enrichment_document_pages(extraction_id,page_number),
 UNIQUE(extraction_id,page_number,start_offset)
);
CREATE TRIGGER enrichment_document_chunk_scope BEFORE INSERT ON enrichment_document_chunks
WHEN NOT EXISTS (SELECT 1 FROM enrichment_document_pages p WHERE p.extraction_id=NEW.extraction_id
 AND p.page_number=NEW.page_number AND NEW.start_offset>=p.start_offset AND NEW.end_offset<=p.end_offset)
BEGIN SELECT RAISE(ABORT,'chunk outside page'); END;
-- An inverted lexical index; no copied full text and no virtual-table shadow state.
CREATE TABLE enrichment_document_terms (
 term TEXT NOT NULL CHECK(length(term) BETWEEN 2 AND 64),
 chunk_id TEXT NOT NULL REFERENCES enrichment_document_chunks(chunk_id),
 occurrences INTEGER NOT NULL CHECK(occurrences>0),
 PRIMARY KEY(term,chunk_id)
);
CREATE INDEX enrichment_document_terms_chunk ON enrichment_document_terms(chunk_id);
CREATE INDEX enrichment_document_extractions_source ON enrichment_document_extractions(source_id);
CREATE INDEX enrichment_document_bindings_manifestation ON enrichment_document_bindings(manifestation_id);
CREATE INDEX enrichment_documents_content ON enrichment_documents(pdf_sha256,target_id,input_sha256,observed_at);
CREATE INDEX enrichment_targets_doi ON enrichment_targets(json_extract(record_json,'$.doi'));
CREATE INDEX enrichment_facts_filter ON enrichment_facts(scope,field_name,status,proposal_id);
-- Disposable bibliographic search projection from the existing register sync;
-- never changes input identity or the source text/proposal version it belongs to.
CREATE TABLE enrichment_catalogue_index (
 target_id TEXT NOT NULL PRIMARY KEY REFERENCES enrichment_targets(target_id),
 input_sha256 TEXT NOT NULL,
 authors TEXT,
 publication_year INTEGER,
 venue TEXT,
 review_status TEXT,
 projection_sha256 TEXT NOT NULL,
 observed_at TEXT NOT NULL
);
CREATE INDEX enrichment_catalogue_authors ON enrichment_catalogue_index(authors);
CREATE INDEX enrichment_catalogue_year ON enrichment_catalogue_index(publication_year);
CREATE TRIGGER enrichment_manifestations_no_update BEFORE UPDATE ON enrichment_manifestations BEGIN SELECT RAISE(ABORT,'immutable document provenance'); END;
CREATE TRIGGER enrichment_manifestations_no_delete BEFORE DELETE ON enrichment_manifestations BEGIN SELECT RAISE(ABORT,'immutable document provenance'); END;
CREATE TRIGGER enrichment_document_bindings_no_update BEFORE UPDATE ON enrichment_document_bindings BEGIN SELECT RAISE(ABORT,'immutable document provenance'); END;
CREATE TRIGGER enrichment_document_bindings_no_delete BEFORE DELETE ON enrichment_document_bindings BEGIN SELECT RAISE(ABORT,'immutable document provenance'); END;
CREATE TRIGGER enrichment_document_extractions_no_update BEFORE UPDATE ON enrichment_document_extractions BEGIN SELECT RAISE(ABORT,'immutable document provenance'); END;
CREATE TRIGGER enrichment_document_extractions_no_delete BEFORE DELETE ON enrichment_document_extractions BEGIN SELECT RAISE(ABORT,'immutable document provenance'); END;
CREATE TRIGGER enrichment_document_pages_no_update BEFORE UPDATE ON enrichment_document_pages BEGIN SELECT RAISE(ABORT,'immutable document provenance'); END;
CREATE TRIGGER enrichment_document_pages_no_delete BEFORE DELETE ON enrichment_document_pages BEGIN SELECT RAISE(ABORT,'immutable document provenance'); END;
CREATE TRIGGER enrichment_document_chunks_no_update BEFORE UPDATE ON enrichment_document_chunks BEGIN SELECT RAISE(ABORT,'immutable document provenance'); END;
CREATE TRIGGER enrichment_document_chunks_no_delete BEFORE DELETE ON enrichment_document_chunks BEGIN SELECT RAISE(ABORT,'immutable document provenance'); END;
CREATE TRIGGER enrichment_document_terms_no_update BEFORE UPDATE ON enrichment_document_terms BEGIN SELECT RAISE(ABORT,'immutable document provenance'); END;
CREATE TRIGGER enrichment_document_terms_no_delete BEFORE DELETE ON enrichment_document_terms BEGIN SELECT RAISE(ABORT,'immutable document provenance'); END;
