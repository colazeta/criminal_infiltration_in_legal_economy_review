"""Regression checks for preservation and the fresh operational cycle."""
import csv
import hashlib
import json
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/metrics'))
from build_research_stats import active_runs
from daily_calendar import calendar_projection, validate_calendar, CYCLE
from fetch_surveillance_ledger import fetch_validated_runs
from scripts.curation.import_intake_issue import import_candidates, IntakeImportError
from test_surveillance_metrics import completed_run

class ArchiveResetTests(unittest.TestCase):
    def test_retired_files_are_byte_identical_and_scientific_vocabulary_is_retained(self):
        retired = ROOT / 'data/legacy/pre-oa-reset-2026-09-08'
        manifest = json.loads((retired / 'inventory.json').read_text())
        for name, item in manifest['files'].items():
            content = (retired / name).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), item['sha256'], name)
            self.assertEqual(len(content), item['bytes'], name)
        for name in ('taxonomy.csv', 'exclusion_reasons.csv', 'secondary_collections.csv'):
            self.assertEqual((retired / 'registry' / name).read_bytes(), (ROOT / 'data/registry' / name).read_bytes())

    def test_old_intake_is_blocked_before_parsing_or_writing(self):
        target = ROOT / 'data/curation/review_queue.csv'
        before = target.read_bytes()
        with self.assertRaisesRegex(IntakeImportError, 'retired archive'):
            import_candidates(ROOT, '', '', '99', '2026-09-09')
        self.assertEqual(target.read_bytes(), before)

    def test_pilot_materialiser_cannot_repopulate_the_active_queue(self):
        target = ROOT / 'data/curation/review_queue.csv'
        before = target.read_bytes()
        process = subprocess.run([sys.executable, 'scripts/curation/build_legacy_queue.py'], cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn('Legacy materialisation is retired', process.stderr)
        self.assertEqual(target.read_bytes(), before)

    def test_current_statistics_exclude_old_days_and_preserve_missing_days(self):
        old = completed_run('2026-09-08')
        new = completed_run('2026-09-09')
        self.assertEqual(active_runs([old, new]), [new])
        start = date.fromisoformat(CYCLE['daily_start_date'])
        calendar = calendar_projection([], '2026-09-10T12:00:00Z', start, CYCLE['review_id'])
        validate_calendar(calendar, [])
        self.assertEqual([r['date'] for r in calendar['rows']], ['2026-09-09', '2026-09-10'])
        self.assertEqual(calendar['missingDays'], 2)
        self.assertTrue(all(r['queriesCompleted'] is None for r in calendar['rows']))
        self.assertEqual(calendar_projection([], CYCLE['reset_at'], start, CYCLE['review_id'])['rows'], [])
        with self.assertRaisesRegex(ValueError, 'predates'):
            calendar_projection([old], '2026-09-10T12:00:00Z', start, CYCLE['review_id'])

    def test_retired_ledger_comments_are_preserved_but_not_reimported(self):
        comment = {'created_at':'2026-09-08T05:20:00Z', 'user':{'login':'colazeta'}, 'body':'Historical comment remains in GitHub.'}
        with patch('fetch_surveillance_ledger.api_get', return_value=([comment], {})) as request:
            self.assertEqual(fetch_validated_runs('colazeta/criminal_infiltration_in_legal_economy_review', 30, ['colazeta'], 'test', CYCLE), [])
            self.assertEqual(request.call_count, 1)
