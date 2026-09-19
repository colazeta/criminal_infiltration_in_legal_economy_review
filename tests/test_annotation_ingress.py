"""Ingress completeness, bounded batches and private receipt failures."""
import unittest
from unittest.mock import patch
from scripts.architecture import ingest_annotations as ingress


class AnnotationIngressTests(unittest.TestCase):
    def test_missing_parent_is_not_silently_dropped_from_the_population(self):
        comment={'id':1,'issue_url':ingress.API+'/issues/99'}
        with patch.object(ingress,'pages',side_effect=[[],[comment]]):
            with self.assertRaisesRegex(RuntimeError,'parent_missing'):
                ingress.population()

    def test_batch_receipt_must_cover_every_input(self):
        bad={'contract':ingress.VERSION,'receipts':[]}
        with patch.object(ingress,'call',return_value=bad):
            with self.assertRaisesRegex(RuntimeError,'batch_receipt_invalid'):
                ingress.ingest([{'private':'not logged'}],'c'*40)

    def test_all_bounded_batch_items_are_counted_without_private_content(self):
        sizes=[]
        def call(operation,*,expected_commit,ingress):
            self.assertEqual(operation,'archive-annotation-batch');self.assertEqual(expected_commit,'c'*40)
            sizes.append(len(ingress))
            return {'contract':'CILE-ANNOTATION-ARCHIVE-1','receipts':[{'contract':'CILE-ANNOTATION-ARCHIVE-1','captured':True,'annotation':False,'snapshot_id':'d'*64} for _ in ingress]}
        with patch.object(ingress,'call',side_effect=call):
            result=ingress.ingest([{'private':'retained input'}]*61,'c'*40)
        self.assertEqual(sizes,[25,25,11]);self.assertEqual(result['inputs'],61)
        self.assertNotIn('retained input',str(result))

    def test_unexpected_private_receipt_field_is_rejected_before_logging(self):
        with self.assertRaisesRegex(RuntimeError,'receipt_invalid'):
            ingress.validate_receipt({'contract':ingress.VERSION,'captured':True,'annotation':False,'private_source':'never print'})

    def test_repeated_page_id_stops_a_mutating_population(self):
        with patch.object(ingress,'request',return_value=[{'id':1}]*100):
            with self.assertRaisesRegex(RuntimeError,'population_changed'):
                ingress.pages('/issues/comments')

    def test_bounded_catchup_imports_only_changed_observations_then_requires_stability(self):
        a=[{'comment':{'id':1},'body':'first private observation'}]
        b=a+[{'comment':{'id':2},'body':'second private observation'}]
        writes=[]
        def write(items, commit):
            writes.append(items)
            return {'inputs':len(items),'new_annotations':0}
        with patch.object(ingress,'population',side_effect=[a,b,b]), patch.object(ingress,'ingest',side_effect=write):
            items,first,replay,observed,rounds=ingress.stable_import('c'*40)
        self.assertEqual(items,b);self.assertEqual(rounds,2)
        self.assertEqual(first['inputs'],2);self.assertEqual(replay['new_annotations'],0)
        self.assertEqual([len(x) for x in writes],[0,0,1,1,1,1])

    def test_unstable_population_is_not_certified_after_the_bounded_rounds(self):
        values=[[{'comment':{'id':i}}] for i in range(5)]
        with patch.object(ingress,'population',side_effect=values), patch.object(ingress,'ingest',return_value={'inputs':0,'new_annotations':0}):
            with self.assertRaisesRegex(RuntimeError,'population_changed'):
                ingress.stable_import('c'*40)

    def test_closed_diagnostics_do_not_echo_an_exception_or_source_body(self):
        self.assertEqual(ingress.safe_error(RuntimeError('github_ingress_population_changed')),'github_ingress_population_changed')
        self.assertEqual(ingress.safe_error(RuntimeError('github_ingress_http_403')),'github_ingress_http_403')
        self.assertEqual(ingress.safe_error(RuntimeError('PRIVATE BODY token=abc')),'annotation_ingress_gate_failed')


if __name__=='__main__':unittest.main()
