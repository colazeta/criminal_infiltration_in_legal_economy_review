"""Regression for the audited missing-OA intake bypass; all data are synthetic."""
import copy
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_surveillance_metrics import candidate_issue, exa_run, completed_run
from scripts.curation.import_intake_issue import parse_intake_issue, import_candidates, IntakeImportError
from scripts.intake_open_access import validate_snapshots
from fetch_surveillance_ledger import verify_intake_issue
from surveillance import MetricsError

ROOT = Path(__file__).resolve().parents[1]


def altered_issue(change):
    issue = candidate_issue(exa_run(), number=201)
    manifest = parse_intake_issue(issue['body'], issue['title'])
    before = json.dumps(manifest)
    change(manifest['candidates'][0])
    issue['body'] = issue['body'].replace(before, json.dumps(manifest))
    return issue


class IntakeOpenAccessTests(unittest.TestCase):
    def assert_both_reject(self, issue):
        with self.assertRaises((IntakeImportError, MetricsError)):
            parse_intake_issue(issue['body'], issue['title'])
        with self.assertRaises(MetricsError):
            verify_intake_issue(exa_run(), issue, {'colazeta'}, 30)

    def test_original_missing_receipt_bypass_is_closed(self):
        self.assert_both_reject(altered_issue(lambda c: c.pop('open_access')))

    def test_insufficient_access_evidence_is_rejected_in_both_paths(self):
        for field, value in (
            ('access_status', 'unknown'), ('access_status', 'restricted'),
            ('access_status', 'revoked'), ('version_type', 'preprint'),
            ('host_type', 'aggregator'), ('rights_basis', ''),
            ('verification_method', 'oa_flag'), ('full_text_sha256', 'not-a-hash'),
            ('verified_at', '2026-09-09'), ('verified_at', '2026-09-10T00:00:00Z'),
            ('rights_evidence_url', 'https://user:password@example.org/rights'),
            ('license_uri', None), ('full_text_sha256', True),
        ):
            with self.subTest(field=field, value=value):
                self.assert_both_reject(altered_issue(lambda c: c['open_access'].__setitem__(field, value)))

    def test_receipt_is_bound_to_candidate_and_source_copy(self):
        for field, value in (('candidate_id', 'CAND-ACADEMIC-2026-09-09-999'), ('full_text_url', 'https://example.org/another-paper')):
            with self.subTest(field=field):
                self.assert_both_reject(altered_issue(lambda c: c['open_access'].__setitem__(field, value)))

    def test_unexpected_receipt_content_is_rejected(self):
        self.assert_both_reject(altered_issue(lambda c: c['open_access'].__setitem__('full_text', 'Never persist article bodies')))

    def test_legacy_v1_remains_readable_without_receipts(self):
        run = completed_run()
        verify_intake_issue(run, candidate_issue(run), {'colazeta'}, 30)

    def empty_root(self, root):
        path = root / 'data/curation/review_queue.csv'
        path.parent.mkdir(parents=True)
        path.write_text((ROOT / 'data/curation/review_queue.csv').read_text().splitlines()[0] + '\n')
        return path

    def test_import_preserves_receipts_and_original_body_hash_without_approval(self):
        issue = candidate_issue(exa_run(), number=201)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); queue = self.empty_root(root)
            import_candidates(root, issue['body'], issue['title'], '201', '2026-09-09')
            self.assertEqual(validate_snapshots(root), 3)
            snapshot_path = root / 'data/curation/intake_access/ACADEMIC-2026-09-09.json'
            original = snapshot_path.read_bytes(); snapshot = json.loads(original)
            self.assertEqual(snapshot['source_body_sha256'], hashlib.sha256(issue['body'].encode()).hexdigest())
            self.assertEqual(snapshot['receipts'], [c['open_access'] for c in parse_intake_issue(issue['body'], issue['title'])['candidates']])
            with queue.open() as handle:
                rows = list(csv.DictReader(handle))
            self.assertTrue(all(r['current_status'] == 'pending' and r['current_decision'] == '' for r in rows))
            with self.assertRaises(IntakeImportError):
                import_candidates(root, issue['body'], issue['title'], '201', '2026-09-09')
            self.assertEqual(snapshot_path.read_bytes(), original)
            snapshot_path.unlink()
            with self.assertRaisesRegex(ValueError, 'missing preserved'):
                validate_snapshots(root)

    def test_invalid_intake_does_not_touch_queue_or_create_snapshot(self):
        issue = altered_issue(lambda c: c.pop('open_access'))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); queue = self.empty_root(root); original = queue.read_bytes()
            with self.assertRaises(IntakeImportError):
                import_candidates(root, issue['body'], issue['title'], '201', '2026-09-09')
            self.assertEqual(queue.read_bytes(), original)
            self.assertFalse((root / 'data/curation/intake_access').exists())

    def test_failed_queue_write_removes_only_new_receipt(self):
        issue = candidate_issue(exa_run(), number=201)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); queue = self.empty_root(root); original = queue.read_bytes()
            with patch('scripts.curation.import_intake_issue.os.replace', side_effect=OSError('synthetic disk failure')):
                with self.assertRaises(OSError):
                    import_candidates(root, issue['body'], issue['title'], '201', '2026-09-09')
            self.assertEqual(queue.read_bytes(), original)
            self.assertEqual(list((root / 'data/curation/intake_access').glob('*.json')), [])

    def test_existing_snapshot_cannot_be_overwritten(self):
        issue = candidate_issue(exa_run(), number=201)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); queue = self.empty_root(root); original = queue.read_bytes()
            path = root / 'data/curation/intake_access/ACADEMIC-2026-09-09.json'
            path.parent.mkdir(); path.write_text('existing evidence')
            with self.assertRaises(FileExistsError):
                import_candidates(root, issue['body'], issue['title'], '201', '2026-09-09')
            self.assertEqual(path.read_text(), 'existing evidence')
            self.assertEqual(queue.read_bytes(), original)
