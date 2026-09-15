"""Private checkpoint resume tests; no source, model or network access."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.calibration import full_text_development as development
from scripts.calibration import full_text_development_resume as resume


class FullTextDevelopmentResumeTests(unittest.TestCase):
    candidate = 'CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-002'

    def setUp(self):
        resume.reset_pass_state(None)

    def request(self, text='literal source evidence', chunk_id='chunk-1'):
        return {
            'messages': [
                {'role': 'system', 'content': 'synthetic'},
                {'role': 'user', 'content': json.dumps({'chunk_id': chunk_id, 'text': text}, separators=(',', ':'))},
            ],
            'temperature': 0, 'seed': 0, 'max_tokens': 10, 'stream': False,
            'response_format': {'type': 'json_object', 'schema': {'type': 'object'}},
        }

    def output(self, value='supported'):
        return {'atoms': [{
            'entity_type': 'global', 'entity_key': 'paper', 'field': 'summary',
            'value': value, 'evidence': 'literal source evidence',
        }]}

    def env(self, **extra):
        values = {
            'CURATOR_SESSION_SECRET': 'x' * 40,
            'CALIBRATION_CHECKPOINT_SERVICE_COMMIT': 'a' * 40,
            **extra,
        }
        return patch.dict(os.environ, values, clear=False)

    def test_cache_miss_persists_new_output_without_rewriting_request(self):
        request = self.request()
        expected_hash = development.sha(development.canonical(request))
        calls = []
        def service(operation, **kwargs):
            calls.append((operation, kwargs))
            self.assertEqual(kwargs['expected_commit'], 'a' * 40)
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
        self.assertEqual(resume.PASS_STATE['new_chunks'], 1)

    def test_cache_hit_skips_local_model_call(self):
        request = self.request()
        expected_hash = development.sha(development.canonical(request))
        identity = {
            'protocol': resume.PROTOCOL, 'candidate_id': self.candidate,
            'extractor_fingerprint': 'b' * 64, 'request_sha256': expected_hash, 'chunk_id': 'chunk-1',
        }
        def service(operation, **kwargs):
            self.assertEqual(operation, 'development-checkpoint-get')
            self.assertEqual(kwargs['expected_commit'], 'a' * 40)
            return {'status': 'found', 'checkpoint': {**identity, 'output': self.output()}}
        with self.env(), patch.object(resume.runtime, 'runtime_extractor_fingerprint', return_value='b' * 64), \
                patch.object(resume.runtime, '_validate_original_atom_contracts'):
            result = resume.resumable_post(lambda *_: self.fail('model must not run'), request, 300,
                                           service=service, candidate_id=self.candidate)
        self.assertEqual(result, self.output())
        self.assertEqual(resume.PASS_STATE['reused_chunks'], 1)
        self.assertEqual(resume.PASS_STATE['new_chunks'], 0)

    def test_pass_budget_stops_before_an_uncheckpointed_model_call(self):
        resume.reset_pass_state(1)
        original_calls = []
        def original(payload, timeout):
            original_calls.append((payload, timeout))
            return self.output()
        def service(operation, **kwargs):
            if operation == 'development-checkpoint-get':
                return {'status': 'missing'}
            identity = kwargs['checkpoint']
            return {'status': 'stored', 'request_sha256': identity['request_sha256'], 'output_sha256': 'f' * 64}
        with self.env(), patch.object(resume.runtime, 'runtime_extractor_fingerprint', return_value='b' * 64), \
                patch.object(resume.runtime, '_validate_original_atom_contracts'):
            resume.resumable_post(original, self.request(chunk_id='chunk-1'), 300,
                                  service=service, candidate_id=self.candidate)
            with self.assertRaisesRegex(RuntimeError, 'fulltext_checkpoint_pass_budget_exhausted'):
                resume.resumable_post(original, self.request(chunk_id='chunk-2'), 300,
                                      service=service, candidate_id=self.candidate)
        self.assertEqual(len(original_calls), 1)
        self.assertEqual(resume.PASS_STATE['new_chunks'], 1)

    def test_reused_chunk_does_not_consume_new_chunk_budget(self):
        resume.reset_pass_state(1)
        first = self.request(chunk_id='chunk-1')
        second = self.request(chunk_id='chunk-2')
        first_hash = development.sha(development.canonical(first))
        first_identity = {
            'protocol': resume.PROTOCOL, 'candidate_id': self.candidate,
            'extractor_fingerprint': 'b' * 64, 'request_sha256': first_hash, 'chunk_id': 'chunk-1',
        }
        original_calls = []
        def original(payload, timeout):
            original_calls.append((payload, timeout))
            return self.output()
        def service(operation, **kwargs):
            identity = kwargs['checkpoint']
            if operation == 'development-checkpoint-get' and identity['chunk_id'] == 'chunk-1':
                return {'status': 'found', 'checkpoint': {**first_identity, 'output': self.output()}}
            if operation == 'development-checkpoint-get':
                return {'status': 'missing'}
            return {'status': 'stored', 'request_sha256': identity['request_sha256'], 'output_sha256': 'f' * 64}
        with self.env(), patch.object(resume.runtime, 'runtime_extractor_fingerprint', return_value='b' * 64), \
                patch.object(resume.runtime, '_validate_original_atom_contracts'):
            resume.resumable_post(original, first, 300, service=service, candidate_id=self.candidate)
            resume.resumable_post(original, second, 300, service=service, candidate_id=self.candidate)
        self.assertEqual(len(original_calls), 1)
        self.assertEqual(resume.PASS_STATE['reused_chunks'], 1)
        self.assertEqual(resume.PASS_STATE['new_chunks'], 1)

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
        self.assertEqual(called, [(synthesis, 1800)])

    def test_private_service_failure_fails_closed_instead_of_recomputing(self):
        with self.env(), patch.object(resume.runtime, 'runtime_extractor_fingerprint', return_value='b' * 64):
            with self.assertRaisesRegex(RuntimeError, 'fulltext_checkpoint_service_unavailable'):
                resume.resumable_post(lambda *_: self.fail('must not run'), self.request(), 300,
                                      service=lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError('transport')),
                                      candidate_id=self.candidate)

    def test_checkpoint_collision_fails_closed(self):
        def service(operation, **kwargs):
            if operation == 'development-checkpoint-get':
                return {'status': 'missing'}
            raise RuntimeError('development_checkpoint_conflict')
        with self.env(), patch.object(resume.runtime, 'runtime_extractor_fingerprint', return_value='b' * 64), \
                patch.object(resume.runtime, '_validate_original_atom_contracts'):
            with self.assertRaisesRegex(RuntimeError, 'fulltext_checkpoint_conflict'):
                resume.resumable_post(lambda *_args, **_kwargs: self.output(), self.request(), 300,
                                      service=service, candidate_id=self.candidate)

    def test_candidate_service_commit_and_pass_guards_fail_closed(self):
        with self.assertRaisesRegex(RuntimeError, 'candidate_unavailable'):
            resume.candidate_id_from_argv(['script', '--candidate-id', 'bad'])
        with patch.dict(os.environ, {'CALIBRATION_CHECKPOINT_SERVICE_COMMIT': 'bad'}, clear=False), self.assertRaisesRegex(RuntimeError, 'service_commit_unavailable'):
            resume.checkpoint_service_commit()
        with patch.dict(os.environ, {'FULLTEXT_MAX_NEW_CHUNKS': '0'}, clear=False), self.assertRaisesRegex(RuntimeError, 'pass_limit_invalid'):
            resume.pass_limit()
        with patch.dict(os.environ, {'FULLTEXT_REQUIRE_COMPLETE': 'yes'}, clear=False), self.assertRaisesRegex(RuntimeError, 'pass_completion_invalid'):
            resume.pass_requires_complete()

    def test_partial_pass_is_successful_only_after_budget_exhaustion_and_writes_no_source(self):
        with tempfile.TemporaryDirectory() as directory:
            status_file = Path(directory) / 'status.txt'
            with self.env(FULLTEXT_MAX_NEW_CHUNKS='3', FULLTEXT_REQUIRE_COMPLETE='0',
                          FULLTEXT_PASS_STATUS_FILE=str(status_file)), \
                    patch.object(resume.runtime, 'main', side_effect=RuntimeError('fulltext_checkpoint_pass_budget_exhausted')):
                resume.main()
            self.assertEqual(status_file.read_text(encoding='utf-8'), 'partial\n')
            self.assertNotIn('literal source evidence', status_file.read_text(encoding='utf-8'))

    def test_final_pass_fails_if_budget_is_still_exhausted(self):
        with tempfile.TemporaryDirectory() as directory:
            status_file = Path(directory) / 'status.txt'
            with self.env(FULLTEXT_MAX_NEW_CHUNKS='3', FULLTEXT_REQUIRE_COMPLETE='1',
                          FULLTEXT_PASS_STATUS_FILE=str(status_file)), \
                    patch.object(resume.runtime, 'main', side_effect=RuntimeError('fulltext_checkpoint_pass_budget_exhausted')):
                with self.assertRaisesRegex(RuntimeError, 'fulltext_checkpoint_pass_budget_exhausted'):
                    resume.main()
            self.assertEqual(status_file.read_text(encoding='utf-8'), 'incomplete\n')

    def test_development_workflow_scopes_private_secret_and_chains_bounded_passes(self):
        workflow = Path('.github/workflows/fulltext-calibration-source.yml').read_text(encoding='utf-8')
        development_job = workflow.split('\n  development:\n', 1)[1]
        header = development_job.split('\n    steps:\n', 1)[0]
        self.assertIn('    environment: curator-production\n', header)
        self.assertIn('CURATOR_SESSION_SECRET: ${{ secrets.CURATOR_SESSION_SECRET }}', development_job)
        self.assertEqual(workflow.count("FULLTEXT_MAX_NEW_CHUNKS: '3'"), 5)
        self.assertEqual(workflow.count('environment: curator-production'), 5)
        self.assertIn('  development-2:', workflow)
        self.assertIn('  development-3:', workflow)
        self.assertIn('  development-4:', workflow)
        self.assertIn('  development-5:', workflow)
        self.assertIn("FULLTEXT_REQUIRE_COMPLETE: '1'", workflow.split('\n  development-5:\n', 1)[1])
        self.assertNotIn('timeout-minutes: 71', workflow)


if __name__ == '__main__':
    unittest.main()
