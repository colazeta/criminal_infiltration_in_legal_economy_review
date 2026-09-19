"""Closed storage contract for observed GitHub inputs and unreviewed annotations."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION = 'CILE-ANNOTATION-ARCHIVE-1'


def build():
    profile = json.loads((ROOT / 'ontology/cile-review-profile.yaml').read_text())
    definitions = {
        'ingress_snapshots': ('LegacySnapshot', '''snapshot_id TEXT NOT NULL PRIMARY KEY,
 source_kind TEXT NOT NULL CHECK(source_kind IN ('github_issue','github_comment')),
 external_id TEXT NOT NULL, source_url TEXT NOT NULL, source_created_at TEXT NOT NULL,
 source_updated_at TEXT NOT NULL, content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64),
 storage_key TEXT NOT NULL UNIQUE, observed_at TEXT NOT NULL,
 UNIQUE(source_kind,external_id,content_sha256)''',
                             {'snapshot_id':'v2_snapshot_id','source_kind':'ingress_source_kind','external_id':'ingress_external_id','source_url':'source_url','source_created_at':'v2_created_at','source_updated_at':'ingress_updated_at','content_sha256':'enrichment_content_sha256','storage_key':'enrichment_storage_key','observed_at':'enrichment_observed_at'}),
        'manual_annotations': ('AssistantRecommendation', '''annotation_id TEXT NOT NULL PRIMARY KEY,
 snapshot_id TEXT NOT NULL UNIQUE REFERENCES enrichment_ingress_snapshots(snapshot_id),
 issue_snapshot_id TEXT NOT NULL REFERENCES enrichment_ingress_snapshots(snapshot_id),
 target_id TEXT REFERENCES enrichment_targets(target_id), candidate_marker TEXT,
 binding_state TEXT NOT NULL CHECK(binding_state IN ('candidate_bound','unresolved','conflict','unregistered')),
 review_state TEXT NOT NULL CHECK(review_state='unreviewed_manual_support'),
 authorised_display INTEGER NOT NULL CHECK(authorised_display IN (0,1)),
 unparsed_lines INTEGER NOT NULL CHECK(unparsed_lines>=0), imported_at TEXT NOT NULL,
 CHECK((binding_state='candidate_bound')=(target_id IS NOT NULL))''',
                               {'annotation_id':'annotation_id','snapshot_id':'v2_snapshot_id','issue_snapshot_id':'v2_snapshot_id','target_id':'enrichment_target_id','candidate_marker':'candidate_id','binding_state':'annotation_binding_state','review_state':'annotation_review_state','authorised_display':'annotation_display_authorised','unparsed_lines':'annotation_unparsed_lines','imported_at':'v2_imported_at'}),
        'annotation_sections': ('AnalyticalAnnotation', '''section_id TEXT NOT NULL PRIMARY KEY,
 annotation_id TEXT NOT NULL REFERENCES enrichment_manual_annotations(annotation_id),
 scope TEXT NOT NULL CHECK(scope IN ('overview','framework','studies','datasets','methods','variables','findings','sources')),
 group_label TEXT NOT NULL, position INTEGER NOT NULL CHECK(position>0),
 UNIQUE(annotation_id,position)''',
                                {'section_id':'v2_section_id','annotation_id':'annotation_id','scope':'annotation_scope','group_label':'v2_heading','position':'v2_position'}),
        'annotation_fields': ('AnalyticalAnnotation', '''field_id TEXT NOT NULL PRIMARY KEY,
 section_id TEXT NOT NULL REFERENCES enrichment_annotation_sections(section_id),
 field_name TEXT NOT NULL, value TEXT NOT NULL CHECK(length(value)>0 AND length(value)<=12000),
 position INTEGER NOT NULL CHECK(position>0), UNIQUE(section_id,position)''',
                              {'field_id':'annotation_id','section_id':'v2_section_id','field_name':'annotation_field','value':'extraction_value','position':'v2_position'}),
        'annotation_classes': ('ClinicalContributionProposal', '''assertion_id TEXT NOT NULL PRIMARY KEY,
 annotation_id TEXT NOT NULL REFERENCES enrichment_manual_annotations(annotation_id),
 field_id TEXT NOT NULL REFERENCES enrichment_annotation_fields(field_id),
 category TEXT NOT NULL CHECK(category IN ('aetiology','diagnosis','screening','therapy','prognosis','prevention')),
 role TEXT NOT NULL CHECK(role IN ('primary','secondary','alternative')),
 UNIQUE(field_id,category,role)''',
                               {'assertion_id':'annotation_id','annotation_id':'annotation_id','field_id':'annotation_id','category':'extraction_category','role':'annotation_class_role'}),
        'annotation_heads': ('PublicationState', '''external_id TEXT NOT NULL PRIMARY KEY,
 annotation_id TEXT NOT NULL REFERENCES enrichment_manual_annotations(annotation_id),
 state TEXT NOT NULL CHECK(state IN ('current','withdrawn','conflict')),
 record_version INTEGER NOT NULL CHECK(record_version>0), updated_at TEXT NOT NULL''',
                             {'external_id':'ingress_external_id','annotation_id':'annotation_id','state':'annotation_visibility_state','record_version':'v2_record_version','updated_at':'ingress_updated_at'}),
        'annotation_events': ('ReviewEvent', '''event_id TEXT NOT NULL PRIMARY KEY,
 external_id TEXT NOT NULL, annotation_id TEXT NOT NULL REFERENCES enrichment_manual_annotations(annotation_id),
 previous_annotation_id TEXT REFERENCES enrichment_manual_annotations(annotation_id),
 event_kind TEXT NOT NULL CHECK(event_kind IN ('import','revision','older_revision','conflict','withdrawal','retained_after_withdrawal')),
 observed_at TEXT NOT NULL''',
                              {'event_id':'event_id','external_id':'ingress_external_id','annotation_id':'annotation_id','previous_annotation_id':'v2_supersedes_id','event_kind':'annotation_event_kind','observed_at':'enrichment_observed_at'}),
        'annotation_receipts': ('ReviewEvent', '''receipt_id TEXT NOT NULL PRIMARY KEY,
 annotation_id TEXT NOT NULL UNIQUE REFERENCES enrichment_manual_annotations(annotation_id),
 transformation_version TEXT NOT NULL CHECK(transformation_version='CILE-ANNOTATION-ARCHIVE-1'),
 source_sha256 TEXT NOT NULL CHECK(length(source_sha256)=64),
 parsed_sha256 TEXT NOT NULL CHECK(length(parsed_sha256)=64),
 rebuilt_sha256 TEXT NOT NULL CHECK(rebuilt_sha256=parsed_sha256),
 verified_at TEXT NOT NULL''',
                                {'receipt_id':'v2_receipt_id','annotation_id':'annotation_id','transformation_version':'v2_protocol_version','source_sha256':'enrichment_content_sha256','parsed_sha256':'enrichment_content_sha256','rebuilt_sha256':'enrichment_content_sha256','verified_at':'enrichment_observed_at'}),
    }
    fields = {
        'overview':['summary','contribution','research_question','infiltration_definition','infiltration_operationalisation','authors_limitations'],
        'framework':['status','primary','secondary','alternative','rationale','secondary_rationale','alternative_rationale'],
        'studies':['study_type','research_question','population','sampling','sample_size','observation_unit','analysis_unit','geography','period'],
        'methods':['design','method','comparison','identification','validation','robustness','findings'],
        'datasets':['annotation_text'], 'variables':['annotation_text'], 'findings':['annotation_text'], 'sources':['source_url'],
    }
    sql = ['-- Original ingress captures and unreviewed annotations; no scientific acceptance.']
    tables = {}
    for name,(concept,body,mapping) in definitions.items():
        table='enrichment_'+name
        if name=='annotation_fields':
            domain=','.join("'"+v+"'" for v in sorted({v for values in fields.values() for v in values}))
            body += f',\n CHECK(field_name IN ({domain}))'
        sql.append(f'CREATE TABLE {table} (\n {body}\n);')
        tables[table]={'class':concept,'fields':mapping}
    sql += ["CREATE INDEX enrichment_annotation_target ON enrichment_manual_annotations(target_id);",
            "CREATE TRIGGER enrichment_annotation_head_identity BEFORE UPDATE ON enrichment_annotation_heads WHEN NEW.external_id<>OLD.external_id OR NEW.record_version<>OLD.record_version+1 BEGIN SELECT RAISE(ABORT,'annotation_head_concurrency'); END;",
            "CREATE TRIGGER enrichment_annotation_no_republish BEFORE UPDATE ON enrichment_annotation_heads WHEN OLD.state='withdrawn' AND NEW.state<>'withdrawn' BEGIN SELECT RAISE(ABORT,'annotation_withdrawal_requires_human_restore'); END;"]
    allowed = ' OR '.join("(s.scope='"+scope+"' AND NEW.field_name IN ("+','.join("'"+v+"'" for v in values)+"))" for scope,values in fields.items())
    sql.append(f"CREATE TRIGGER enrichment_annotation_field_scope BEFORE INSERT ON enrichment_annotation_fields WHEN NOT EXISTS(SELECT 1 FROM enrichment_annotation_sections s WHERE s.section_id=NEW.section_id AND ({allowed})) BEGIN SELECT RAISE(ABORT,'annotation_field_scope'); END;")
    sql.append("CREATE TRIGGER enrichment_annotation_class_scope BEFORE INSERT ON enrichment_annotation_classes WHEN NOT EXISTS(SELECT 1 FROM enrichment_annotation_fields f JOIN enrichment_annotation_sections s USING(section_id) WHERE f.field_id=NEW.field_id AND s.annotation_id=NEW.annotation_id AND s.scope='framework' AND f.field_name=NEW.role) BEGIN SELECT RAISE(ABORT,'annotation_class_scope'); END;")
    for table in tables:
        for action in ['UPDATE','DELETE']:
            if table=='enrichment_annotation_heads' and action=='UPDATE': continue
            sql.append(f"CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'append_only'); END;")
    content='\n\n'.join(sql)+'\n'
    (ROOT/'curator-app/migrations/0008_annotation_archive.sql').write_text(content)
    (ROOT/'curator-app/src/annotation-archive-migration.json').write_text(json.dumps({'sql':content,'sha256':hashlib.sha256(content.encode()).hexdigest()},indent=2)+'\n')
    module={'profile_version':profile['version'],'contract':VERSION,'tables':tables,'field_names':fields,
            'privacy_boundary':'Private immutable GitHub snapshots; public projection includes only named reading fields and safe source URLs. No reviewer, analyst notes, original source text or complete-analysis attestation.',
            'identity_boundary':'Exact consistent issue and annotation markers bind an existing candidate target; absent or conflicting markers are retained exceptions. No canonical work or source-content version is inferred.'}
    (ROOT/'ontology/modules/annotation-archive.json').write_text(json.dumps(module,indent=2)+'\n')


if __name__=='__main__': build()
