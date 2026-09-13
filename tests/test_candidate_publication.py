from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from scripts.curation.build_paper_register import FIELDS
from scripts.curation.verify_published_register import compare_registers, record_index, public_bytes
from scripts.metrics.mark_statistics_unavailable import mark_unavailable, WARNING
ROOT = Path(__file__).resolve().parents[1]

def payload(*ids):
    rows=[]
    for cid in ids:
        row={field: '' for field in FIELDS}
        row.update(id=cid, title='Example '+cid, year=None, sourceLinks=[], reviewStatus='pending', accessStatus='unknown')
        rows.append(row)
    return {'schemaVersion':1, 'records':rows}

class PublicCandidateVerificationTests(unittest.TestCase):
    def test_exact_or_newer_superset_is_verified(self):
        self.assertEqual(compare_registers(payload('A'), payload('A', 'B'))['missing_records'], 0)
    def test_equal_counts_with_different_identities_do_not_pass(self):
        with self.assertRaisesRegex(ValueError, 'missing'): compare_registers(payload('A'), payload('B'))
    def test_stale_subset_does_not_pass(self):
        with self.assertRaises(ValueError): compare_registers(payload('A', 'B'), payload('A'))
    def test_duplicate_identity_does_not_pass(self):
        with self.assertRaises(ValueError): record_index(payload('A', 'A'))
    def test_same_identity_with_stale_metadata_does_not_pass(self):
        old=payload('A'); old['records'][0]['title']='Stale title'
        with self.assertRaisesRegex(ValueError, 'changed'): compare_registers(payload('A'), old)
    def test_internal_fields_cannot_be_smuggled_into_public_evidence(self):
        invalid=payload('A'); invalid['records'][0]['reviewer_note']='private'
        with self.assertRaisesRegex(ValueError,'allowlist'): record_index(invalid)
    def test_private_or_credential_bearing_hosts_are_never_requested(self):
        for url in ('http://colazeta.github.io/data.json', 'https://example.org/data.json', 'https://user:pass@colazeta.github.io/data.json'):
            with self.assertRaises(ValueError): public_bytes(url)
    def test_workflow_verifies_after_deployment(self):
        workflow=(ROOT/'.github/workflows/archive.yml').read_text()
        self.assertLess(workflow.index('id: deployment'), workflow.index('verify_published_register.py'))
        self.assertIn('queue: max',workflow)
        self.assertNotIn('cancel-in-progress: true',workflow)

class AggregateFailureIsolationTests(unittest.TestCase):
    def test_failed_telemetry_is_explicit_and_cannot_be_rendered_as_no_results(self):
        with tempfile.TemporaryDirectory() as folder:
            page=Path(folder)/'stats.html'; stats=Path(folder)/'stats.json'
            page.write_text('<p id="latest-execution">Old result</p><script src="./stats.js" defer></script>')
            stats.write_text((ROOT/'site/data/research-stats.json').read_text())
            mark_unavailable(page,stats)
            self.assertIn(WARNING,page.read_text())
            self.assertNotIn('stats.js',page.read_text())
            self.assertIsNone(json.loads(stats.read_text())['summary']['allTime']['newCandidates'])
    def test_nonempty_counts_cannot_be_relabelled_unavailable(self):
        with tempfile.TemporaryDirectory() as folder:
            page=Path(folder)/'stats.html'; stats=Path(folder)/'stats.json'
            page.write_text('<p id="latest-execution">Old result</p>')
            data=json.loads((ROOT/'site/data/research-stats.json').read_text())
            data['summary']['allTime']['newCandidates']=12
            stats.write_text(json.dumps(data))
            with self.assertRaises(ValueError): mark_unavailable(page,stats)
    def test_only_metrics_read_is_optional_and_failure_remains_reported(self):
        workflow=(ROOT/'.github/workflows/archive.yml').read_text()
        self.assertEqual(workflow.count('continue-on-error: true'),1)
        self.assertIn('id: metrics\n        continue-on-error: true',workflow)
        self.assertIn("steps.metrics.outcome != 'success'",workflow)
        self.assertIn('Daily statistics failed validation and were not published',workflow)
        self.assertIn('python scripts/ontology/validate_ontology.py',workflow)
