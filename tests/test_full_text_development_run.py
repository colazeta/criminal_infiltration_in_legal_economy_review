"""Runtime-budget tests only; no model, source or network access."""
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.calibration import full_text_development as development
from scripts.calibration import full_text_development_run as runtime
from scripts.calibration.full_text_development_run import (
    EVIDENCE_REJECTION_POLICY,
    EVIDENCE_UNIQUENESS_SUFFIX,
    FIELD_SCOPED_ATOM_SCHEMA,
    SYNTHESIS_FIELD_SCOPED_SCHEMA,
    RUNTIME_CHECKPOINT,
    RUNTIME_DIAGNOSTICS,
    SCIENTIFIC_CONFIG,
    bounded_chunk_request,
    bounded_synthesis_request,
    field_scoped_atom_schema,
    field_scoped_synthesis_schema,
    runtime_checkpoint_payload,
    runtime_chunk_system,
    runtime_extractor_fingerprint,
    runtime_post,
    runtime_resolve_atoms,
    runtime_timeout,
)


class FullTextDevelopmentRuntimeTests(unittest.TestCase):
    def setUp(self):
        RUNTIME_DIAGNOSTICS.update({
            'nonliteral_atoms_omitted': 0,
            'ambiguous_atoms_omitted': 0,
            'omission_digest': development.sha(development.canonical([])),
        })
        RUNTIME_CHECKPOINT.update({'output': None, 'payload': None})

    def test_operational_timeout_extension_is_bounded_and_monotone(self):
        self.assertEqual(runtime_timeout(300), 600)
        self.assertEqual(runtime_timeout(420), 720)
        self.assertEqual(runtime_timeout(900), 900)
        with self.assertRaisesRegex(ValueError, 'runtime_timeout_invalid'):
            runtime_timeout(0)

    def test_timeout_is_classified_without_changing_payload(self):
        payload = {'unchanged': True}
        seen = {}

        def timed_out(value, timeout):
            seen['payload'] = value
            seen['timeout'] = timeout
            raise TimeoutError()

        with self.assertRaisesRegex(RuntimeError, 'fulltext_model_timeout'):
            runtime_post(timed_out, payload, 300)
        self.assertIs(seen['payload'], payload)
        self.assertEqual(seen['timeout'], 600)

    def test_bounded_scientific_runtime_has_stable_explicit_fingerprint(self):
        self.assertEqual(SCIENTIFIC_CONFIG['chunk_chars'], 6000)
        self.assertEqual(SCIENTIFIC_CONFIG['chunk_overlap'], 400)
        self.assertEqual(SCIENTIFIC_CONFIG['max_atoms_per_chunk'], 8)
        self.assertEqual(SCIENTIFIC_CONFIG['chunk_max_tokens'], 1600)
        self.assertEqual(FIELD_SCOPED_ATOM_SCHEMA, 'entity-field-paired-oneof-v1')
        self.assertEqual(SYNTHESIS_FIELD_SCOPED_SCHEMA, 'destination-field-scoped-assignments-v1')
        fingerprint = runtime_extractor_fingerprint()
        self.assertRegex(fingerprint, r'^[0-9a-f]{64}$')
        self.assertEqual(fingerprint, runtime_extractor_fingerprint())
        self.assertNotEqual(fingerprint, development.extractor_fingerprint())

    def test_chunk_request_expands_output_budget_and_requires_unique_literal_evidence(self):
        chunk = {'id': 'chunk-1', 'text': 'Synthetic source evidence ' * 60}
        request = bounded_chunk_request(chunk)
        self.assertEqual(request['max_tokens'], 1600)
        supplied = request['messages'][1]['content']
        self.assertIn('Synthetic source evidence', supplied)
        system = request['messages'][0]['content']
        self.assertIn(EVIDENCE_UNIQUENESS_SUFFIX, system)
        self.assertIn('occurs exactly once', system)
        self.assertIn('extend it with exact contiguous surrounding source words', system)
        self.assertIn('omit the atom', system)
        self.assertEqual(system, runtime_chunk_system() + system[len(runtime_chunk_system()):])
        self.assertEqual(request['temperature'], 0)
        self.assertEqual(request['seed'], 0)
        self.assertEqual(SCIENTIFIC_CONFIG['chunk_chars'], 6000)
        self.assertEqual(SCIENTIFIC_CONFIG['max_atoms_per_chunk'], 8)

    def test_decoder_schema_pairs_each_entity_with_only_its_governed_fields(self):
        schema = field_scoped_atom_schema()
        branches = schema['properties']['atoms']['items']['oneOf']
        self.assertEqual(len(branches), len(development.FIELD_BY_ENTITY))
        by_entity = {
            branch['properties']['entity_type']['const']: set(branch['properties']['field']['enum'])
            for branch in branches
        }
        self.assertEqual(by_entity, {key: set(value) for key, value in development.FIELD_BY_ENTITY.items()})
        self.assertIn('summary', by_entity['global'])
        self.assertNotIn('method', by_entity['global'])
        self.assertIn('method', by_entity['analysis'])
        self.assertNotIn('summary', by_entity['analysis'])
        request_schema = bounded_chunk_request({'id': 'chunk-1', 'text': 'bounded source ' * 100})['response_format']['schema']
        self.assertEqual(request_schema, schema)
        self.assertIs(development.atom_schema, runtime._ORIGINAL_ATOM_SCHEMA)

    def test_synthesis_decoder_scopes_assignment_fields_to_destination_group(self):
        schema = field_scoped_synthesis_schema()
        props = schema['properties']
        self.assertEqual(
            set(props['global_fields']['items']['properties']['field']['enum']),
            set(development.GLOBAL_FIELDS),
        )
        group_kinds = {
            'studies': 'study', 'datasets': 'dataset', 'analyses': 'analysis',
            'variable_uses': 'variable_use', 'findings': 'finding',
        }
        for group, kind in group_kinds.items():
            field_schema = props[group]['items']['properties']['fields']['items']['properties']['field']
            self.assertEqual(set(field_schema['enum']), set(development.FIELD_BY_ENTITY[kind]))
        self.assertNotIn(
            'method', props['global_fields']['items']['properties']['field']['enum'],
        )
        self.assertNotIn(
            'summary', props['analyses']['items']['properties']['fields']['items']['properties']['field']['enum'],
        )

    def test_bounded_synthesis_request_uses_scoped_schema_without_mutating_base_module(self):
        atoms = [{
            'id': 'atom-1', 'entity_type': 'analysis', 'entity_key': 'a',
            'field': 'method', 'value': 'Method',
            'span': {'id': 'span-1', 'start_offset': 0, 'end_offset': 1},
        }]
        request = bounded_synthesis_request(atoms)
        self.assertEqual(request['max_tokens'], SCIENTIFIC_CONFIG['synthesis_max_tokens'])
        self.assertEqual(request['response_format']['schema'], field_scoped_synthesis_schema())
        self.assertIs(development.synthesis_schema, runtime._ORIGINAL_SYNTHESIS_SCHEMA)

    def test_base_builder_still_rejects_wrong_destination_field(self):
        atoms = [{
            'id': 'atom-1', 'entity_type': 'analysis', 'entity_key': 'a',
            'field': 'method', 'value': 'Method',
            'span': {'id': 'span-1', 'start_offset': 0, 'end_offset': 1},
        }]
        synthesis = {
            'global_fields': [{'field': 'method', 'value': 'Wrong destination', 'atom_ids': ['atom-1']}],
            'studies': [], 'datasets': [], 'analyses': [], 'variable_uses': [], 'findings': [],
            'framework': {'status': 'insufficient_evidence', 'primary': None, 'rationale': None,
                          'secondary': [], 'alternative': None},
        }
        with self.assertRaisesRegex(ValueError, 'assignment_field'):
            development.build_proposal(
                {'target_id': 't', 'input_sha256': 'a' * 64}, {'source_id': 's'}, atoms, synthesis
            )

    def test_ambiguous_repeated_evidence_is_still_rejected_by_base_validator(self):
        text = 'start ' + ('x' * 1200) + ' repeated evidence middle repeated evidence ' + ('y' * 1200)
        chunks = development.chunk_source(text)
        outputs = []
        for chunk in chunks:
            atoms = []
            if 'repeated evidence' in chunk['text']:
                atoms.append({
                    'entity_type': 'global', 'entity_key': 'paper',
                    'field': 'research_question', 'value': 'Synthetic question',
                    'evidence': 'repeated evidence',
                })
            outputs.append({'atoms': atoms})
        with self.assertRaisesRegex(ValueError, 'ambiguous_evidence'):
            development.resolve_atoms(chunks, outputs)

    def _prime_checkpoint(self):
        RUNTIME_CHECKPOINT.update({
            'output': Path('/tmp/non-secret-test-checkpoint'),
            'payload': {'status': 'chunk_extraction_in_progress', 'chunks_completed': 1},
        })

    def test_runtime_omits_only_nonliteral_or_nonunique_atoms_and_preserves_unique_atoms(self):
        chunk = {
            'id': 'chunk-1', 'start': 0, 'utf16_start': 0,
            'text': 'unique evidence then repeated evidence and repeated evidence end',
        }
        outputs = [{'atoms': [
            {
                'entity_type': 'global', 'entity_key': 'paper',
                'field': 'research_question', 'value': 'Unique supported question',
                'evidence': 'unique evidence',
            },
            {
                'entity_type': 'global', 'entity_key': 'paper',
                'field': 'contribution', 'value': 'Ambiguous contribution',
                'evidence': 'repeated evidence',
            },
            {
                'entity_type': 'global', 'entity_key': 'paper',
                'field': 'summary', 'value': 'Unsupported summary',
                'evidence': 'not present in source',
            },
        ]}]
        self._prime_checkpoint()
        persisted = []
        with patch.object(runtime, '_ORIGINAL_CHECKPOINT', side_effect=lambda output, payload: persisted.append((output, payload))):
            atoms = runtime_resolve_atoms([chunk], outputs)
        self.assertEqual(len(atoms), 1)
        self.assertEqual(atoms[0]['field'], 'research_question')
        self.assertEqual(RUNTIME_DIAGNOSTICS['ambiguous_atoms_omitted'], 1)
        self.assertEqual(RUNTIME_DIAGNOSTICS['nonliteral_atoms_omitted'], 1)
        self.assertRegex(RUNTIME_DIAGNOSTICS['omission_digest'], r'^[0-9a-f]{64}$')
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0][1]['status'], 'evidence_resolution_complete_model_pending')
        self.assertEqual(persisted[0][1]['runtime_evidence_rejections']['ambiguous_atoms_omitted'], 1)
        self.assertEqual(persisted[0][1]['runtime_evidence_rejections']['nonliteral_atoms_omitted'], 1)

    def test_runtime_does_not_hide_malformed_atoms(self):
        chunk = {'id': 'chunk-1', 'start': 0, 'utf16_start': 0, 'text': 'literal evidence'}
        malformed = {'atoms': [{'entity_type': 'global', 'field': 'summary', 'value': 'x', 'evidence': 'literal evidence'}]}
        with self.assertRaisesRegex(ValueError, 'atom_shape'):
            runtime_resolve_atoms([chunk], [malformed])

    def test_runtime_validates_field_scope_before_evidence_filtering(self):
        chunk = {'id': 'chunk-1', 'start': 0, 'utf16_start': 0, 'text': 'repeated evidence repeated evidence'}
        invalid = {'atoms': [{
            'entity_type': 'global', 'entity_key': 'paper', 'field': 'method',
            'value': 'Invalid global method', 'evidence': 'repeated evidence',
        }]}
        with self.assertRaisesRegex(ValueError, 'atom_field_scope'):
            runtime_resolve_atoms([chunk], [invalid])
        self.assertEqual(RUNTIME_DIAGNOSTICS['ambiguous_atoms_omitted'], 0)

    def test_runtime_validates_atom_limit_before_evidence_filtering(self):
        chunk = {'id': 'chunk-1', 'start': 0, 'utf16_start': 0, 'text': 'repeated evidence repeated evidence'}
        atom = {
            'entity_type': 'global', 'entity_key': 'paper', 'field': 'summary',
            'value': 'Repeated', 'evidence': 'repeated evidence',
        }
        outputs = [{'atoms': [dict(atom) for _ in range(development.MAX_ATOMS_PER_CHUNK + 1)]}]
        with self.assertRaisesRegex(ValueError, 'atom_limit'):
            runtime_resolve_atoms([chunk], outputs)
        self.assertEqual(RUNTIME_DIAGNOSTICS['ambiguous_atoms_omitted'], 0)

    def test_resolution_checkpoint_precedes_later_synthesis_failure(self):
        chunk = {'id': 'chunk-1', 'start': 0, 'utf16_start': 0, 'text': 'only source words'}
        outputs = [{'atoms': [{
            'entity_type': 'global', 'entity_key': 'paper', 'field': 'summary',
            'value': 'Unsupported', 'evidence': 'missing words',
        }]}]
        self._prime_checkpoint()
        persisted = []
        with patch.object(runtime, '_ORIGINAL_CHECKPOINT', side_effect=lambda output, payload: persisted.append(payload)):
            atoms = runtime_resolve_atoms([chunk], outputs)
        self.assertEqual(atoms, [])
        self.assertEqual(persisted[-1]['status'], 'evidence_resolution_complete_model_pending')
        self.assertEqual(persisted[-1]['runtime_evidence_rejections']['nonliteral_atoms_omitted'], 1)
        with self.assertRaises(RuntimeError):
            raise RuntimeError('synthetic_later_failure')

    def test_encrypted_checkpoint_diagnostics_expose_counts_not_source_text(self):
        RUNTIME_DIAGNOSTICS.update({
            'nonliteral_atoms_omitted': 2,
            'ambiguous_atoms_omitted': 1,
            'omission_digest': 'a' * 64,
        })
        payload = runtime_checkpoint_payload({'status': 'development_complete'})
        audit = payload['runtime_evidence_rejections']
        self.assertEqual(audit['policy'], EVIDENCE_REJECTION_POLICY)
        self.assertEqual(audit['nonliteral_atoms_omitted'], 2)
        self.assertEqual(audit['ambiguous_atoms_omitted'], 1)
        self.assertTrue(re.fullmatch(r'[0-9a-f]{64}', audit['omission_digest']))
        self.assertNotIn('source_text', audit)
        self.assertNotIn('quote', audit)
        self.assertNotIn('value', audit)

    def test_base_module_is_not_mutated_merely_by_importing_runtime_policy(self):
        self.assertEqual(development.CHUNK_CHARS, 18000)
        self.assertEqual(development.CHUNK_OVERLAP, 800)
        self.assertEqual(development.MAX_ATOMS_PER_CHUNK, 18)
        self.assertIs(development.atom_schema, runtime._ORIGINAL_ATOM_SCHEMA)
        self.assertIs(development.synthesis_schema, runtime._ORIGINAL_SYNTHESIS_SCHEMA)


if __name__ == '__main__':
    unittest.main()
