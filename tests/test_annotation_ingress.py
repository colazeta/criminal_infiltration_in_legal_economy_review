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


if __name__=='__main__':unittest.main()
