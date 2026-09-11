"""The model generation schema and acceptance gate agree on required summary evidence."""
import unittest
from scripts.enrichment.pilot import FACT_FIELDS, bound_schema, prepare_proposal

class PilotSummaryTests(unittest.TestCase):
    def test_generation_requires_nonnull_grounded_summary(self):
        spec = bound_schema('Synthetic source: a conceptual analysis of business control.')
        summary = spec['properties']['summary']
        self.assertEqual(summary['type'], 'object')
        self.assertIn('summary', spec['required'])
        self.assertEqual(set(summary['required']), {'value', 'evidence_ids'})
        self.assertEqual(summary['properties']['value']['minLength'], 1)
        self.assertEqual(summary['properties']['evidence_ids']['minItems'], 1)
        self.assertEqual(summary['properties']['evidence_ids']['items']['enum'], ['b1'])
        self.assertIn('null', spec['properties']['sample_size']['type'])

    def test_converter_still_rejects_null_summary_without_fabricating_one(self):
        target = {'target_id':'t'*16, 'input_sha256':'a'*64}
        source = dict(target, source_id='s'*16, evidence_kind='abstract', text='Synthetic conceptual research source.')
        extracted = {field:None for field in FACT_FIELDS}
        extracted.update(findings=[], variables=[], framework={'category':None,'rationale':None})
        with self.assertRaisesRegex(ValueError, 'pilot_summary_required'):
            prepare_proposal({'target':target,'sources':[source]}, extracted)

    def test_source_schema_does_not_mutate_the_optional_fact_template(self):
        spec = bound_schema('Synthetic evidence with source blocks.')
        self.assertEqual(spec['properties']['summary']['type'], 'object')
        self.assertEqual(spec['properties']['method']['type'], ['object','null'])
