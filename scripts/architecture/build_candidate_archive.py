"""Generate typed candidate observations in the existing private SQLite archive.

CSV columns are a closed ingress vocabulary, never arbitrary SQL identifiers.
This generator creates no runtime data and does not activate a cutover.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build():
    profile = json.loads((ROOT / 'ontology/cile-review-profile.yaml').read_text())
    domains = json.loads((ROOT / 'scripts/architecture/candidate-domains.json').read_text())
    for spec in domains.values():
        spec['allowed_values'] = {field: list(profile['enums'][name]['permissible_values'])
                                  for field, name in spec['controlled_fields'].items()}
    tables = {}
    sql = ['-- Candidate-bound observations; no work reconciliation or scientific decision.']

    def table(name, concept, body, fields):
        tables[name] = {'class': concept, 'fields': fields}
        sql.append(f'CREATE TABLE {name} (\n {body}\n);')

    table('enrichment_candidate_records', 'CandidateRecord', '''
 candidate_id TEXT NOT NULL, cycle_id TEXT NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(candidate_id,cycle_id)''',
          {'candidate_id': 'candidate_id', 'cycle_id': 'review_id', 'created_at': 'v2_created_at'})
    table('enrichment_candidate_revisions', 'MetadataAssertion', '''
 revision_id TEXT NOT NULL PRIMARY KEY, candidate_id TEXT NOT NULL, cycle_id TEXT NOT NULL,
 domain TEXT NOT NULL CHECK(domain IN ('bibliography','abstract','retrieval','access')),
 source_commit TEXT NOT NULL CHECK(length(source_commit)=40),
 content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64),
 storage_key TEXT NOT NULL UNIQUE, observed_at TEXT NOT NULL,
 UNIQUE(revision_id,candidate_id,cycle_id,domain),
 FOREIGN KEY(candidate_id,cycle_id) REFERENCES enrichment_candidate_records(candidate_id,cycle_id)''',
          {'revision_id': 'v2_assertion_id', 'candidate_id': 'candidate_id', 'cycle_id': 'review_id',
           'domain': 'dcterms:type', 'source_commit': 'was_derived_from',
           'content_sha256': 'enrichment_content_sha256', 'storage_key': 'enrichment_storage_key',
           'observed_at': 'enrichment_observed_at'})
    table('enrichment_candidate_heads', 'CandidateRecord', '''
 candidate_id TEXT NOT NULL, cycle_id TEXT NOT NULL, domain TEXT NOT NULL,
 revision_id TEXT NOT NULL, record_version INTEGER NOT NULL CHECK(record_version>=1),
 state TEXT NOT NULL CHECK(state IN ('active','withdrawn')), updated_at TEXT NOT NULL,
 PRIMARY KEY(candidate_id,cycle_id,domain),
 FOREIGN KEY(revision_id,candidate_id,cycle_id,domain)
 REFERENCES enrichment_candidate_revisions(revision_id,candidate_id,cycle_id,domain)''',
          {'candidate_id': 'candidate_id', 'cycle_id': 'review_id', 'domain': 'dcterms:type',
           'revision_id': 'v2_assertion_id', 'record_version': 'v2_record_version',
           'state': 'annotation_visibility_state', 'updated_at': 'ingress_updated_at'})
    table('enrichment_candidate_receipts', 'ReviewEvent', '''
 receipt_id TEXT NOT NULL PRIMARY KEY, candidate_id TEXT NOT NULL, cycle_id TEXT NOT NULL,
 domain TEXT NOT NULL, revision_id TEXT NOT NULL, previous_revision_id TEXT,
 action TEXT NOT NULL CHECK(action IN ('initialise','observe','supersede','withdraw')),
 expected_version INTEGER NOT NULL CHECK(expected_version>=0), persisted_at TEXT NOT NULL,
 FOREIGN KEY(revision_id,candidate_id,cycle_id,domain)
 REFERENCES enrichment_candidate_revisions(revision_id,candidate_id,cycle_id,domain),
 FOREIGN KEY(previous_revision_id,candidate_id,cycle_id,domain)
 REFERENCES enrichment_candidate_revisions(revision_id,candidate_id,cycle_id,domain)''',
          {'receipt_id': 'event_id', 'candidate_id': 'candidate_id', 'cycle_id': 'review_id',
           'domain': 'dcterms:type', 'revision_id': 'v2_assertion_id', 'previous_revision_id': 'supersedes',
           'action': 'dcterms:type', 'expected_version': 'v2_record_version', 'persisted_at': 'v2_imported_at'})
    all_repeated = sorted({f for d in domains.values() for f in d['repeated']})
    kinds = ','.join(repr(f) for f in all_repeated)
    table('enrichment_candidate_values', 'MetadataAssertion', f'''
 revision_id TEXT NOT NULL REFERENCES enrichment_candidate_revisions(revision_id),
 field TEXT NOT NULL CHECK(field IN ({kinds})), position INTEGER NOT NULL CHECK(position>=0),
 value TEXT NOT NULL CHECK(length(value)>0), PRIMARY KEY(revision_id,field,position)''',
          {'revision_id': 'v2_assertion_id', 'field': 'v2_field_uri',
           'position': 'v2_position', 'value': 'identifier_value'})
    for domain, spec in domains.items():
        fields = {'revision_id': 'v2_assertion_id'}
        columns = ['revision_id TEXT NOT NULL PRIMARY KEY REFERENCES enrichment_candidate_revisions(revision_id)']
        for field in spec['fields']:
            if field == 'candidate_id' or field in spec['repeated']:
                continue
            physical = 'observed_' + field if domain != 'bibliography' and field in ('title', 'doi') else field
            fields[physical] = spec['slots'][field]
            # Source lexemes (including empty/uncertain scores/years) are retained as
            # assertions. They are not parsed into invented numeric measurements.
            definition = f'{physical} TEXT NOT NULL'
            if field in spec['controlled_fields']:
                enum = profile['enums'][spec['controlled_fields'][field]]['permissible_values']
                allowed = ','.join(repr(v) for v in enum)
                definition += f' CHECK({physical} IN ({allowed}))'
            columns.append(definition)
        table('enrichment_candidate_' + domain, spec['class'], ',\n '.join(columns), fields)
        sql.append(f"CREATE TRIGGER candidate_{domain}_scope BEFORE INSERT ON enrichment_candidate_{domain} WHEN NOT EXISTS(SELECT 1 FROM enrichment_candidate_revisions WHERE revision_id=NEW.revision_id AND domain='{domain}') BEGIN SELECT RAISE(ABORT,'candidate_domain_mismatch'); END;")
    sql.extend([
        'CREATE INDEX candidate_revision_identity ON enrichment_candidate_revisions(candidate_id,cycle_id,domain);',
        'CREATE INDEX candidate_receipt_scope ON enrichment_candidate_receipts(candidate_id,cycle_id,domain,action,revision_id);',
        'CREATE INDEX candidate_receipt_revision ON enrichment_candidate_receipts(revision_id,action);',
        'CREATE INDEX candidate_receipt_export ON enrichment_candidate_receipts(cycle_id,domain,receipt_id);',
        "CREATE TRIGGER candidate_head_cas BEFORE UPDATE ON enrichment_candidate_heads WHEN NEW.candidate_id<>OLD.candidate_id OR NEW.cycle_id<>OLD.cycle_id OR NEW.domain<>OLD.domain OR NEW.record_version<>OLD.record_version+1 BEGIN SELECT RAISE(ABORT,'candidate_head_concurrency'); END;",
        "CREATE TRIGGER candidate_no_republication BEFORE UPDATE ON enrichment_candidate_heads WHEN OLD.state='withdrawn' BEGIN SELECT RAISE(ABORT,'candidate_restore_requires_reviewed_procedure'); END;",
    ])
    allowed = ' OR '.join("(r.domain='" + domain + "' AND NEW.field IN (" +
                          ','.join(repr(f) for f in spec['repeated']) + '))'
                          for domain, spec in domains.items() if spec['repeated'])
    sql.append(f"CREATE TRIGGER candidate_values_scope BEFORE INSERT ON enrichment_candidate_values WHEN NOT EXISTS(SELECT 1 FROM enrichment_candidate_revisions r WHERE r.revision_id=NEW.revision_id AND ({allowed})) BEGIN SELECT RAISE(ABORT,'candidate_repeated_field_scope'); END;")
    for name in tables:
        for action in ['UPDATE', 'DELETE']:
            if name == 'enrichment_candidate_heads' and action == 'UPDATE':
                continue
            sql.append(f"CREATE TRIGGER {name}_no_{action.lower()} BEFORE {action} ON {name} BEGIN SELECT RAISE(ABORT,'append_only'); END;")
    content = '\n\n'.join(sql) + '\n'
    (ROOT / 'curator-app/migrations/0009_candidate_archive.sql').write_text(content)
    (ROOT / 'curator-app/src/candidate-archive-migration.json').write_text(json.dumps(
        {'sql': content, 'sha256': hashlib.sha256(content.encode()).hexdigest()}, indent=2) + '\n')
    module = {'profile_version': profile['version'], 'contract': 'CILE-CANDIDATE-ARCHIVE-1',
              'schema': 'schema/candidate-archive.schema.json',
              'tables': tables, 'domains': domains,
              'authority': 'Staged importer until full-population migration, backup and writer cutover are verified.',
              'identity': 'Candidate identifiers are retained. Bibliographic author/identifier strings are source assertions, not disambiguated Agents or ScholarlyWorks.',
              'privacy': 'All observations and source lexemes are private; only explicit bibliographic allowlists may be exported.'}
    (ROOT / 'ontology/modules/candidate-archive.json').write_text(json.dumps(module, indent=2) + '\n')
    variants = []
    for domain, spec in domains.items():
        fields = {field: {'type': 'string', 'maxLength': 16000} for field in spec['fields']}
        for field in spec['required_fields']:
            fields[field]['minLength'] = 1
        for field, allowed in spec['allowed_values'].items():
            fields[field]['enum'] = allowed
        fields['candidate_id']['pattern'] = '^CAND-[A-Za-z0-9-]{1,100}$'
        variants.append({'type': 'object', 'additionalProperties': False,
                         'required': ['contract', 'action', 'domain', 'source_commit', 'expected_version', 'row'],
                         'properties': {'contract': {'const': module['contract']},
                                        'domain': {'const': domain},
                                        'action': {'enum': ['initialise', 'observe', 'supersede', 'withdraw']},
                                        'source_commit': {'type': 'string', 'pattern': '^[a-f0-9]{40}$'},
                                        'expected_version': {'type': 'integer', 'minimum': 0, 'maximum': 9007199254740991},
                                        'row': {'type': 'object', 'additionalProperties': False,
                                                'required': spec['fields'], 'properties': fields}}})
    schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema',
              'title': module['contract'], 'oneOf': variants}
    (ROOT / module['schema']).write_text(json.dumps(schema, indent=2) + '\n')


if __name__ == '__main__':
    build()
