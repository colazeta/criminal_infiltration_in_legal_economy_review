"""Synthetic benchmark partition tests, without network, model or production calls."""
import copy
import json
import stat
import tempfile
import unittest
from pathlib import Path
from scripts.calibration import paper_content_benchmark as base
from scripts.calibration.paper_content_shard import pool, validate_packets, write_private, MIN_CASES, MAX_CASES

class ContentShardTests(unittest.TestCase):
    def payload(self, part=0):
        packets=[]
        for i,doi in enumerate(pool(part)[:MIN_CASES]):
            record={'id':'CAND-SYNTHETIC-'+str(i),'doi':doi,'title':'Synthetic test title '+str(i),
                    'sourceLinks':['https://example.org/synthetic']}
            packets.append(base.packet_for(record,{'DOI':doi,'title':[record['title']],
                                                  'abstract':'Synthetic abstract only; no scientific finding.'}))
        return {'protocol':base.PROTOCOL,'partition':part,'packets':packets}

    def test_three_disjoint_partitions_preserve_the_declared_pool(self):
        groups=[pool(i) for i in range(3)]
        self.assertEqual(set().union(*map(set,groups)),set(base.DOIS))
        self.assertEqual(sum(map(len,groups)),len(set(base.DOIS)))
        self.assertEqual(MIN_CASES*3,12)
        self.assertEqual(MAX_CASES*3,18)
        for bad in [-1,3,True,'0']:
            with self.assertRaises(ValueError): pool(bad)

    def test_valid_input_and_source_tampering(self):
        payload=self.payload()
        self.assertEqual(len(validate_packets(payload,0)),MIN_CASES)
        altered=copy.deepcopy(payload)
        altered['packets'][0]['sources'][0]['text']+=' changed'
        with self.assertRaisesRegex(ValueError,'source_integrity'): validate_packets(altered,0)

    def test_wrong_partition_and_duplicate_identity_are_rejected(self):
        payload=self.payload()
        with self.assertRaisesRegex(ValueError,'partition_mismatch'): validate_packets(payload,1)
        payload['packets'][1]=copy.deepcopy(payload['packets'][0])
        with self.assertRaisesRegex(ValueError,'partition_identity'): validate_packets(payload,0)

    def test_insufficient_or_oversized_partition_is_not_a_complete_benchmark(self):
        payload=self.payload();payload['packets']=payload['packets'][:3]
        with self.assertRaisesRegex(ValueError,'coverage'): validate_packets(payload,0)
        payload['packets']=[{}]*7
        with self.assertRaisesRegex(ValueError,'coverage'): validate_packets(payload,0)

    def test_local_input_is_private_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'input.json'
            write_private(path,{'synthetic':True})
            self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            self.assertTrue(json.loads(path.read_text())['synthetic'])
            with self.assertRaises(FileExistsError): write_private(path,{})

    def test_workflow_has_no_production_secret_and_preserves_old_batches(self):
        text=(Path(__file__).resolve().parents[1]/'.github/workflows/enrichment-content-benchmark.yml').read_text()
        self.assertNotIn('secrets.',text)
        self.assertNotIn('environment:',text)
        self.assertNotIn('cancel-in-progress: true',text)
        self.assertIn('cancel-in-progress: false',text)
        self.assertIn('fail-fast: false',text)
        self.assertIn('persist-credentials: false',text)
        self.assertLess(text.index('Retain source-only ciphertext'),text.index('paper_content_shard infer'))
        self.assertNotIn('path: ${{ runner.temp }}/benchmark-input.json',text)
