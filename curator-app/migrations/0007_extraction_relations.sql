-- CILE-EXTRACTION-RELATIONS-1. Additive; original submissions remain immutable history.

CREATE TABLE enrichment_proposal_details (
 proposal_id TEXT NOT NULL PRIMARY KEY REFERENCES enrichment_proposals(proposal_id),
 source_coverage TEXT NOT NULL CHECK(source_coverage IN ('abstract_only','partial_text','full_text')),
 agent TEXT NOT NULL, model TEXT, prompt_sha256 TEXT CHECK(prompt_sha256 IS NULL OR length(prompt_sha256)=64)
);

CREATE TABLE enrichment_proposal_sources (
 proposal_id TEXT NOT NULL REFERENCES enrichment_proposals(proposal_id), source_id TEXT NOT NULL REFERENCES enrichment_sources(source_id),
 position INTEGER NOT NULL CHECK(typeof(position)='integer' AND position>0), PRIMARY KEY(proposal_id,source_id), UNIQUE(proposal_id,position)
);

CREATE TRIGGER enrichment_proposal_sources_scope BEFORE INSERT ON enrichment_proposal_sources
 WHEN NOT EXISTS(SELECT 1 FROM enrichment_proposals p JOIN enrichment_sources s ON s.target_id=p.target_id AND s.input_sha256=p.input_sha256 WHERE p.proposal_id=NEW.proposal_id AND s.source_id=NEW.source_id AND s.evidence_kind<>'metadata')
 BEGIN SELECT RAISE(ABORT,'source_scope_mismatch'); END;

CREATE TABLE enrichment_spans (
 proposal_id TEXT NOT NULL, span_id TEXT NOT NULL, source_id TEXT NOT NULL,
 position INTEGER NOT NULL CHECK(typeof(position)='integer' AND position>0), start_offset INTEGER NOT NULL CHECK(typeof(start_offset)='integer' AND start_offset>=0),
 end_offset INTEGER NOT NULL CHECK(typeof(end_offset)='integer' AND end_offset>start_offset), locator TEXT NOT NULL,
 PRIMARY KEY(proposal_id,span_id), UNIQUE(proposal_id,position),
 FOREIGN KEY(proposal_id,source_id) REFERENCES enrichment_proposal_sources(proposal_id,source_id)
);

CREATE TABLE enrichment_studies_order (
 proposal_id TEXT NOT NULL, study_id TEXT NOT NULL, position INTEGER NOT NULL CHECK(typeof(position)='integer' AND position>0),
 PRIMARY KEY(proposal_id,study_id), UNIQUE(proposal_id,position),
 FOREIGN KEY(proposal_id,study_id) REFERENCES enrichment_studies(proposal_id,study_id)
);

CREATE TABLE enrichment_datasets_order (
 proposal_id TEXT NOT NULL, dataset_id TEXT NOT NULL, position INTEGER NOT NULL CHECK(typeof(position)='integer' AND position>0),
 PRIMARY KEY(proposal_id,dataset_id), UNIQUE(proposal_id,position),
 FOREIGN KEY(proposal_id,dataset_id) REFERENCES enrichment_datasets(proposal_id,dataset_id)
);

CREATE TABLE enrichment_analyses_order (
 proposal_id TEXT NOT NULL, analysis_id TEXT NOT NULL, position INTEGER NOT NULL CHECK(typeof(position)='integer' AND position>0),
 PRIMARY KEY(proposal_id,analysis_id), UNIQUE(proposal_id,position),
 FOREIGN KEY(proposal_id,analysis_id) REFERENCES enrichment_analyses(proposal_id,analysis_id)
);

CREATE TABLE enrichment_variable_uses_order (
 proposal_id TEXT NOT NULL, variable_use_id TEXT NOT NULL, position INTEGER NOT NULL CHECK(typeof(position)='integer' AND position>0),
 PRIMARY KEY(proposal_id,variable_use_id), UNIQUE(proposal_id,position),
 FOREIGN KEY(proposal_id,variable_use_id) REFERENCES enrichment_variable_uses(proposal_id,variable_use_id)
);

CREATE TABLE enrichment_findings_order (
 proposal_id TEXT NOT NULL, finding_id TEXT NOT NULL, position INTEGER NOT NULL CHECK(typeof(position)='integer' AND position>0),
 PRIMARY KEY(proposal_id,finding_id), UNIQUE(proposal_id,position),
 FOREIGN KEY(proposal_id,finding_id) REFERENCES enrichment_findings(proposal_id,finding_id)
);

CREATE TABLE enrichment_analysis_datasets (
 proposal_id TEXT NOT NULL, analysis_id TEXT NOT NULL, dataset_id TEXT NOT NULL, position INTEGER NOT NULL CHECK(typeof(position)='integer' AND position>0),
 PRIMARY KEY(proposal_id,analysis_id,dataset_id), UNIQUE(proposal_id,analysis_id,position),
 FOREIGN KEY(proposal_id,analysis_id) REFERENCES enrichment_analyses(proposal_id,analysis_id),
 FOREIGN KEY(proposal_id,dataset_id) REFERENCES enrichment_datasets(proposal_id,dataset_id)
);

CREATE TABLE enrichment_variable_datasets (
 proposal_id TEXT NOT NULL, variable_use_id TEXT NOT NULL, dataset_id TEXT NOT NULL, position INTEGER NOT NULL CHECK(typeof(position)='integer' AND position>0),
 PRIMARY KEY(proposal_id,variable_use_id,dataset_id), UNIQUE(proposal_id,variable_use_id,position),
 FOREIGN KEY(proposal_id,variable_use_id) REFERENCES enrichment_variable_uses(proposal_id,variable_use_id),
 FOREIGN KEY(proposal_id,dataset_id) REFERENCES enrichment_datasets(proposal_id,dataset_id)
);

CREATE TABLE enrichment_finding_variables (
 proposal_id TEXT NOT NULL, finding_id TEXT NOT NULL, variable_use_id TEXT NOT NULL, position INTEGER NOT NULL CHECK(typeof(position)='integer' AND position>0),
 PRIMARY KEY(proposal_id,finding_id,variable_use_id), UNIQUE(proposal_id,finding_id,position),
 FOREIGN KEY(proposal_id,finding_id) REFERENCES enrichment_findings(proposal_id,finding_id),
 FOREIGN KEY(proposal_id,variable_use_id) REFERENCES enrichment_variable_uses(proposal_id,variable_use_id)
);

CREATE TRIGGER enrichment_analysis_datasets_scope BEFORE INSERT ON enrichment_analysis_datasets
 WHEN NOT EXISTS(SELECT 1 FROM enrichment_analyses a JOIN enrichment_datasets d ON d.proposal_id=a.proposal_id AND d.study_id=a.study_id WHERE a.proposal_id=NEW.proposal_id AND a.analysis_id=NEW.analysis_id AND d.dataset_id=NEW.dataset_id)
 BEGIN SELECT RAISE(ABORT,'cross_study_dataset'); END;
CREATE TRIGGER enrichment_variable_datasets_scope BEFORE INSERT ON enrichment_variable_datasets
 WHEN NOT EXISTS(SELECT 1 FROM enrichment_variable_uses v JOIN enrichment_analysis_datasets a ON a.proposal_id=v.proposal_id AND a.analysis_id=v.analysis_id WHERE v.proposal_id=NEW.proposal_id AND v.variable_use_id=NEW.variable_use_id AND a.dataset_id=NEW.dataset_id)
 BEGIN SELECT RAISE(ABORT,'variable_dataset_scope'); END;
CREATE TRIGGER enrichment_finding_variables_scope BEFORE INSERT ON enrichment_finding_variables
 WHEN NOT EXISTS(SELECT 1 FROM enrichment_findings f JOIN enrichment_variable_uses v ON v.proposal_id=f.proposal_id AND v.analysis_id=f.analysis_id WHERE f.proposal_id=NEW.proposal_id AND f.finding_id=NEW.finding_id AND v.variable_use_id=NEW.variable_use_id)
 BEGIN SELECT RAISE(ABORT,'finding_variable_scope'); END;

CREATE TABLE enrichment_secondary_classes (
 proposal_id TEXT NOT NULL REFERENCES enrichment_proposals(proposal_id), category TEXT NOT NULL CHECK(category IN ('aetiology','diagnosis','screening','therapy','prognosis','prevention')),
 position INTEGER NOT NULL CHECK(typeof(position)='integer' AND position>0), PRIMARY KEY(proposal_id,category), UNIQUE(proposal_id,position)
);

CREATE TABLE enrichment_framework_alternatives (
 proposal_id TEXT NOT NULL PRIMARY KEY REFERENCES enrichment_proposals(proposal_id), category TEXT CHECK(category IS NULL OR category IN ('aetiology','diagnosis','screening','therapy','prognosis','prevention'))
);

CREATE TABLE enrichment_facts (
 fact_id TEXT NOT NULL PRIMARY KEY, proposal_id TEXT NOT NULL REFERENCES enrichment_proposals(proposal_id),
 scope TEXT NOT NULL, field_name TEXT NOT NULL, study_id TEXT, dataset_id TEXT, analysis_id TEXT, variable_use_id TEXT, finding_id TEXT, secondary_category TEXT,
 status TEXT NOT NULL CHECK(status IN ('reported','not_reported','not_verifiable','not_applicable','ambiguous')),
 value TEXT, origin TEXT NOT NULL CHECK(origin IN ('source','analyst')),
 UNIQUE(fact_id,proposal_id), CHECK(value IS NULL OR length(value)<=6000),
 CHECK(status NOT IN ('reported','ambiguous') OR (value IS NOT NULL AND length(value)>0)), CHECK(status NOT IN ('not_reported','not_verifiable','not_applicable') OR value IS NULL),
 CHECK((scope='overview' AND field_name IN ('summary','contribution','research_question','infiltration_definition','infiltration_operationalisation','authors_limitations','analyst_limitations') AND study_id IS NULL AND dataset_id IS NULL AND analysis_id IS NULL AND variable_use_id IS NULL AND finding_id IS NULL AND secondary_category IS NULL) OR (scope='studies' AND field_name IN ('study_type','research_question','population','sampling','sample_size','observation_unit','analysis_unit','geography','period') AND study_id IS NOT NULL AND dataset_id IS NULL AND analysis_id IS NULL AND variable_use_id IS NULL AND finding_id IS NULL AND secondary_category IS NULL) OR (scope='datasets' AND field_name IN ('name','provider','accessibility','selection','coverage','limitations') AND study_id IS NULL AND dataset_id IS NOT NULL AND analysis_id IS NULL AND variable_use_id IS NULL AND finding_id IS NULL AND secondary_category IS NULL) OR (scope='analyses' AND field_name IN ('design','method','comparison','identification','validation','robustness') AND study_id IS NULL AND dataset_id IS NULL AND analysis_id IS NOT NULL AND variable_use_id IS NULL AND finding_id IS NULL AND secondary_category IS NULL) OR (scope='variable_uses' AND field_name IN ('original_name','concept','operationalisation','unit','period','transformation','role') AND study_id IS NULL AND dataset_id IS NULL AND analysis_id IS NULL AND variable_use_id IS NOT NULL AND finding_id IS NULL AND secondary_category IS NULL) OR (scope='findings' AND field_name IN ('statement','finding_type','direction','estimate','unit','uncertainty','reference_comparison','population_scope','temporal_scope','caveat') AND study_id IS NULL AND dataset_id IS NULL AND analysis_id IS NULL AND variable_use_id IS NULL AND finding_id IS NOT NULL AND secondary_category IS NULL) OR (scope='framework' AND field_name IN ('rationale') AND study_id IS NULL AND dataset_id IS NULL AND analysis_id IS NULL AND variable_use_id IS NULL AND finding_id IS NULL AND secondary_category IS NULL) OR (scope='secondary' AND field_name IN ('rationale') AND study_id IS NULL AND dataset_id IS NULL AND analysis_id IS NULL AND variable_use_id IS NULL AND finding_id IS NULL AND secondary_category IS NOT NULL)),
 FOREIGN KEY(proposal_id,study_id) REFERENCES enrichment_studies(proposal_id,study_id),
 FOREIGN KEY(proposal_id,dataset_id) REFERENCES enrichment_datasets(proposal_id,dataset_id),
 FOREIGN KEY(proposal_id,analysis_id) REFERENCES enrichment_analyses(proposal_id,analysis_id),
 FOREIGN KEY(proposal_id,variable_use_id) REFERENCES enrichment_variable_uses(proposal_id,variable_use_id),
 FOREIGN KEY(proposal_id,finding_id) REFERENCES enrichment_findings(proposal_id,finding_id),
 FOREIGN KEY(proposal_id,secondary_category) REFERENCES enrichment_secondary_classes(proposal_id,category)
);

CREATE UNIQUE INDEX enrichment_fact_overview ON enrichment_facts(proposal_id,field_name) WHERE scope='overview';

CREATE UNIQUE INDEX enrichment_fact_studies ON enrichment_facts(proposal_id,study_id,field_name) WHERE scope='studies';

CREATE UNIQUE INDEX enrichment_fact_datasets ON enrichment_facts(proposal_id,dataset_id,field_name) WHERE scope='datasets';

CREATE UNIQUE INDEX enrichment_fact_analyses ON enrichment_facts(proposal_id,analysis_id,field_name) WHERE scope='analyses';

CREATE UNIQUE INDEX enrichment_fact_variable_uses ON enrichment_facts(proposal_id,variable_use_id,field_name) WHERE scope='variable_uses';

CREATE UNIQUE INDEX enrichment_fact_findings ON enrichment_facts(proposal_id,finding_id,field_name) WHERE scope='findings';

CREATE UNIQUE INDEX enrichment_fact_framework ON enrichment_facts(proposal_id,field_name) WHERE scope='framework';

CREATE UNIQUE INDEX enrichment_fact_secondary ON enrichment_facts(proposal_id,secondary_category,field_name) WHERE scope='secondary';

CREATE TABLE enrichment_fact_evidence (
 fact_id TEXT NOT NULL, proposal_id TEXT NOT NULL, span_id TEXT NOT NULL, position INTEGER NOT NULL CHECK(typeof(position)='integer' AND position>0),
 PRIMARY KEY(fact_id,span_id), UNIQUE(fact_id,position),
 FOREIGN KEY(fact_id,proposal_id) REFERENCES enrichment_facts(fact_id,proposal_id),
 FOREIGN KEY(proposal_id,span_id) REFERENCES enrichment_spans(proposal_id,span_id)
);

CREATE TABLE enrichment_normalization_receipts (
 receipt_id TEXT NOT NULL PRIMARY KEY, proposal_id TEXT NOT NULL UNIQUE REFERENCES enrichment_proposals(proposal_id),
 transformation_version TEXT NOT NULL CHECK(transformation_version='CILE-EXTRACTION-RELATIONS-1'),
 source_sha256 TEXT NOT NULL CHECK(length(source_sha256)=64), rebuilt_sha256 TEXT NOT NULL CHECK(rebuilt_sha256=source_sha256),
 write_kind TEXT NOT NULL CHECK(write_kind IN ('native','backfill')), verified_at TEXT NOT NULL
);

CREATE TRIGGER enrichment_normalization_evidence_required BEFORE INSERT ON enrichment_normalization_receipts
 WHEN EXISTS(SELECT 1 FROM enrichment_facts f WHERE f.proposal_id=NEW.proposal_id AND f.status='reported' AND NOT EXISTS(SELECT 1 FROM enrichment_fact_evidence e WHERE e.fact_id=f.fact_id))
 BEGIN SELECT RAISE(ABORT,'reported_fact_requires_evidence'); END;

CREATE TRIGGER enrichment_proposal_details_no_update BEFORE UPDATE ON enrichment_proposal_details BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_proposal_details_no_delete BEFORE DELETE ON enrichment_proposal_details BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_proposal_sources_no_update BEFORE UPDATE ON enrichment_proposal_sources BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_proposal_sources_no_delete BEFORE DELETE ON enrichment_proposal_sources BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_spans_no_update BEFORE UPDATE ON enrichment_spans BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_spans_no_delete BEFORE DELETE ON enrichment_spans BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_studies_order_no_update BEFORE UPDATE ON enrichment_studies_order BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_studies_order_no_delete BEFORE DELETE ON enrichment_studies_order BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_datasets_order_no_update BEFORE UPDATE ON enrichment_datasets_order BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_datasets_order_no_delete BEFORE DELETE ON enrichment_datasets_order BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_analyses_order_no_update BEFORE UPDATE ON enrichment_analyses_order BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_analyses_order_no_delete BEFORE DELETE ON enrichment_analyses_order BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_variable_uses_order_no_update BEFORE UPDATE ON enrichment_variable_uses_order BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_variable_uses_order_no_delete BEFORE DELETE ON enrichment_variable_uses_order BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_findings_order_no_update BEFORE UPDATE ON enrichment_findings_order BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_findings_order_no_delete BEFORE DELETE ON enrichment_findings_order BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_analysis_datasets_no_update BEFORE UPDATE ON enrichment_analysis_datasets BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_analysis_datasets_no_delete BEFORE DELETE ON enrichment_analysis_datasets BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_variable_datasets_no_update BEFORE UPDATE ON enrichment_variable_datasets BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_variable_datasets_no_delete BEFORE DELETE ON enrichment_variable_datasets BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_finding_variables_no_update BEFORE UPDATE ON enrichment_finding_variables BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_finding_variables_no_delete BEFORE DELETE ON enrichment_finding_variables BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_secondary_classes_no_update BEFORE UPDATE ON enrichment_secondary_classes BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_secondary_classes_no_delete BEFORE DELETE ON enrichment_secondary_classes BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_framework_alternatives_no_update BEFORE UPDATE ON enrichment_framework_alternatives BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_framework_alternatives_no_delete BEFORE DELETE ON enrichment_framework_alternatives BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_facts_no_update BEFORE UPDATE ON enrichment_facts BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_facts_no_delete BEFORE DELETE ON enrichment_facts BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_fact_evidence_no_update BEFORE UPDATE ON enrichment_fact_evidence BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_fact_evidence_no_delete BEFORE DELETE ON enrichment_fact_evidence BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_normalization_receipts_no_update BEFORE UPDATE ON enrichment_normalization_receipts BEGIN SELECT RAISE(ABORT,'append_only'); END;

CREATE TRIGGER enrichment_normalization_receipts_no_delete BEFORE DELETE ON enrichment_normalization_receipts BEGIN SELECT RAISE(ABORT,'append_only'); END;
