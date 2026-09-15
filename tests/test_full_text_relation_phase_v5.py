"""Grouped #714 phase-separated relation regressions; no source/model/network access."""
import json
import unittest
from unittest.mock import patch

from scripts.calibration import full_text_development as development

phase = None


class FullTextRelationPhaseV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Import v5 only when this test class starts, not during discovery.

        The v5 execution module temporarily replaces shared v2 extension points.
        Deferring import prevents unittest discovery from mutating the reviewed
        v4 compatibility surface before the older regression modules execute.
        """
        global phase
        from scripts.calibration import full_text_development_resume_v5 as phase_module
        phase = phase_module

    def setUp(self):
        phase.reset_diagnostics()

    @classmethod
    def tearDownClass(cls):
        """Restore reviewed v4 hooks after direct v5-module regression coverage."""
        phase.v2.SYNTHESIS_ATOM_SCOPED_SCHEMA = phase.v4.SYNTHESIS_ATOM_SCOPED_SCHEMA
        phase.v2.atom_scoped_synthesis_schema = phase.v4.atom_scoped_synthesis_schema
        phase.v2.atom_scoped_bounded_synthesis_request = phase.v4.atom_scoped_bounded_synthesis_request
        phase.v2.install_assignment_scope = phase.v4.install_assignment_scope
        phase.v2.restore_assignment_scope = phase.v4.restore_assignment_scope
        phase.v2.resumable_post = phase.v4.resumable_post

    @staticmethod
    def atoms():
        return [
            {'id': 'atom-study', 'entity_type': 'study', 'entity_key': 's1', 'field': 'study_type', 'value': 'study', 'span': {'id': 'span-study', 'start_offset': 0, 'end_offset': 1}},
            {'id': 'atom-dataset', 'entity_type': 'dataset', 'entity_key': 'd1', 'field': 'name', 'value': 'data', 'span': {'id': 'span-dataset', 'start_offset': 2, 'end_offset': 3}},
            {'id': 'atom-analysis', 'entity_type': 'analysis', 'entity_key': 'a1', 'field': 'method', 'value': 'method', 'span': {'id': 'span-analysis', 'start_offset': 4, 'end_offset': 5}},
            {'id': 'atom-variable', 'entity_type': 'variable_use', 'entity_key': 'v1', 'field': 'concept', 'value': 'concept', 'span': {'id': 'span-variable', 'start_offset': 6, 'end_offset': 7}},
            {'id': 'atom-finding', 'entity_type': 'finding', 'entity_key': 'f1', 'field': 'statement', 'value': 'finding', 'span': {'id': 'span-finding', 'start_offset': 8, 'end_offset': 9}},
        ]

    @staticmethod
    def assignment(field, atom_id, value='value'):
        return {'field': field, 'value': value, 'atom_ids': [atom_id]}

    def phase_a(self, analyses=True, datasets=True):
        return {
            'global_fields': [],
            'studies': [{'fields': [self.assignment('study_type', 'atom-study', 'study')]}],
            'datasets': [{'fields': [self.assignment('name', 'atom-dataset', 'data')]}] if datasets else [],
            'analyses': [{'fields': [self.assignment('method', 'atom-analysis', 'method')]}] if analyses else [],
            'variable_uses': [{'fields': [self.assignment('concept', 'atom-variable', 'concept')]}],
            'findings': [{'fields': [self.assignment('statement', 'atom-finding', 'finding')]}],
            'framework': {'status': 'insufficient_evidence', 'primary': None, 'rationale': None, 'secondary': [], 'alternative': None},
        }

    def test_phase_a_preserves_711_atom_scope_and_removes_foreign_keys(self):
        schema = phase.phase_a_synthesis_schema(self.atoms())['properties']
        for group in ('studies', 'datasets', 'analyses', 'variable_uses', 'findings'):
            self.assertEqual(set(schema[group]['items']['properties']), {'fields'})
        study_fields = schema['studies']['items']['properties']['fields']['items']['oneOf']
        matching = next(item for item in study_fields if item['properties']['field'].get('const') == 'study_type')
        self.assertEqual(matching['properties']['atom_ids']['items']['enum'], ['atom-study'])
        self.assertNotIn('analysis_id', json.dumps(schema, sort_keys=True))
        self.assertNotIn('study_id', json.dumps(schema, sort_keys=True))

    def test_phase_a_assigns_stable_ids_and_rejects_record_collision(self):
        first = phase._materialise_phase_a(self.phase_a())
        phase.reset_diagnostics()
        second = phase._materialise_phase_a(self.phase_a())
        self.assertEqual(
            {group: [item['id'] for item in first[group]] for group, _ in phase._GROUPS},
            {group: [item['id'] for item in second[group]] for group, _ in phase._GROUPS},
        )
        duplicate = self.phase_a()
        duplicate['analyses'].append(json.loads(json.dumps(duplicate['analyses'][0])))
        with self.assertRaisesRegex(ValueError, 'fulltext_phase_a_record_collision'):
            phase._materialise_phase_a(duplicate)

    def test_audit_missing_analysis_family_omits_dependants_without_model_retry(self):
        records = phase._materialise_phase_a(self.phase_a(analyses=False, datasets=False))
        with patch.object(phase.development, 'post_model', side_effect=AssertionError('no relation call is possible')):
            links = phase._link_records(records)
        self.assertEqual(links['variable_uses'], [])
        self.assertEqual(links['findings'], [])
        self.assertEqual(phase.DIAGNOSTICS['phase_b_failure_families']['variable_missing_analysis'], 1)
        self.assertEqual(phase.DIAGNOSTICS['phase_b_failure_families']['finding_missing_analysis'], 1)
        self.assertEqual(phase.DIAGNOSTICS['phase_b_omitted_counts']['variable_uses'], 1)
        self.assertEqual(phase.DIAGNOSTICS['phase_b_omitted_counts']['findings'], 1)

    def test_relation_decoders_constrain_each_family_to_materialised_parents(self):
        records = phase._materialise_phase_a(self.phase_a())
        study_id = records['studies'][0]['id']
        dataset_id = records['datasets'][0]['id']
        analysis_id = records['analyses'][0]['id']
        variable_id = records['variable_uses'][0]['id']

        analysis = phase._analysis_link_schema(records, [{'id': dataset_id, 'study_id': study_id}])
        branch = analysis['items']['oneOf'][0]
        self.assertEqual(branch['properties']['study_id']['const'], study_id)
        self.assertEqual(branch['properties']['dataset_ids']['items']['enum'], [dataset_id])

        variable = phase._variable_link_schema(records, [{'id': analysis_id, 'study_id': study_id, 'dataset_ids': [dataset_id]}])
        branch = variable['items']['oneOf'][0]
        self.assertEqual(branch['properties']['analysis_id']['const'], analysis_id)
        self.assertEqual(branch['properties']['dataset_ids']['items']['enum'], [dataset_id])

        finding = phase._finding_link_schema(
            records,
            [{'id': variable_id, 'analysis_id': analysis_id, 'dataset_ids': [dataset_id]}],
            [{'id': analysis_id, 'study_id': study_id, 'dataset_ids': [dataset_id]}],
        )
        branch = finding['items']['oneOf'][0]
        self.assertEqual(branch['properties']['analysis_id']['const'], analysis_id)
        self.assertEqual(branch['properties']['variable_use_ids']['items']['enum'], [variable_id])

    def test_repeated_relation_id_fails_closed_instead_of_normalising_again(self):
        records = phase._materialise_phase_a(self.phase_a())
        dataset_id = records['datasets'][0]['id']
        with self.assertRaisesRegex(ValueError, 'fulltext_relation_link_collision'):
            phase._unique_links(
                [{'id': dataset_id, 'study_id': 's'}, {'id': dataset_id, 'study_id': 's'}],
                {dataset_id},
            )

    def test_full_phase_merges_only_linked_records_before_unchanged_validator(self):
        synthesis = self.phase_a()
        materialised = phase._materialise_phase_a(json.loads(json.dumps(synthesis)))
        study_id = materialised['studies'][0]['id']
        dataset_id = materialised['datasets'][0]['id']
        analysis_id = materialised['analyses'][0]['id']
        variable_id = materialised['variable_uses'][0]['id']
        finding_id = materialised['findings'][0]['id']
        relation_outputs = [
            {'links': [{'id': dataset_id, 'study_id': study_id}]},
            {'links': [{'id': analysis_id, 'study_id': study_id, 'dataset_ids': [dataset_id]}]},
            {'links': [{'id': variable_id, 'analysis_id': analysis_id, 'dataset_ids': [dataset_id]}]},
            {'links': [{'id': finding_id, 'analysis_id': analysis_id, 'variable_use_ids': [variable_id]}]},
        ]
        captured = []
        def validator(_target, _source, _atoms, graph):
            captured.append(json.loads(json.dumps(graph)))
            return {'ok': True}
        phase.reset_diagnostics()
        with patch.object(phase.development, 'post_model', side_effect=relation_outputs), patch.object(phase.v4, '_ORIGINAL_BUILD_PROPOSAL', side_effect=validator):
            result = phase.phase_separated_build_proposal({}, {}, self.atoms(), synthesis)
        self.assertEqual(result, {'ok': True})
        self.assertEqual(captured[0]['datasets'][0]['study_id'], study_id)
        self.assertEqual(captured[0]['analyses'][0]['dataset_ids'], [dataset_id])
        self.assertEqual(captured[0]['variable_uses'][0]['analysis_id'], analysis_id)
        self.assertEqual(captured[0]['findings'][0]['variable_use_ids'], [variable_id])
        self.assertEqual(synthesis, captured[0])
        self.assertEqual(len(phase.DIAGNOSTICS['relation_request_sha256']), 4)
        self.assertRegex(phase.DIAGNOSTICS['phase_separated_request_sha256'], r'^[0-9a-f]{64}$')

    def test_checkpoint_diagnostics_expose_counts_and_hashes_not_record_ids(self):
        records = phase._materialise_phase_a(self.phase_a(analyses=False, datasets=False))
        with patch.object(phase.development, 'post_model', side_effect=AssertionError('not called')):
            phase._link_records(records)
        payload = phase.phase_checkpoint_payload({'status': 'synthetic'})
        diagnostics = payload['runtime_phase_separated_relations']
        serialised = json.dumps(diagnostics, sort_keys=True)
        self.assertEqual(diagnostics['policy'], phase.PHASE_SEPARATION_POLICY)
        for group, _ in phase._GROUPS:
            for item in records[group]:
                self.assertNotIn(item['id'], serialised)


if __name__ == '__main__':
    unittest.main()
