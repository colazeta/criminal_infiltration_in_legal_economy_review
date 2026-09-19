"""Rebuild the actual SQL dictionary and ontology traceability; no production claims."""
import csv
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def catalogue(root=ROOT):
    profile = json.loads((root / 'ontology/cile-review-profile.yaml').read_text())
    contracts = {}
    for module in ['review-v2', 'enrichment-adjudication', 'enrichment-delivery-assets', 'extraction-relations', 'annotation-archive', 'candidate-archive']:
        contracts.update(json.loads((root / f'ontology/modules/{module}.json').read_text())['tables'])
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    migrations, owners = [], {}
    for path in sorted((root / 'curator-app/migrations').glob('*.sql')):
        before = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        content = path.read_text()
        db.executescript(content)
        after = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        relative = str(path.relative_to(root))
        for name in after - before:
            owners[name] = relative
        migrations.append({'path': relative, 'sha256': hashlib.sha256(content.encode()).hexdigest()})
    physical, trace = [], []
    for table, sql in db.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
        mapping = contracts.get(table)
        if not mapping:
            raise ValueError('unmapped_table:' + table)
        columns = [dict(r) for r in db.execute(f'PRAGMA table_info("{table}")')]
        if set(mapping['fields']) != {c['name'] for c in columns}:
            raise ValueError('unmapped_column:' + table)
        foreign = [dict(r) for r in db.execute(f'PRAGMA foreign_key_list("{table}")')]
        indexes = []
        for row in db.execute(f'PRAGMA index_list("{table}")').fetchall():
            index = dict(row)
            index['columns'] = [dict(r) for r in db.execute(f'PRAGMA index_info("{row[1]}")')]
            index['sql'] = db.execute('SELECT sql FROM sqlite_master WHERE name=?', (row[1],)).fetchone()[0]
            indexes.append(index)
        storage = 'configured_enrichment_sqlite' if table.startswith('enrichment_') else 'prepared_v2_not_runtime_verified'
        for column in columns:
            field = mapping['fields'][column['name']]
            slot = field.get('slot') if isinstance(field, dict) else field
            if slot not in profile['slots'] and ':' not in slot:
                raise ValueError('undeclared_slot:' + slot)
            # Ordinary SQLite TEXT PRIMARY KEY does not imply NOT NULL.
            nullable = not column['notnull'] and not (column['type'] == 'INTEGER' and column['pk'])
            trace.append({'concept': mapping['class'], 'slot': slot, 'table': table,
                          'column': column['name'], 'type': column['type'],
                          'primary_key_position': column['pk'], 'nullable_in_sqlite': nullable,
                          'default': column['dflt_value'], 'migration': owners[table],
                          'implementation_status': storage})
        physical.append({'table': table, 'concept': mapping['class'], 'migration': owners[table],
                         'implementation_status': storage, 'columns': columns,
                         'foreign_keys': foreign, 'indexes': indexes, 'sql': sql,
                         'triggers': [dict(r) for r in db.execute('SELECT name,sql FROM sqlite_master WHERE type=\'trigger\' AND tbl_name=? ORDER BY name', (table,))]})
    db.close()
    return {'profile_version': profile['version'], 'runtime_verified': False,
            'migrations': migrations, 'tables': physical}, trace


def write(root=ROOT):
    output = root / 'docs/architecture'
    output.mkdir(parents=True, exist_ok=True)
    physical, trace = catalogue(root)
    (output / 'physical-schema.json').write_text(json.dumps(physical, indent=2) + '\n')
    with (output / 'traceability.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(trace[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(trace)
    print(json.dumps({'tables': len(physical['tables']), 'columns': len(trace),
                      'runtime_verified': False}))


if __name__ == '__main__':
    write()
