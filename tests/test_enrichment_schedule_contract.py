"""Operational schema and scheduling checks; never synthetic research receipts."""
import json
import sqlite3
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class ScheduleContractTests(unittest.TestCase):
    def test_all_schedule_fields_have_semantic_slots(self):
        profile=json.loads((ROOT/'ontology/cile-review-profile.yaml').read_text())
        contract=json.loads((ROOT/'ontology/modules/enrichment-schedule.json').read_text())
        self.assertEqual(profile['version'],contract['profile_version'])
        db=sqlite3.connect(':memory:');db.executescript((ROOT/contract['migration']).read_text())
        self.assertEqual(set(contract['tables']),{row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")})
        for table,fields in contract['tables'].items():
            self.assertEqual(set(fields),{row[1] for row in db.execute(f'PRAGMA table_info({table})')})
            self.assertTrue(set(fields.values()).issubset(profile['slots']))
            self.assertEqual(db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0],0)
        self.assertTrue(set(contract['classes']).issubset(profile['classes']))

    def test_worker_exposes_alarm_and_exact_hour40_trigger(self):
        cfg=json.loads((ROOT/'curator-app/wrangler.example.jsonc').read_text())
        self.assertIn('40 * * * *',cfg['triggers']['crons'])
        source=(ROOT/'curator-app/src/worker.js').read_text()
        self.assertIn('alarm() { return this.core.alarm(); }',source)
        self.assertNotIn('cancel-in-progress: true',(ROOT/'.github/workflows/enrichment-pilot.yml').read_text())
