"""Synthetic tests for the full-text calibration development harness.

No scholarly source, network request, model inference or scientific label is used here.
"""
import unittest

from scripts.calibration.full_text_development import (
    build_proposal,
    canonical,
    chunk_request,
    chunk_source,
    extractor_fingerprint,
    resolve_atoms,
    sha,
)


class FullTextCalibrationDevelopmentTests(unittest.TestCase):
    def test_stable_extractor_identity_is_source_independent_but_request_is_not(self):
        fingerprint = extractor_fingerprint()
        a = chunk_source('A' * 20000)
        b = chunk_source('B' * 20000)
        self.assertEqual(fingerprint, extractor_fingerprint())
        self.assertNotEqual(sha(canonical(chunk_request(a[0]))), sha(canonical(chunk_request(b[0]))))

    def test_chunks_cover_complete_source_without_gaps(self):
        text = ('α' * 9000) + '\n\n' + ('beta ' * 7000) + '\n' + ('z' * 19000)
        chunks = chunk_source(text)
        self.assertEqual(chunks[0]['start'], 0)
        self.assertEqual(chunks[-1]['end'], len(text))
        cursor = 0
        for chunk in chunks:
            self.assertLessEqual(chunk['start'], cursor)
            cursor = max(cursor, chunk['end'])
            self.assertEqual(chunk['text'], text[chunk['start']:chunk['end']])
            self.assertEqual(chunk['utf16_start'], len(text[:chunk['start']].encode('utf-16-le')) // 2)
        self.assertEqual(cursor, len(text))

    def test_evidence_must_be_exact_and_utf16_offsets_are_preserved(self):
        text = 'intro ' + ('x' * 1200) + ' café unique evidence ' + ('y' * 1200)
        chunks = chunk_source(text)
        evidence = 'café unique evidence'
        outputs = []
        for chunk in chunks:
            atoms = []
            if evidence in chunk['text']:
                atoms.append({
                    'entity_type': 'global', 'entity_key': 'paper',
                    'field': 'research_question', 'value': 'A supported research question',
                    'evidence': evidence,
                })
            outputs.append({'atoms': atoms})
        atoms = resolve_atoms(chunks, outputs)
        self.assertEqual(len(atoms), 1)
        start_cp = text.index(evidence)
        self.assertEqual(atoms[0]['span']['start_offset'], len(text[:start_cp].encode('utf-16-le')) // 2)
        self.assertEqual(
            atoms[0]['span']['end_offset'] - atoms[0]['span']['start_offset'],
            len(evidence.encode('utf-16-le')) // 2,
        )
        bad = [{'atoms': [{
            'entity_type': 'global', 'entity_key': 'paper', 'field': 'research_question',
            'value': 'Unsupported', 'evidence': 'not in source',
        }]} for _ in chunks]
        with self.assertRaisesRegex(ValueError, 'nonliteral'):
            resolve_atoms(chunks, bad)

    def test_builder_preserves_multiple_studies_and_relations(self):
        atom_specs = [
            ('global', 'paper', 'summary', 'Paper summary'),
            ('global', 'paper', 'contribution', 'Main contribution'),
            ('study', 's-a', 'population', 'Population A'),
            ('study', 's-b', 'population', 'Population B'),
            ('dataset', 'd-a', 'name', 'Dataset A'),
            ('dataset', 'd-b', 'name', 'Dataset B'),
            ('analysis', 'a-a', 'method', 'Method A'),
            ('analysis', 'a-b', 'method', 'Method B'),
            ('variable_use', 'v-a', 'original_name', 'Variable A'),
            ('variable_use', 'v-b', 'original_name', 'Variable B'),
            ('finding', 'f-a', 'statement', 'Finding A'),
            ('finding', 'f-b', 'statement', 'Finding B'),
        ]
        atoms = []
        for index, (entity, key, field, value) in enumerate(atom_specs, 1):
            atoms.append({
                'id': f'atom-{index}', 'entity_type': entity, 'entity_key': key,
                'field': field, 'value': value,
                'span': {'id': f'span-{index}', 'start_offset': index * 10, 'end_offset': index * 10 + 5},
            })
        by = {(atom['entity_type'], atom['field'], atom['value']): atom['id'] for atom in atoms}

        def assign(entity, field, value):
            return {'field': field, 'value': value, 'atom_ids': [by[(entity, field, value)]]}

        synthesis = {
            'global_fields': [
                assign('global', 'summary', 'Paper summary'),
                assign('global', 'contribution', 'Main contribution'),
            ],
            'studies': [
                {'id': 'study-1', 'fields': [assign('study', 'population', 'Population A')]},
                {'id': 'study-2', 'fields': [assign('study', 'population', 'Population B')]},
            ],
            'datasets': [
                {'id': 'dataset-1', 'study_id': 'study-1', 'fields': [assign('dataset', 'name', 'Dataset A')]},
                {'id': 'dataset-2', 'study_id': 'study-2', 'fields': [assign('dataset', 'name', 'Dataset B')]},
            ],
            'analyses': [
                {'id': 'analysis-1', 'study_id': 'study-1', 'dataset_ids': ['dataset-1'],
                 'fields': [assign('analysis', 'method', 'Method A')]},
                {'id': 'analysis-2', 'study_id': 'study-2', 'dataset_ids': ['dataset-2'],
                 'fields': [assign('analysis', 'method', 'Method B')]},
            ],
            'variable_uses': [
                {'id': 'variable-1', 'analysis_id': 'analysis-1', 'dataset_ids': ['dataset-1'],
                 'fields': [assign('variable_use', 'original_name', 'Variable A')]},
                {'id': 'variable-2', 'analysis_id': 'analysis-2', 'dataset_ids': ['dataset-2'],
                 'fields': [assign('variable_use', 'original_name', 'Variable B')]},
            ],
            'findings': [
                {'id': 'finding-1', 'analysis_id': 'analysis-1', 'variable_use_ids': ['variable-1'],
                 'fields': [assign('finding', 'statement', 'Finding A')]},
                {'id': 'finding-2', 'analysis_id': 'analysis-2', 'variable_use_ids': ['variable-2'],
                 'fields': [assign('finding', 'statement', 'Finding B')]},
            ],
            'framework': {
                'status': 'insufficient_evidence', 'primary': None, 'rationale': None,
                'secondary': [], 'alternative': None,
            },
        }
        target = {'target_id': 'target', 'input_sha256': 'a' * 64}
        source = {'source_id': 'source'}
        proposal = build_proposal(target, source, atoms, synthesis)
        self.assertEqual(len(proposal['studies']), 2)
        self.assertEqual(proposal['datasets'][1]['study_id'], 'study-2')
        self.assertEqual(proposal['analyses'][1]['dataset_ids'], ['dataset-2'])
        self.assertEqual(proposal['variable_uses'][1]['analysis_id'], 'analysis-2')
        self.assertEqual(proposal['findings'][1]['variable_use_ids'], ['variable-2'])
        self.assertEqual(proposal['generated_by']['prompt_sha256'], extractor_fingerprint())
        self.assertEqual(proposal['source_coverage'], 'full_text')
        self.assertEqual(proposal['research_question']['status'], 'not_verifiable')
        self.assertGreaterEqual(len(proposal['spans']), 12)

    def test_cross_study_dataset_relation_fails_closed(self):
        atoms = [{
            'id': 'atom-1', 'entity_type': 'dataset', 'entity_key': 'd',
            'field': 'name', 'value': 'Dataset',
            'span': {'id': 'span-1', 'start_offset': 1, 'end_offset': 2},
        }]
        synthesis = {
            'global_fields': [],
            'studies': [{'id': 'study-1', 'fields': []}, {'id': 'study-2', 'fields': []}],
            'datasets': [{'id': 'dataset-1', 'study_id': 'study-1',
                          'fields': [{'field': 'name', 'value': 'Dataset', 'atom_ids': ['atom-1']}]}],
            'analyses': [{'id': 'analysis-1', 'study_id': 'study-2', 'dataset_ids': ['dataset-1'], 'fields': []}],
            'variable_uses': [], 'findings': [],
            'framework': {'status': 'outside_framework', 'primary': None, 'rationale': None,
                          'secondary': [], 'alternative': None},
        }
        with self.assertRaisesRegex(ValueError, 'analysis_relation'):
            build_proposal({'target_id': 't', 'input_sha256': 'b' * 64}, {'source_id': 's'}, atoms, synthesis)


if __name__ == '__main__':
    unittest.main()
