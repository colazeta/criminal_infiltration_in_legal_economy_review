"""Relation-safe v3 synthesis regression tests; no source/model/network access."""
import json
import os
import unittest
from unittest.mock import patch

from scripts.calibration import full_text_development as development
from scripts.calibration import full_text_development_resume as resume
from scripts.calibration import full_text_development_run as runtime


class FullTextRelationScopeV3Tests(unittest.TestCase):
    candidate = 'CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-002'

    def atoms(self):
        return [
            {'id': 'atom-study', 'entity_type': 'study', 'entity_key': 's1',
             'field': 'study_type', 'value': 'study',
             'span': {'id': 'span-study', 'start_offset': 0, 'end_offset': 1}},
            {'id': 'atom-analysis', 'entity_type': 'analysis', 'entity_key': 'a1',
             'field': 'method', 'value': 'method',
             'span': {'id': 'span-analysis', 'start_offset': 2, 'end_offset': 3}},
            {'id': 'atom-variable', 'entity_type': 'variable_use', 'entity_key': 'v1',
             'field': 'concept', 'value': 'concept',
             'span': {'id': 'span-variable', 'start_offset': 4, 'end_offset': 5}},
            {'id': 'atom-finding', 'entity_type': 'finding', 'entity_key': 'f1',
             'field': 'statement', 'value': 'finding',
             'span': {'id': 'span-finding', 'start_offset': 6, 'end_offset': 7}},
        ]

    def request(self):
        return {
            'messages': [
                {'role': 'system', 'content': 'synthetic'},
                {'role': 'user', 'content': json.dumps(
                    {'chunk_id': 'chunk-1', 'text': 'literal source evidence'},
                    separators=(',', ':'),
                )},
            ],
            'temperature': 0, 'seed': 0, 'max_tokens': 10, 'stream': False,
            'response_format': {'type': 'json_object', 'schema': {'type': 'object'}},
        }

    @staticmethod
    def output():
        return {'atoms': [{
            'entity_type': 'global', 'entity_key': 'paper', 'field': 'summary',
            'value': 'supported', 'evidence': 'literal source evidence',
        }]}

    def test_relation_arrays_are_decoder_unique_and_prompt_is_bound(self):
        schema = resume.atom_scoped_synthesis_schema(self.atoms())['properties']
        self.assertTrue(schema['analyses']['items']['properties']['dataset_ids']['uniqueItems'])
        self.assertTrue(schema['variable_uses']['items']['properties']['dataset_ids']['uniqueItems'])
        self.assertTrue(schema['findings']['items']['properties']['variable_use_ids']['uniqueItems'])

        request = resume.atom_scoped_bounded_synthesis_request(self.atoms())
        self.assertIn(resume.RELATION_CONSISTENCY_SUFFIX, request['messages'][0]['content'])
        self.assertEqual(
            request['response_format']['schema'],
            resume.atom_scoped_synthesis_schema(self.atoms()),
        )

    def test_v3_fingerprint_changes_and_restores_runtime_contract(self):
        prior_fn = runtime.runtime_extractor_fingerprint
        prior_contract = runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA
        prior_value = runtime.runtime_extractor_fingerprint()
        state = resume.install_assignment_scope()
        try:
            self.assertEqual(runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA,
                             resume.SYNTHESIS_ATOM_SCOPED_SCHEMA)
            self.assertNotEqual(runtime.runtime_extractor_fingerprint(), prior_value)
        finally:
            resume.restore_assignment_scope(state)
        self.assertIs(runtime.runtime_extractor_fingerprint, prior_fn)
        self.assertEqual(runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA, prior_contract)

    def test_exact_v2_chunk_hit_is_promoted_privately_before_reuse(self):
        resume.reset_pass_state(None)
        request = self.request()
        request_hash = development.sha(development.canonical(request))
        calls = []
        with patch.dict(os.environ, {
            'CURATOR_SESSION_SECRET': 'x' * 40,
            'CALIBRATION_CHECKPOINT_SERVICE_COMMIT': 'a' * 40,
        }, clear=False), patch.object(runtime, '_validate_original_atom_contracts'):
            state = resume.install_assignment_scope()
            try:
                current_fp = runtime.runtime_extractor_fingerprint()
                legacy_fp = resume.legacy_v2_extractor_fingerprint()
                current = {
                    'protocol': resume.PROTOCOL,
                    'candidate_id': self.candidate,
                    'extractor_fingerprint': current_fp,
                    'request_sha256': request_hash,
                    'chunk_id': 'chunk-1',
                }
                legacy = {**current, 'extractor_fingerprint': legacy_fp}

                def service(operation, **kwargs):
                    calls.append((operation, kwargs['checkpoint']['extractor_fingerprint']))
                    cp = kwargs['checkpoint']
                    if operation == 'development-checkpoint-get' and cp['extractor_fingerprint'] == current_fp:
                        return {'status': 'missing'}
                    if operation == 'development-checkpoint-get' and cp['extractor_fingerprint'] == legacy_fp:
                        return {'status': 'found', 'checkpoint': {**legacy, 'output': self.output()}}
                    if operation == 'development-checkpoint-put':
                        self.assertEqual(cp['extractor_fingerprint'], current_fp)
                        return {'status': 'stored', 'request_sha256': request_hash,
                                'output_sha256': 'f' * 64}
                    self.fail('unexpected private checkpoint operation')

                result = resume.resumable_post(
                    lambda *_args, **_kwargs: self.fail('model must not rerun'),
                    request, 300, service=service, candidate_id=self.candidate,
                )
            finally:
                resume.restore_assignment_scope(state)

        self.assertEqual(result, self.output())
        self.assertEqual(
            calls,
            [('development-checkpoint-get', current_fp),
             ('development-checkpoint-get', legacy_fp),
             ('development-checkpoint-put', current_fp)],
        )
        self.assertEqual(resume.PASS_STATE['reused_chunks'], 1)
        self.assertEqual(resume.PASS_STATE['new_chunks'], 0)


if __name__ == '__main__':
    unittest.main()
