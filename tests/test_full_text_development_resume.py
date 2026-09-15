"""Private checkpoint resume tests; no source, model or network access."""
import json
import os
import unittest
from unittest.mock import patch

from scripts.calibration import full_text_development as development
from scripts.calibration import full_text_development_resume as resume


class FullTextDevelopmentResumeTests(unittest.TestCase):
    candidate = 'CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-002'

    def request(self, text='literal source evidence'):
        return {
            'messages': [
                {'role': 'system', 'content': 'synthetic'},
                {'role': 'user', 'content': json.dumps({'chunk_id': 'chunk-1', 'text': text}, separators=(',', ':'))},
            ],
            'temperature': 0, 'seed': 0, 'max_tokens': 10, 'stream': False,
            'response_format': {'type': 'json_object', 'schema': {'type': 'object'}},
        }

    def output(self, value='supported'):
        return {'atoms': [{
            'entity_type': 'global', 'entity_key': 'paper', 'field': 'summary',
            'value': value, 'evidence': 'literal source evidence',
        }]}

    def env(self):
        return patch.dict(os.environ, {
            'CURATOR_SESSION_SECRET': 'x' * 40,
            'GITHUB_SHA': 'a' * 40,
        }, clear=False)

    def test_cache_miss_persists_new_output_without_rewriting_request(self):
        request = self.request()
        expected_hash = development.sha(development.canonical(request))
        calls = []
        def service(operation, **kwargs):
            calls.append((operation, kwargs))
            if operation == 'development-checkpoint-get': return {'status': 'missing'}
            cp = kwargs['checkpoint']
            self.assertEqual(cp['request_sha256'], expected_hash)
            self.assertEqual(cp['output'], self.output())
            return {'status': 'stored', 'request_sha256': expected_hash, 'output_sha256': 'f' * 64}
        original_calls = []
        def original(payload, timeout):
            original_calls.append((payload, timeout))
            return self.output()
        with self.env(), patch.object(resume.runtime, 'runtime_extractor_fingerprint', return_value='b' * 64), \
                patch.object(resume.runtime, '_validate_original_atom_contracts'):
            result = resume.resumable_post(original, request, 300, service=service, candidate_id=self.candidate)
        self.assertEqual(result, self.output())
        self.assertEqual(original_calls, [(request, 600)])
        self.assertEqual([item[0] for item in calls], ['development-checkpoint-get', 'development-checkpoint-put'])

    def test_cache_hit_skips_local_model_call(self):
        request = self.request()
        expected_hash = development.sha(development.canonical(request))
        identity = {
            'protocol': resume.PROTOCOL, 'candidate_id': self.candidate,
            'extractor_fingerprint': 'b' * 64, 'request_sha256': expected_hash, 'chunk_id': 'chunk-1',
        }
        def service(operation, **kwargs):
            self.assertEqual(operation, 'development-checkpoint-get')
            return {'status': 'found', 'checkpoint': {**identity, 'output': self.output()}}
        with self.env(), patch.object(resume.runtime, 'runtime_extractor_fingerprint', return_value='b' * 64), \
                patch.object(resume.runtime, '_validate_original_atom_contracts'):
            result = resume.resumable_post(lambda *_: self.fail('model must not run'), request, 300,
                                           service=service, candidate_id=self.candidate)
        self.assertEqual(result, self.output())

    def test_changed_request_hash_does_not_share_checkpoint_identity(self):
        with patch.object(resume.runtime, 'runtime_extractor_fingerprint', return_value='b' * 64):
            first = resume.chunk_identity(self.request('first source'), self.candidate)
            second = resume.chunk_identity(self.request('second source'), self.candidate)
        self.assertNotEqual(first['request_sha256'], second['request_sha256'])
        self.assertEqual(first['extractor_fingerprint'], second['extractor_fingerprint'])

    def test_synthesis_is_not_cached(self):
        synthesis = {
            'messages': [{'role': 'system', 'content': 's'}, {'role': 'user', 'content': json.dumps({'evidence_atoms': []})}],
            'temperature': 0,
        }
        called = []
        def original(payload, timeout): called.append((payload, timeout)); return {'ok': True}
        with self.env():
            result = resume.resumable_post(original, synthesis, 420, service=lambda *_a, **_k: self.fail('no service'))
        self.assertEqual(result, {'ok': True})
        self.assertEqual(called, [(synthesis, 720)])

    def test_private_service_failure_fails_closed_instead_of_recomputing(self):
        with self.env(), patch.object(resume.runtime, 'runtime_extractor_fingerprint', return_value='b' * 64):
            with self.assertRaisesRegex(RuntimeError, 'fulltext_checkpoint_service_unavailable'):
                resume.resumable_post(lambda *_: self.fail('must not run'), self.request(), 300,
                                      service=lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError('transport')),
                                      candidate_id=self.candidate)

    def test_candidate_and_commit_guards_fail_closed(self):
        with self.assertRaisesRegex(RuntimeError, 'candidate_unavailable'):
            resume.candidate_id_from_argv(['script', '--candidate-id', 'bad'])
        with patch.dict(os.environ, {'GITHUB_SHA': 'bad'}, clear=False), self.assertRaisesRegex(RuntimeError, 'commit_unavailable'):
            resume.exact_commit()


if __name__ == '__main__':
    unittest.main()
