import copy
import json
from pathlib import Path
import unittest

from scripts.enrichment.import_verified_bibliography import import_verified, validate_manifest

ROOT = Path(__file__).resolve().parents[1]


class VerifiedBibliographyImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / 'config/verified-bibliography-seed.json').read_text())

    def test_seed_is_complete_contiguous_and_keeps_unresolved_no_doi_entries(self):
        data = validate_manifest(copy.deepcopy(self.manifest))
        self.assertEqual(data['declared_count'], 34)
        self.assertEqual([entry['position'] for entry in data['entries']], list(range(1, 35)))
        self.assertTrue(all(entry['unresolved_identity'] for entry in data['entries']))
        self.assertTrue(all(entry['doi'] is None for entry in data['entries']))
        self.assertEqual(data['coverage'], 'source_complete')

    def test_import_resolves_private_ids_at_runtime_and_verifies_public_snapshot(self):
        calls = []
        source_id = 'a' * 64
        input_hash = 'b' * 64

        def service(operation, **kwargs):
            calls.append((operation, kwargs))
            if operation == 'packet':
                return {
                    'target': {
                        'record_id': self.manifest['candidate_id'],
                        'input_sha256': input_hash,
                    },
                    'sources': [{
                        'source_id': source_id,
                        'source_url': self.manifest['source_url'],
                        'evidence_kind': 'full_text',
                        'content_sha256': self.manifest['source_text_sha256'],
                        'version_label': self.manifest['version_label'],
                    }],
                }
            if operation == 'bibliography':
                payload = kwargs['bibliography']
                self.assertEqual(payload['source_id'], source_id)
                self.assertEqual(payload['input_sha256'], input_hash)
                self.assertEqual(payload['scope'], 'paper_bibliography')
                self.assertEqual(payload['coverage'], 'source_complete')
                self.assertEqual(payload['declared_count'], 34)
                return {'bibliography_id': 'c' * 64, 'replayed': False}
            raise AssertionError(operation)

        def public_readback(candidate_id):
            self.assertEqual(candidate_id, self.manifest['candidate_id'])
            return {
                'availability': 'registered',
                'bibliography': {
                    'scope': 'paper_bibliography',
                    'coverage': 'source_complete',
                    'declared_count': 34,
                    'entries_count': 34,
                    'revision': 'd' * 64,
                    'entries': self.manifest['entries'],
                    'next_offset': None,
                },
            }

        result = import_verified(copy.deepcopy(self.manifest), 'e' * 40, service=service, public_readback=public_readback)
        self.assertEqual([operation for operation, _ in calls], ['packet', 'bibliography'])
        self.assertEqual(result['status'], 'actual_bibliography_readback_verified')
        self.assertEqual(result['entries_count'], 34)
        self.assertTrue(result['public_projection_verified'])
        self.assertFalse(result['scientific_validation'])
        self.assertNotIn('source_id', result)
        self.assertNotIn('input_sha256', result)
        self.assertNotIn('bibliography_id', result)

    def test_import_fails_closed_on_wrong_retained_source_or_public_snapshot(self):
        def wrong_source(operation, **kwargs):
            if operation == 'packet':
                return {
                    'target': {'record_id': self.manifest['candidate_id'], 'input_sha256': 'b' * 64},
                    'sources': [],
                }
            raise AssertionError(operation)

        with self.assertRaisesRegex(RuntimeError, 'bibliography_retained_source_unavailable'):
            import_verified(copy.deepcopy(self.manifest), 'e' * 40, service=wrong_source, public_readback=lambda _: {})

        def service(operation, **kwargs):
            if operation == 'packet':
                return {
                    'target': {'record_id': self.manifest['candidate_id'], 'input_sha256': 'b' * 64},
                    'sources': [{
                        'source_id': 'a' * 64,
                        'source_url': self.manifest['source_url'],
                        'evidence_kind': 'full_text',
                        'content_sha256': self.manifest['source_text_sha256'],
                        'version_label': self.manifest['version_label'],
                    }],
                }
            if operation == 'bibliography':
                return {'bibliography_id': 'c' * 64, 'replayed': False}
            raise AssertionError(operation)

        with self.assertRaisesRegex(RuntimeError, 'bibliography_public_readback_failed'):
            import_verified(copy.deepcopy(self.manifest), 'e' * 40, service=service,
                            public_readback=lambda _: {'availability': 'registered', 'bibliography': None})

    def test_manifest_rejects_non_contiguous_positions_and_false_completeness(self):
        broken = copy.deepcopy(self.manifest)
        broken['entries'][1]['position'] = 99
        with self.assertRaisesRegex(RuntimeError, 'positions_not_contiguous'):
            validate_manifest(broken)
        broken = copy.deepcopy(self.manifest)
        broken['declared_count'] = 33
        with self.assertRaisesRegex(RuntimeError, 'count_conflict'):
            validate_manifest(broken)


if __name__ == '__main__':
    unittest.main()
