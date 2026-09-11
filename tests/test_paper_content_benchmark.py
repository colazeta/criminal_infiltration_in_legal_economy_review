"""Synthetic benchmark-harness tests; no online requests or actual labels."""
import json
import hashlib
from pathlib import Path
import unittest
from scripts.calibration.paper_content_benchmark import DOIS, packet_for, PROTOCOL

class ContentBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.record={'id':'CAND-SYNTHETIC-ONLY','doi':'10.9999/synthetic','title':'A synthetic study',
                     'sourceLinks':['https://example.org/synthetic']}
        self.message={'DOI':self.record['doi'],'title':[self.record['title']],
                      'abstract':'<jats:p>Synthetic abstract with exact source punctuation.</jats:p>'}

    def test_benchmark_packet_is_source_faithful_and_not_a_production_receipt(self):
        packet=packet_for(self.record,self.message)
        self.assertEqual(packet['sources'][0]['text'],self.message['abstract'])
        self.assertEqual(packet['sources'][0]['content_sha256'],hashlib.sha256(self.message['abstract'].encode()).hexdigest())
        self.assertEqual(packet['scope'],'offline_benchmark_not_a_production_receipt')
        self.assertEqual(packet['target']['record_id'],self.record['id'])
        self.assertEqual(packet['target']['target_id'],hashlib.sha256((PROTOCOL+self.record['id']).encode()).hexdigest())

    def test_conflicting_identity_is_rejected(self):
        for field,value in [('DOI','10.9999/other'),('title',['Different work'])]:
            message={**self.message,field:value}
            with self.assertRaisesRegex(ValueError,'identity_mismatch'):
                packet_for(self.record,message)

    def test_missing_and_overlong_abstracts_are_explicit_not_truncated(self):
        for abstract,code in [(None,'abstract_not_returned'),('', 'abstract_not_returned'),('x'*14001,'source_over_limit')]:
            with self.assertRaisesRegex(ValueError,code):
                packet_for(self.record,{**self.message,'abstract':abstract})

    def test_pool_is_bounded_unique_and_already_registered(self):
        self.assertEqual(len(DOIS),24)
        self.assertEqual(len(DOIS),len(set(DOIS)))
        path=Path(__file__).resolve().parents[1]/'site/data/paper-register.json'
        registered={r['doi'].lower() for r in json.loads(path.read_text())['records']}
        self.assertTrue(set(DOIS)<=registered)
        self.assertNotIn('10.1257/aer.20201015',DOIS)  # Earlier development item, not a new benchmark item.
