import base64
import unittest
from unittest.mock import patch
from scripts.enrichment.document_coverage import run, summarise


def row(candidate='CAND-TEST', **changes):
    return {'candidate_id': candidate, 'document_id': 'd', 'content_sha256': 'pdf',
            'acquisition_status': 'acquired', 'full_text_extraction_status': 'verified',
            'analysed': True, 'assessment_completed': None, 'validation_accepted': False,
            'redistribution_status': 'rights_unresolved', **changes}


class DocumentCoverageTests(unittest.TestCase):
    def test_versions_and_revocations_do_not_inflate_works_or_coverage(self):
        records = [row(), row(redistribution_status='public_rehost_allowed'),
                   row('CAND-MISSING', document_id=None, content_sha256=None,
                       acquisition_status='not_acquired', full_text_extraction_status='abstract_only',
                       analysed=False)]
        totals = summarise(records)
        self.assertEqual(totals['registered'], 2)
        self.assertEqual(totals['pdf_acquired'], 1)
        self.assertEqual(totals['full_text_verified'], 1)
        self.assertEqual(totals['publicly_rehostable'], 0)
        self.assertEqual(totals['full_text_missing'], 1)
        self.assertIsNone(totals['assessment_completed'])
        self.assertEqual(totals['validation_accepted'], 0)
        self.assertIsNone(totals['canonical_works'])

    def test_partial_inventory_never_presents_global_counts(self):
        def service(operation, **arguments):
            return {'protocol': 'CILE-DOCUMENT-COVERAGE-1', 'archive_commit': 'a'*40, 'identity_revision': 'b'*64,
                    'records': [row()], 'next_offset': 25}
        report = run('a'*40, service=service)
        self.assertFalse(report['complete_inventory'])
        self.assertIsNone(report['counts'])
        self.assertEqual(report['next_offset'], 25)

    def test_changed_legacy_text_is_an_explicit_blocker_and_never_rebound(self):
        calls = []
        def service(operation, **arguments):
            calls.append(operation)
            if operation == 'document-coverage':
                return {'protocol': 'CILE-DOCUMENT-COVERAGE-1', 'archive_commit': 'a'*40, 'identity_revision': 'b'*64,
                        'records': [row(full_text_extraction_status='pending')], 'next_offset': None}
            if operation == 'document-packet':
                return {'bytes_base64': base64.b64encode(b'test transport').decode(),
                        'text': 'Original immutable text', 'document': {'source_text_sha256': 'original'}}
            self.fail('Unexpected indexing mutation')
        with patch('scripts.enrichment.document_coverage.extract_document', return_value=('Changed text', {})):
            report = run('a'*40, reindex=True, service=service)
        self.assertEqual(calls, ['document-coverage', 'document-packet'])
        self.assertEqual(report['records'][0]['backfill_blocker'], 'document_legacy_extraction_differs')
