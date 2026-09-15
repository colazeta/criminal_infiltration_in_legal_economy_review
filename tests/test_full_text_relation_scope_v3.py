"""Relation-safe v4 synthesis regression tests; no source/model/network access."""
import json
import os
import unittest
from unittest.mock import patch

from scripts.calibration import full_text_development as development
from scripts.calibration import full_text_development_resume as resume
from scripts.calibration import full_text_development_run as runtime


class FullTextRelationScopeV4Tests(unittest.TestCase):
    candidate = 'CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-002'

    def setUp(self):
        resume.reset_relation_diagnostics()
        resume.reset_pass_state(None)

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

    @staticmethod
    def relation_synthesis(analysis_id='wrong', datasets=None):
        return {
            'analyses': [
                {'id': 'analysis-one', 'dataset_ids': ['dataset-one']},
                {'id': 'analysis-two', 'dataset_ids': ['dataset-two']},
            ],
            'variable_uses': [{
                'id': 'variable-one',
                'analysis_id': analysis_id,
                'dataset_ids': ['dataset-two'] if datasets is None else datasets,
            }],
        }

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

    def test_v4_fingerprint_changes_and_restores_runtime_contract(self):
        prior_fn = runtime.runtime_extractor_fingerprint
        prior_contract = runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA
        prior_value = runtime.runtime_extractor_fingerprint()
        state = resume.install_assignment_scope()
        try:
            self.assertEqual(runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA,
                             resume.SYNTHESIS_ATOM_SCOPED_SCHEMA)
            self.assertNotEqual(runtime.runtime_extractor_fingerprint(), prior_value)
            self.assertNotEqual(
                runtime.runtime_extractor_fingerprint(),
                resume.legacy_v3_extractor_fingerprint(),
            )
        finally:
            resume.restore_assignment_scope(state)
        self.assertIs(runtime.runtime_extractor_fingerprint, prior_fn)
        self.assertEqual(runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA, prior_contract)

    def test_exact_v3_chunk_hit_is_promoted_privately_before_reuse(self):
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
                legacy_v3_fp = resume.legacy_v3_extractor_fingerprint()
                current = {
                    'protocol': resume.PROTOCOL,
                    'candidate_id': self.candidate,
                    'extractor_fingerprint': current_fp,
                    'request_sha256': request_hash,
                    'chunk_id': 'chunk-1',
                }
                legacy = {**current, 'extractor_fingerprint': legacy_v3_fp}

                def service(operation, **kwargs):
                    calls.append((operation, kwargs['checkpoint']['extractor_fingerprint']))
                    cp = kwargs['checkpoint']
                    if operation == 'development-checkpoint-get' and cp['extractor_fingerprint'] == current_fp:
                        return {'status': 'missing'}
                    if operation == 'development-checkpoint-get' and cp['extractor_fingerprint'] == legacy_v3_fp:
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
             ('development-checkpoint-get', legacy_v3_fp),
             ('development-checkpoint-put', current_fp)],
        )
        self.assertEqual(resume.PASS_STATE['reused_chunks'], 1)
        self.assertEqual(resume.PASS_STATE['new_chunks'], 0)

    def test_exact_v2_chunk_hit_is_fallback_after_v3_miss(self):
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
                legacy_v3_fp = resume.legacy_v3_extractor_fingerprint()
                legacy_v2_fp = resume.legacy_v2_extractor_fingerprint()
                current = {
                    'protocol': resume.PROTOCOL,
                    'candidate_id': self.candidate,
                    'extractor_fingerprint': current_fp,
                    'request_sha256': request_hash,
                    'chunk_id': 'chunk-1',
                }
                legacy_v2 = {**current, 'extractor_fingerprint': legacy_v2_fp}

                def service(operation, **kwargs):
                    calls.append((operation, kwargs['checkpoint']['extractor_fingerprint']))
                    cp = kwargs['checkpoint']
                    if operation == 'development-checkpoint-get' and cp['extractor_fingerprint'] in {current_fp, legacy_v3_fp}:
                        return {'status': 'missing'}
                    if operation == 'development-checkpoint-get' and cp['extractor_fingerprint'] == legacy_v2_fp:
                        return {'status': 'found', 'checkpoint': {**legacy_v2, 'output': self.output()}}
                    if operation == 'development-checkpoint-put':
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
             ('development-checkpoint-get', legacy_v3_fp),
             ('development-checkpoint-get', legacy_v2_fp),
             ('development-checkpoint-put', current_fp)],
        )
        self.assertEqual(resume.PASS_STATE['reused_chunks'], 1)
        self.assertEqual(resume.PASS_STATE['new_chunks'], 0)

    def test_variable_analysis_relation_is_normalised_only_when_uniquely_implied(self):
        synthesis = self.relation_synthesis()
        repaired, changes = resume._normalise_variable_analysis_relations(synthesis)
        self.assertEqual(synthesis['variable_uses'][0]['analysis_id'], 'wrong')
        self.assertEqual(repaired['variable_uses'][0]['analysis_id'], 'analysis-two')
        self.assertEqual(repaired['variable_uses'][0]['dataset_ids'], ['dataset-two'])
        self.assertEqual(changes, [{
            'variable_index': 0,
            'dataset_count': 1,
            'prior_analysis_known': False,
        }])

    def test_valid_variable_relation_is_not_rewritten(self):
        synthesis = self.relation_synthesis(analysis_id='analysis-two')
        with self.assertRaisesRegex(ValueError, 'fulltext_variable_relation_unresolved'):
            resume._normalise_variable_analysis_relations(synthesis)
        self.assertEqual(synthesis['variable_uses'][0]['analysis_id'], 'analysis-two')

    def test_ambiguous_or_unsupported_variable_relation_fails_closed(self):
        ambiguous = {
            'analyses': [
                {'id': 'analysis-one', 'dataset_ids': ['dataset-one']},
                {'id': 'analysis-two', 'dataset_ids': ['dataset-one']},
            ],
            'variable_uses': [{
                'id': 'variable-one', 'analysis_id': 'wrong',
                'dataset_ids': ['dataset-one'],
            }],
        }
        with self.assertRaisesRegex(ValueError, 'fulltext_variable_relation_unresolved'):
            resume._normalise_variable_analysis_relations(ambiguous)
        with self.assertRaisesRegex(ValueError, 'fulltext_variable_relation_unresolved'):
            resume._normalise_variable_analysis_relations(
                self.relation_synthesis(datasets=['missing-dataset'])
            )
        with self.assertRaisesRegex(ValueError, 'fulltext_variable_relation_unresolved'):
            resume._normalise_variable_analysis_relations(
                self.relation_synthesis(datasets=[])
            )

    def test_build_proposal_retries_once_with_only_the_unique_relation_change(self):
        synthesis = self.relation_synthesis()
        seen = []

        def base_builder(_target, _source, _atoms, graph):
            seen.append(json.loads(json.dumps(graph)))
            if len(seen) == 1:
                raise ValueError('fulltext_variable_relation')
            return {'status': 'synthetic-valid'}

        with patch.object(resume, '_ORIGINAL_BUILD_PROPOSAL', side_effect=base_builder):
            result = resume.relation_normalising_build_proposal({}, {}, [], synthesis)

        self.assertEqual(result, {'status': 'synthetic-valid'})
        self.assertEqual(seen[0]['variable_uses'][0]['analysis_id'], 'wrong')
        self.assertEqual(seen[1]['variable_uses'][0]['analysis_id'], 'analysis-two')
        self.assertEqual(synthesis['variable_uses'][0]['analysis_id'], 'analysis-two')
        self.assertEqual(resume.RELATION_DIAGNOSTICS['normalised_variable_relations'], 1)

    def test_checkpoint_diagnostics_expose_no_record_ids(self):
        synthesis = self.relation_synthesis()
        with patch.object(
            resume, '_ORIGINAL_BUILD_PROPOSAL',
            side_effect=[ValueError('fulltext_variable_relation'), {'ok': True}],
        ):
            resume.relation_normalising_build_proposal({}, {}, [], synthesis)
        payload = resume.relation_checkpoint_payload({'status': 'synthetic'})
        diagnostics = payload['runtime_relation_normalisation']
        self.assertEqual(diagnostics['policy'], resume.RELATION_NORMALISATION_POLICY)
        self.assertEqual(diagnostics['normalised_variable_relations'], 1)
        serialised = json.dumps(diagnostics, sort_keys=True)
        self.assertNotIn('analysis-two', serialised)
        self.assertNotIn('variable-one', serialised)
        self.assertNotIn('dataset-two', serialised)


if __name__ == '__main__':
    unittest.main()
