"""Generate closed relational extraction DDL from the governed extraction schema."""
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GROUPS = {'studies': ('study', 'study_id', 'ReportedStudy'),
          'datasets': ('dataset', 'dataset_id', 'StudyDatasetUse'),
          'analyses': ('analysis', 'analysis_id', 'ReportedAnalysis'),
          'variable_uses': ('variable_use', 'variable_use_id', 'AnalysisVariableUse'),
          'findings': ('finding', 'finding_id', 'ReportedFinding')}


def build():
    schema = json.loads((ROOT / 'schema/paper-enrichment.schema.json').read_text())
    quote = lambda values: ','.join("'" + value + "'" for value in values)
    categories = [v for v in schema['$defs']['framework']['properties']['primary']['enum'] if v]
    facts = {'overview': [k for k, v in schema['properties'].items() if v.get('$ref') == '#/$defs/fact']}
    facts.update({g: [k for k, v in schema['$defs'][definition]['properties'].items() if v.get('$ref') == '#/$defs/fact'] for g, (definition, _, _) in GROUPS.items()})
    facts.update({'framework': ['rationale'], 'secondary': ['rationale']})
    sql = ["-- CILE-EXTRACTION-RELATIONS-1. Additive; original submissions remain immutable history.\n"]
    tables = {}

    def table(name, concept, body, mapping):
        name = 'enrichment_' + name
        sql.append(f'CREATE TABLE {name} (\n {body}\n);\n')
        tables[name] = {'class': concept, 'fields': mapping}

    table('proposal_details', 'ScientificExtractionProposal',
          "proposal_id TEXT NOT NULL PRIMARY KEY REFERENCES enrichment_proposals(proposal_id),\n source_coverage TEXT NOT NULL CHECK(source_coverage IN ('abstract_only','partial_text','full_text')),\n agent TEXT NOT NULL, model TEXT, prompt_sha256 TEXT CHECK(prompt_sha256 IS NULL OR length(prompt_sha256)=64)",
          {'proposal_id': 'enrichment_proposal_id', 'source_coverage': 'extraction_source_coverage', 'agent': 'extraction_agent', 'model': 'extraction_model', 'prompt_sha256': 'extraction_prompt_sha256'})
    table('proposal_sources', 'ScientificExtractionProposal',
          "proposal_id TEXT NOT NULL REFERENCES enrichment_proposals(proposal_id), source_id TEXT NOT NULL REFERENCES enrichment_sources(source_id),\n position INTEGER NOT NULL CHECK(typeof(position)=\'integer\' AND position>0), PRIMARY KEY(proposal_id,source_id), UNIQUE(proposal_id,position)",
          {'proposal_id': 'enrichment_proposal_id', 'source_id': 'enrichment_source_id', 'position': 'v2_position'})
    sql.append("""CREATE TRIGGER enrichment_proposal_sources_scope BEFORE INSERT ON enrichment_proposal_sources
 WHEN NOT EXISTS(SELECT 1 FROM enrichment_proposals p JOIN enrichment_sources s ON s.target_id=p.target_id AND s.input_sha256=p.input_sha256 WHERE p.proposal_id=NEW.proposal_id AND s.source_id=NEW.source_id AND s.evidence_kind<>'metadata')
 BEGIN SELECT RAISE(ABORT,'source_scope_mismatch'); END;
""")
    table('spans', 'EvidenceSpan',
          "proposal_id TEXT NOT NULL, span_id TEXT NOT NULL, source_id TEXT NOT NULL,\n position INTEGER NOT NULL CHECK(typeof(position)=\'integer\' AND position>0), start_offset INTEGER NOT NULL CHECK(typeof(start_offset)=\'integer\' AND start_offset>=0),\n end_offset INTEGER NOT NULL CHECK(typeof(end_offset)=\'integer\' AND end_offset>start_offset), locator TEXT NOT NULL,\n PRIMARY KEY(proposal_id,span_id), UNIQUE(proposal_id,position),\n FOREIGN KEY(proposal_id,source_id) REFERENCES enrichment_proposal_sources(proposal_id,source_id)",
          {'proposal_id': 'enrichment_proposal_id', 'span_id': 'extraction_id', 'source_id': 'extraction_source_id', 'position': 'v2_position', 'start_offset': 'extraction_start_offset', 'end_offset': 'extraction_end_offset', 'locator': 'extraction_locator'})
    for group, (_, key, concept) in GROUPS.items():
        table(group + '_order', concept,
              f'proposal_id TEXT NOT NULL, {key} TEXT NOT NULL, position INTEGER NOT NULL CHECK(typeof(position)=\'integer\' AND position>0),\n PRIMARY KEY(proposal_id,{key}), UNIQUE(proposal_id,position),\n FOREIGN KEY(proposal_id,{key}) REFERENCES enrichment_{group}(proposal_id,{key})',
              {'proposal_id': 'enrichment_proposal_id', key: 'enrichment_' + key, 'position': 'v2_position'})
    for name, owner, key, target, target_key, concept in [
        ('analysis_datasets', 'analyses', 'analysis_id', 'datasets', 'dataset_id', 'ReportedAnalysis'),
        ('variable_datasets', 'variable_uses', 'variable_use_id', 'datasets', 'dataset_id', 'AnalysisVariableUse'),
        ('finding_variables', 'findings', 'finding_id', 'variable_uses', 'variable_use_id', 'ReportedFinding')]:
        table(name, concept,
              f'proposal_id TEXT NOT NULL, {key} TEXT NOT NULL, {target_key} TEXT NOT NULL, position INTEGER NOT NULL CHECK(typeof(position)=\'integer\' AND position>0),\n PRIMARY KEY(proposal_id,{key},{target_key}), UNIQUE(proposal_id,{key},position),\n FOREIGN KEY(proposal_id,{key}) REFERENCES enrichment_{owner}(proposal_id,{key}),\n FOREIGN KEY(proposal_id,{target_key}) REFERENCES enrichment_{target}(proposal_id,{target_key})',
              {'proposal_id': 'enrichment_proposal_id', key: 'enrichment_' + key, target_key: 'enrichment_' + target_key, 'position': 'v2_position'})
    sql.append("""CREATE TRIGGER enrichment_analysis_datasets_scope BEFORE INSERT ON enrichment_analysis_datasets
 WHEN NOT EXISTS(SELECT 1 FROM enrichment_analyses a JOIN enrichment_datasets d ON d.proposal_id=a.proposal_id AND d.study_id=a.study_id WHERE a.proposal_id=NEW.proposal_id AND a.analysis_id=NEW.analysis_id AND d.dataset_id=NEW.dataset_id)
 BEGIN SELECT RAISE(ABORT,'cross_study_dataset'); END;
CREATE TRIGGER enrichment_variable_datasets_scope BEFORE INSERT ON enrichment_variable_datasets
 WHEN NOT EXISTS(SELECT 1 FROM enrichment_variable_uses v JOIN enrichment_analysis_datasets a ON a.proposal_id=v.proposal_id AND a.analysis_id=v.analysis_id WHERE v.proposal_id=NEW.proposal_id AND v.variable_use_id=NEW.variable_use_id AND a.dataset_id=NEW.dataset_id)
 BEGIN SELECT RAISE(ABORT,'variable_dataset_scope'); END;
CREATE TRIGGER enrichment_finding_variables_scope BEFORE INSERT ON enrichment_finding_variables
 WHEN NOT EXISTS(SELECT 1 FROM enrichment_findings f JOIN enrichment_variable_uses v ON v.proposal_id=f.proposal_id AND v.analysis_id=f.analysis_id WHERE f.proposal_id=NEW.proposal_id AND f.finding_id=NEW.finding_id AND v.variable_use_id=NEW.variable_use_id)
 BEGIN SELECT RAISE(ABORT,'finding_variable_scope'); END;
""")
    table('secondary_classes', 'ClinicalContributionProposal',
          f'proposal_id TEXT NOT NULL REFERENCES enrichment_proposals(proposal_id), category TEXT NOT NULL CHECK(category IN ({quote(categories)})),\n position INTEGER NOT NULL CHECK(typeof(position)=\'integer\' AND position>0), PRIMARY KEY(proposal_id,category), UNIQUE(proposal_id,position)',
          {'proposal_id': 'enrichment_proposal_id', 'category': 'extraction_category', 'position': 'v2_position'})
    table('framework_alternatives', 'ClinicalContributionProposal',
          f'proposal_id TEXT NOT NULL PRIMARY KEY REFERENCES enrichment_proposals(proposal_id), category TEXT CHECK(category IS NULL OR category IN ({quote(categories)}))',
          {'proposal_id': 'enrichment_proposal_id', 'category': 'extraction_alternative'})
    owners = [key for _, key, _ in GROUPS.values()] + ['secondary_category']
    owner_fields = ', '.join(key + ' TEXT' for key in owners)
    checks = []
    for scope, fields in facts.items():
        own = GROUPS[scope][1] if scope in GROUPS else 'secondary_category' if scope == 'secondary' else None
        checks.append(f"(scope='{scope}' AND field_name IN ({quote(fields)}) AND " + ' AND '.join(key + (' IS NOT NULL' if key == own else ' IS NULL') for key in owners) + ')')
    fks = ',\n '.join(f'FOREIGN KEY(proposal_id,{key}) REFERENCES enrichment_{group}(proposal_id,{key})' for group, (_, key, _) in GROUPS.items())
    table('facts', 'AnalyticalAnnotation',
          f"fact_id TEXT NOT NULL PRIMARY KEY, proposal_id TEXT NOT NULL REFERENCES enrichment_proposals(proposal_id),\n scope TEXT NOT NULL, field_name TEXT NOT NULL, {owner_fields},\n status TEXT NOT NULL CHECK(status IN ('reported','not_reported','not_verifiable','not_applicable','ambiguous')),\n value TEXT, origin TEXT NOT NULL CHECK(origin IN ('source','analyst')),\n UNIQUE(fact_id,proposal_id), CHECK(value IS NULL OR length(value)<=6000),\n CHECK(status NOT IN ('reported','ambiguous') OR (value IS NOT NULL AND length(value)>0)), CHECK(status NOT IN ('not_reported','not_verifiable','not_applicable') OR value IS NULL),\n CHECK({' OR '.join(checks)}),\n {fks},\n FOREIGN KEY(proposal_id,secondary_category) REFERENCES enrichment_secondary_classes(proposal_id,category)",
          {'fact_id': 'annotation_id', 'proposal_id': 'enrichment_proposal_id', 'scope': 'annotation_scope', 'field_name': 'annotation_field', **{k: 'enrichment_' + k for _, k, _ in GROUPS.values()}, 'secondary_category': 'extraction_category', 'status': 'extraction_status', 'value': 'extraction_value', 'origin': 'extraction_origin'})
    for scope in facts:
        owner = GROUPS[scope][1] if scope in GROUPS else 'secondary_category' if scope == 'secondary' else None
        sql.append(f"CREATE UNIQUE INDEX enrichment_fact_{scope} ON enrichment_facts(proposal_id,{owner+',' if owner else ''}field_name) WHERE scope='{scope}';\n")
    table('fact_evidence', 'AnalyticalAnnotation',
          'fact_id TEXT NOT NULL, proposal_id TEXT NOT NULL, span_id TEXT NOT NULL, position INTEGER NOT NULL CHECK(typeof(position)=\'integer\' AND position>0),\n PRIMARY KEY(fact_id,span_id), UNIQUE(fact_id,position),\n FOREIGN KEY(fact_id,proposal_id) REFERENCES enrichment_facts(fact_id,proposal_id),\n FOREIGN KEY(proposal_id,span_id) REFERENCES enrichment_spans(proposal_id,span_id)',
          {'fact_id': 'annotation_id', 'proposal_id': 'enrichment_proposal_id', 'span_id': 'extraction_evidence_span_ids', 'position': 'v2_position'})
    table('normalization_receipts', 'ReviewEvent',
          "receipt_id TEXT NOT NULL PRIMARY KEY, proposal_id TEXT NOT NULL UNIQUE REFERENCES enrichment_proposals(proposal_id),\n transformation_version TEXT NOT NULL CHECK(transformation_version='CILE-EXTRACTION-RELATIONS-1'),\n source_sha256 TEXT NOT NULL CHECK(length(source_sha256)=64), rebuilt_sha256 TEXT NOT NULL CHECK(rebuilt_sha256=source_sha256),\n write_kind TEXT NOT NULL CHECK(write_kind IN ('native','backfill')), verified_at TEXT NOT NULL",
          {'receipt_id': 'event_id', 'proposal_id': 'enrichment_proposal_id', 'transformation_version': 'version', 'source_sha256': 'enrichment_payload_sha256', 'rebuilt_sha256': 'enrichment_payload_sha256', 'write_kind': 'annotation_write_kind', 'verified_at': 'generated_at_time'})
    sql.append("""CREATE TRIGGER enrichment_normalization_evidence_required BEFORE INSERT ON enrichment_normalization_receipts
 WHEN EXISTS(SELECT 1 FROM enrichment_facts f WHERE f.proposal_id=NEW.proposal_id AND f.status='reported' AND NOT EXISTS(SELECT 1 FROM enrichment_fact_evidence e WHERE e.fact_id=f.fact_id))
 BEGIN SELECT RAISE(ABORT,'reported_fact_requires_evidence'); END;
""")
    for name in tables:
        for action in ['update', 'delete']:
            sql.append(f"CREATE TRIGGER {name}_no_{action} BEFORE {action.upper()} ON {name} BEGIN SELECT RAISE(ABORT,'append_only'); END;\n")
    ddl = '\n'.join(sql)
    path = 'curator-app/migrations/0007_extraction_relations.sql'
    (ROOT / path).write_text(ddl)
    (ROOT / 'curator-app/src/extraction-relations-migration.json').write_text(json.dumps({'sql': ddl, 'sha256': hashlib.sha256(ddl.encode()).hexdigest()}, indent=2) + '\n')
    module = {'profile_version': '0.4.2', 'contract': 'CILE-EXTRACTION-RELATIONS-1', 'migration': path,
              'scope': 'immutable proposal-scoped assertions; no automatic scientific acceptance',
              'fact_fields': facts, 'tables': tables,
              'semantics': 'Original proposal and child payload JSON are immutable submission history. All current extraction reads rebuild from the typed relations and assertions and check the original payload digest. No latest-string conflict resolution, identity reconciliation or human approval is implied.'}
    (ROOT / 'ontology/modules/extraction-relations.json').write_text(json.dumps(module, indent=2) + '\n')


if __name__ == '__main__':
    build()
