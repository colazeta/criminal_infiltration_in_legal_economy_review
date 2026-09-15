"""Persistence-bridge regressions; no source, model, secret or network access."""
import copy
import hashlib
import unittest

from scripts.calibration.full_text_proposal_persist import (
    persist_proposal,
    production_target_id,
    remap_proposal,
    retained_binding,
)


CANDIDATE = 'CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-002'
URL = 'https://docs.iza.org/dp13028.pdf'
COMMIT = 'a' * 40
PDF_SHA = 'b' * 64
TEXT = 'retained full text for synthetic persistence test'
TEXT_SHA = hashlib.sha256(TEXT.encode()).hexdigest()
INPUT_SHA = 'c' * 64


class FakeService:
    def __init__(self):
        self.target_id = production_target_id(CANDIDATE)
        self.target = {
            'target_id': self.target_id,
            'record_id': CANDIDATE,
            'input_sha256': INPUT_SHA,
        }
        self.sources = [{
            'source_id': 'production-source-id',
            'target_id': self.target_id,
            'input_sha256': INPUT_SHA,
            'evidence_kind': 'full_text',
            'source_url': URL,
            'content_sha256': TEXT_SHA,
            'text': TEXT,
        }]
        self.documents = [{
            'document_id': 'document-id',
            'source_url': URL,
            'pdf_sha256': PDF_SHA,
            'byte_length': 12345,
            'visibility': 'private',
        }]
        self.proposals = []

    def __call__(self, operation, **kwargs):
        self.assert_commit(kwargs)
        if operation == 'packet':
            return {'target': copy.deepcopy(self.target), 'sources': copy.deepcopy(self.sources)}
        if operation == 'documents':
            return {'documents': copy.deepcopy(self.documents)}
        if operation == 'document-check':
            return {
                'readable': True,
                'byte_length': 12345,
                'content_type': 'application/pdf',
                'etag': '"' + PDF_SHA + '"',
            }
        if operation == 'proposal':
            self.proposals.append(copy.deepcopy(kwargs['proposal']))
            return {'proposal_id': 'private-proposal-id', 'replayed': False, 'scientific_status': 'proposed'}
        raise AssertionError(operation)

    @staticmethod
    def assert_commit(kwargs):
        if kwargs.get('expected_commit') != COMMIT:
            raise AssertionError('unexpected commit')


def payload(input_sha=INPUT_SHA):
    proposal = {
        'target_id': 'calibration-target',
        'input_sha256': input_sha,
        'source_ids': ['calibration-source'],
        'spans': [
            {'id': 'span-1', 'source_id': 'calibration-source', 'locator': 'private calibration locator'},
            {'id': 'span-2', 'source_id': 'calibration-source', 'locator': 'private calibration locator 2'},
        ],
        'generated_by': {
            'agent': 'cile-fulltext-calibration-development-unvalidated',
            'model': 'fixed-model',
            'prompt_sha256': 'd' * 64,
        },
        'framework': {'status': 'insufficient_evidence'},
    }
    return {
        'status': 'structurally_valid_unreviewed',
        'source_url': URL,
        'pdf_sha256': PDF_SHA,
        'text_sha256': TEXT_SHA,
        'scientific_validation': False,
        'production_writes': 0,
        'proposal': proposal,
    }


class FullTextProposalPersistenceTests(unittest.TestCase):
    def binding(self, service=None):
        service = service or FakeService()
        return retained_binding(CANDIDATE, URL, PDF_SHA, TEXT_SHA, 'private', COMMIT, service), service

    def test_retained_binding_requires_exact_private_source_and_reader_hash(self):
        binding, service = self.binding()
        self.assertEqual(binding['target']['record_id'], CANDIDATE)
        self.assertEqual(binding['source']['content_sha256'], TEXT_SHA)
        self.assertEqual(binding['document']['visibility'], 'private')
        service.documents[0]['pdf_sha256'] = 'e' * 64
        with self.assertRaisesRegex(RuntimeError, 'fulltext_production_document_ambiguous'):
            self.binding(service)

    def test_ambiguous_retained_source_fails_closed(self):
        service = FakeService()
        service.sources.append(copy.deepcopy(service.sources[0]))
        with self.assertRaisesRegex(RuntimeError, 'fulltext_production_source_ambiguous'):
            self.binding(service)

    def test_reader_hash_mismatch_fails_closed(self):
        class BadReader(FakeService):
            def __call__(self, operation, **kwargs):
                result = super().__call__(operation, **kwargs)
                if operation == 'document-check':
                    result['etag'] = '"' + '0' * 64 + '"'
                return result
        with self.assertRaisesRegex(RuntimeError, 'fulltext_production_document_hash_mismatch'):
            self.binding(BadReader())

    def test_remap_changes_only_transport_identity(self):
        binding, _ = self.binding()
        original = payload()
        remapped = remap_proposal(original, binding)
        self.assertEqual(remapped['target_id'], binding['target']['target_id'])
        self.assertEqual(remapped['source_ids'], ['production-source-id'])
        self.assertTrue(all(span['source_id'] == 'production-source-id' for span in remapped['spans']))
        self.assertEqual(remapped['generated_by'], original['proposal']['generated_by'])
        self.assertEqual(remapped['framework'], original['proposal']['framework'])
        self.assertEqual(original['proposal']['target_id'], 'calibration-target')
        self.assertEqual(original['proposal']['source_ids'], ['calibration-source'])

    def test_stale_candidate_input_is_not_persisted(self):
        binding, service = self.binding()
        with self.assertRaisesRegex(RuntimeError, 'fulltext_production_input_stale'):
            persist_proposal(payload('f' * 64), binding, COMMIT, service)
        self.assertEqual(service.proposals, [])

    def test_mixed_calibration_source_spans_are_not_persisted(self):
        binding, service = self.binding()
        value = payload()
        value['proposal']['spans'][1]['source_id'] = 'other-source'
        with self.assertRaisesRegex(RuntimeError, 'fulltext_production_calibration_source_invalid'):
            persist_proposal(value, binding, COMMIT, service)
        self.assertEqual(service.proposals, [])

    def test_proposal_write_is_candidate_bound_and_returns_only_safe_receipt(self):
        binding, service = self.binding()
        receipt = persist_proposal(payload(), binding, COMMIT, service)
        self.assertEqual(receipt, {
            'candidate_id': CANDIDATE,
            'status': 'proposal_persisted_readback_verified',
            'replayed': False,
            'scientific_status': 'proposed',
            'scientific_validation': False,
            'accepted': False,
            'completed': False,
        })
        self.assertEqual(len(service.proposals), 1)
        stored = service.proposals[0]
        self.assertEqual(stored['target_id'], service.target_id)
        self.assertEqual(stored['input_sha256'], INPUT_SHA)
        self.assertNotIn(TEXT, str(receipt))
        self.assertNotIn('private-proposal-id', str(receipt))


if __name__ == '__main__':
    unittest.main()
