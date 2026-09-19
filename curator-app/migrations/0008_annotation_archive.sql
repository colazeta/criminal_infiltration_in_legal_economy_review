-- Original ingress captures and unreviewed annotations; no scientific acceptance.

CREATE TABLE enrichment_ingress_snapshots (
 snapshot_id TEXT NOT NULL PRIMARY KEY,
 source_kind TEXT NOT NULL CHECK(source_kind IN ('github_issue','github_comment')),
 external_id TEXT NOT NULL, source_url TEXT NOT NULL, source_created_at TEXT NOT NULL,
 source_updated_at TEXT NOT NULL, content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64),
 storage_key TEXT NOT NULL UNIQUE, observed_at TEXT NOT NULL,
 UNIQUE(source_kind,external_id,content_sha256)
);

CREATE TABLE enrichment_manual_annotations (
 annotation_id TEXT NOT NULL PRIMARY KEY,
 snapshot_id TEXT NOT NULL UNIQUE REFERENCES enrichment_ingress_snapshots(snapshot_id),
 issue_snapshot_id TEXT NOT NULL REFERENCES enrichment_ingress_snapshots(snapshot_id),
 target_id TEXT REFERENCES enrichment_targets(target_id), candidate_marker TEXT,
 binding_state TEXT NOT NULL CHECK(binding_state IN ('candidate_bound','unresolved','conflict','unregistered')),
 review_state TEXT NOT NULL CHECK(review_state='unreviewed_manual_support'),
 authorised_display INTEGER NOT NULL CHECK(authorised_display IN (0,1)),
 unparsed_lines INTEGER NOT NULL CHECK(unparsed_lines>=0), imported_at TEXT NOT NULL,
 CHECK((binding_state='candidate_bound')=(target_id IS NOT NULL))
);

CREATE TABLE enrichment_annotation_sections (
 section_id TEXT NOT NULL PRIMARY KEY,
 annotation_id TEXT NOT NULL REFERENCES enrichment_manual_annotations(annotation_id),
 scope TEXT NOT NULL CHECK(scope IN ('overview','framework','studies','datasets','methods','variables','findings','sources')),
 group_label TEXT NOT NULL, position INTEGER NOT NULL CHECK(position>0),
 UNIQUE(annotation_id,position)
);

CREATE TABLE enrichment_annotation_fields (
 field_id TEXT NOT NULL PRIMARY KEY,
 section_id TEXT NOT NULL REFERENCES enrichment_annotation_sections(section_id),
 field_name TEXT NOT NULL, value TEXT NOT NULL CHECK(length(value)>0 AND length(value)<=12000),
 position INTEGER NOT NULL CHECK(position>0), UNIQUE(section_id,position),
 CHECK(field_name IN ('alternative','alternative_rationale','analysis_unit','annotation_text','authors_limitations','comparison','contribution','design','findings','geography','identification','infiltration_definition','infiltration_operationalisation','method','observation_unit','period','population','primary','rationale','research_question','robustness','sample_size','sampling','secondary','secondary_rationale','source_url','status','study_type','summary','validation'))
);

CREATE TABLE enrichment_annotation_classes (
 assertion_id TEXT NOT NULL PRIMARY KEY,
 annotation_id TEXT NOT NULL REFERENCES enrichment_manual_annotations(annotation_id),
 field_id TEXT NOT NULL REFERENCES enrichment_annotation_fields(field_id),
 category TEXT NOT NULL CHECK(category IN ('aetiology','diagnosis','screening','therapy','prognosis','prevention')),
 role TEXT NOT NULL CHECK(role IN ('primary','secondary','alternative')),
 UNIQUE(field_id,category,role)
);

CREATE TABLE enrichment_annotation_heads (
 external_id TEXT NOT NULL PRIMARY KEY,
 annotation_id TEXT NOT NULL REFERENCES enrichment_manual_annotations(annotation_id),
 state TEXT NOT NULL CHECK(state IN ('current','withdrawn','conflict')),
 record_version INTEGER NOT NULL CHECK(record_version>0), updated_at TEXT NOT NULL
);

CREATE TABLE enrichment_annotation_events (
 event_id TEXT NOT NULL PRIMARY KEY,
 external_id TEXT NOT NULL, annotation_id TEXT NOT NULL REFERENCES enrichment_manual_annotations(annotation_id),
 previous_annotation_id TEXT REFERENCES enrichment_manual_annotations(annotation_id),
 event_kind TEXT NOT NULL CHECK(event_kind IN ('import','revision','older_revision','conflict','withdrawal','retained_after_withdrawal')),
 observed_at TEXT NOT NULL
);

CREATE TABLE enrichment_annotation_receipts (
 receipt_id TEXT NOT NULL PRIMARY KEY,
 annotation_id TEXT NOT NULL UNIQUE REFERENCES enrichment_manual_annotations(annotation_id),
 transformation_version TEXT NOT NULL CHECK(transformation_version='CILE-ANNOTATION-ARCHIVE-1'),
 source_sha256 TEXT NOT NULL CHECK(length(source_sha256)=64),
 parsed_sha256 TEXT NOT NULL CHECK(length(parsed_sha256)=64),
 rebuilt_sha256 TEXT NOT NULL CHECK(rebuilt_sha256=parsed_sha256),
 verified_at TEXT NOT NULL
);

CREATE INDEX enrichment_annotation_target ON enrichment_manual_annotations(target_id);

CREATE TRIGGER enrichment_annotation_head_identity BEFORE UPDATE ON enrichment_annotation_heads WHEN NEW.external_id<>OLD.external_id OR NEW.record_version<>OLD.record_version+1 BEGIN SELECT RAISE(ABORT,'annotation_head_concurrency'); END;

CREATE TRIGGER enrichment_annotation_no_republish BEFORE UPDATE ON enrichment_annotation_heads WHEN OLD.state='withdrawn' AND NEW.state<>'withdrawn' BEGIN SELECT RAISE(ABORT,'annotation_withdrawal_requires_human_restore'); END;

CREATE TRIGGER enrichment_annotation_field_scope BEFORE INSERT ON enrichment_annotation_fields WHEN NOT EXISTS(SELECT 1 FROM enrichment_annotation_sections s WHERE s.section_id=NEW.section_id AND ((s.scope='overview' AND NEW.field_name IN ('summary','contribution','research_question','infiltration_definition','infiltration_operationalisation','authors_limitations')) OR (s.scope='framework' AND NEW.field_name IN ('status','primary','secondary','alternative','rationale','secondary_rationale','alternative_rationale')) OR (s.scope='studies' AND NEW.field_name IN ('study_type','research_question','population','sampling','sample_size','observation_unit','analysis_unit','geography','period')) OR (s.scope='methods' AND NEW.field_name IN ('design','method','comparison','identification','validation','robustness','findings')) OR (s.scope='datasets' AND NEW.field_name IN ('annotation_text')) OR (s.scope='variables' AND NEW.field_name IN ('annotation_text')) OR (s.scope='findings' AND NEW.field_name IN ('annotation_text')) OR (s.scope='sources' AND NEW.field_name IN ('source_url')))) BEGIN SELECT RAISE(ABORT,'annotation_field_scope'); END;

CREATE TRIGGER enrichment_annotation_class_scope BEFORE INSERT ON enrichment_annotation_classes WHEN NOT EXISTS(SELECT 1 FROM enrichment_annotation_fields f JOIN enrichment_annotation_sections s USING(section_id) WHERE f.field_id=NEW.field_id AND s.annotation_id=NEW.annotation_id AND s.scope='framework' AND f.field_name=NEW.role) BEGIN SELECT RAISE(ABORT,'annotation_class_scope'); END;

CREATE TRIGGER enrichment_ingress_snapshots_no_update BEFORE UPDATE ON enrichment_ingress_snapshots BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_ingress_snapshots_no_delete BEFORE DELETE ON enrichment_ingress_snapshots BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_manual_annotations_no_update BEFORE UPDATE ON enrichment_manual_annotations BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_manual_annotations_no_delete BEFORE DELETE ON enrichment_manual_annotations BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_annotation_sections_no_update BEFORE UPDATE ON enrichment_annotation_sections BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_annotation_sections_no_delete BEFORE DELETE ON enrichment_annotation_sections BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_annotation_fields_no_update BEFORE UPDATE ON enrichment_annotation_fields BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_annotation_fields_no_delete BEFORE DELETE ON enrichment_annotation_fields BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_annotation_classes_no_update BEFORE UPDATE ON enrichment_annotation_classes BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_annotation_classes_no_delete BEFORE DELETE ON enrichment_annotation_classes BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_annotation_heads_no_delete BEFORE DELETE ON enrichment_annotation_heads BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_annotation_events_no_update BEFORE UPDATE ON enrichment_annotation_events BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_annotation_events_no_delete BEFORE DELETE ON enrichment_annotation_events BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_annotation_receipts_no_update BEFORE UPDATE ON enrichment_annotation_receipts BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_annotation_receipts_no_delete BEFORE DELETE ON enrichment_annotation_receipts BEGIN SELECT RAISE(ABORT,'append_only'); END;
