"""Synthesis atom-scope regression tests; no source, model or network access."""
import unittest

from scripts.calibration import full_text_development as development
from scripts.calibration import full_text_development_resume as resume
from scripts.calibration import full_text_development_run as runtime


class FullTextAssignmentScopeTests(unittest.TestCase):
    def atoms(self):
        return [
            {
                'id': 'atom-global-summary', 'entity_type': 'global', 'entity_key': 'paper',
                'field': 'summary', 'value': 'Summary',
                'span': {'id': 'span-global-summary', 'start_offset': 0, 'end_offset': 1},
            },
            {
                'id': 'atom-analysis-method-1', 'entity_type': 'analysis', 'entity_key': 'analysis-1',
                'field': 'method', 'value': 'Method one',
                'span': {'id': 'span-analysis-method-1', 'start_offset': 2, 'end_offset': 3},
            },
            {
                'id': 'atom-analysis-method-2', 'entity_type': 'analysis', 'entity_key': 'analysis-2',
                'field': 'method', 'value': 'Method two',
                'span': {'id': 'span-analysis-method-2', 'start_offset': 4, 'end_offset': 5},
            },
        ]

    @staticmethod
    def branch_for(item_schema, field):
        return next(
            branch for branch in item_schema['oneOf']
            if branch['properties']['field']['const'] == field
        )

    def test_synthesis_schema_allows_only_atom_ids_matching_destination_entity_and_field(self):
        schema = resume.atom_scoped_synthesis_schema(self.atoms())
        props = schema['properties']

        global_summary = self.branch_for(props['global_fields']['items'], 'summary')
        self.assertEqual(
            global_summary['properties']['atom_ids']['items']['enum'],
            ['atom-global-summary'],
        )

        analysis_items = props['analyses']['items']['properties']['fields']['items']
        analysis_method = self.branch_for(analysis_items, 'method')
        self.assertEqual(
            analysis_method['properties']['atom_ids']['items']['enum'],
            ['atom-analysis-method-1', 'atom-analysis-method-2'],
        )
        self.assertNotIn(
            'atom-global-summary',
            analysis_method['properties']['atom_ids']['items']['enum'],
        )

        # With no compatible study atom, the decoder cannot manufacture a study
        # assignment that the unchanged base validator would later have to reject.
        self.assertEqual(
            props['studies']['items']['properties']['fields']['maxItems'], 0,
        )

    def test_bounded_synthesis_request_uses_atom_scoped_schema_without_mutating_base_schema(self):
        original = development.synthesis_schema
        request = resume.atom_scoped_bounded_synthesis_request(self.atoms())
        self.assertEqual(
            request['response_format']['schema'],
            resume.atom_scoped_synthesis_schema(self.atoms()),
        )
        self.assertEqual(
            request['max_tokens'], runtime.SCIENTIFIC_CONFIG['synthesis_max_tokens'],
        )
        self.assertIs(development.synthesis_schema, original)

    def test_installation_changes_only_runtime_synthesis_contract_and_fingerprint_then_restores(self):
        prior_contract = runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA
        prior_builder = runtime.bounded_synthesis_request
        prior_fingerprint = runtime.runtime_extractor_fingerprint()

        state = resume.install_assignment_scope()
        try:
            self.assertEqual(
                runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA,
                resume.SYNTHESIS_ATOM_SCOPED_SCHEMA,
            )
            self.assertIs(
                runtime.bounded_synthesis_request,
                resume.atom_scoped_bounded_synthesis_request,
            )
            self.assertNotEqual(
                runtime.runtime_extractor_fingerprint(), prior_fingerprint,
            )
        finally:
            resume.restore_assignment_scope(state)

        self.assertEqual(runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA, prior_contract)
        self.assertIs(runtime.bounded_synthesis_request, prior_builder)
        self.assertEqual(runtime.runtime_extractor_fingerprint(), prior_fingerprint)


if __name__ == '__main__':
    unittest.main()
