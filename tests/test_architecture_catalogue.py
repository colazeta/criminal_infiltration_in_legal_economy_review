import json
import unittest
from scripts.architecture.catalogue import ROOT, catalogue


class ArchitectureCatalogueTests(unittest.TestCase):
    def test_every_sql_column_has_a_semantic_trace_without_runtime_inference(self):
        physical, trace = catalogue()
        self.assertEqual(len(physical['tables']), 79)
        self.assertEqual(len(trace), 621)
        self.assertFalse(physical['runtime_verified'])
        self.assertEqual(len([t for t in physical['tables'] if t['implementation_status'] == 'configured_enrichment_sqlite']), 46)
        self.assertEqual(physical, json.loads((ROOT / 'docs/architecture/physical-schema.json').read_text()))

    def test_dictionary_exposes_sqlite_null_primary_keys_and_candidate_work_cardinality(self):
        physical, trace = catalogue()
        target = next(r for r in trace if r['table'] == 'enrichment_targets' and r['column'] == 'target_id')
        self.assertTrue(target['nullable_in_sqlite'])
        candidates = next(t for t in physical['tables'] if t['table'] == 'review_candidates')
        self.assertTrue(any(i['unique'] and [c['name'] for c in i['columns']] == ['review_id', 'work_id'] for i in candidates['indexes']))


if __name__ == '__main__':
    unittest.main()
