"""Synthetic software fixtures only: no real papers, model calls or gold labels."""
import copy
import hashlib
import json
import subprocess
import unittest
from scripts.enrichment.pilot import FACT_FIELDS, prepare_proposal

TEXT='Synthetic evidence: Researchers compare business outcomes in two regions using panel regression.'
class PilotTests(unittest.TestCase):
    def setUp(self):
        self.target={'target_id':'t'*16,'input_sha256':'a'*64}
        self.source={'source_id':'s'*16,**self.target,'evidence_kind':'abstract','text':TEXT,'content_sha256':hashlib.sha256(TEXT.encode()).hexdigest()}
        self.packet={'target':self.target,'sources':[self.source]}
        self.ir={k:None for k in FACT_FIELDS}
        self.ir.update({'summary':{'value':'Synthetic comparison.','quote':'Researchers compare business outcomes'},'findings':[],'variables':[],'framework':{'category':None,'rationale':None}})

    def test_grounded_payload_passes_native_schema(self):
        self.ir['method']={'value':'Panel regression','quote':'using panel regression'}
        proposal=prepare_proposal(self.packet,self.ir)
        js="import{validateExtraction}from'./curator-app/src/paper-enrichment.js';let s='';for await(const c of process.stdin)s+=c;const p=JSON.parse(s);validateExtraction(p.proposal,p.target,p.sources);"
        run=subprocess.run(['node','--input-type=module','-e',js],input=json.dumps({'proposal':proposal,**self.packet}),text=True,capture_output=True)
        self.assertEqual(run.returncode,0,'Synthetic payload did not match native schema')
        self.assertEqual(proposal['source_coverage'],'abstract_only')
        self.assertEqual(proposal['framework']['status'],'insufficient_evidence')

    def test_generated_or_full_text_cannot_be_relabelled_as_abstract(self):
        for kind in ['full_text','model_summary','metadata']:
            self.source['evidence_kind']=kind
            with self.assertRaisesRegex(ValueError,'bounded_complete_abstract'): prepare_proposal(self.packet,self.ir)

    def test_nonexistent_or_nonunique_quote_is_rejected(self):
        for quote in ['An invented quote from another paper', 'Synthetic evidence']:
            self.ir['summary']['quote']=quote
            if quote=='Synthetic evidence': self.source['text']=TEXT+' Synthetic evidence'
            with self.assertRaisesRegex(ValueError,'quote_not_unique_or_missing'): prepare_proposal(self.packet,self.ir)

    def test_unsupported_label_or_no_rationale_is_rejected(self):
        for category in ['screening','automatic_acceptance']:
            self.ir['framework']['category']=category
            with self.assertRaises(ValueError): prepare_proposal(self.packet,self.ir)

    def test_unknowns_are_not_false_negative_declarations(self):
        p=prepare_proposal(self.packet,self.ir)
        self.assertEqual(p['infiltration_operationalisation']['status'],'not_verifiable')
        self.assertIsNone(p['infiltration_operationalisation']['value'])
        self.assertFalse(p['studies'])

    def test_offsets_use_utf16_and_model_cannot_supply_ids(self):
        self.source['text']='\U0001f50d '+TEXT
        p=prepare_proposal(self.packet,self.ir)
        offset=self.source['text'].index(self.ir['summary']['quote'])
        self.assertEqual(p['spans'][0]['start_offset'],offset+1)
        bad=copy.deepcopy(self.ir);bad['target_id']='other-paper'
        with self.assertRaisesRegex(ValueError,'schema_keys'): prepare_proposal(self.packet,bad)

    def test_limits_and_no_silent_truncation(self):
        self.ir['findings']=[None]*5
        with self.assertRaisesRegex(ValueError,'finding_limit'): prepare_proposal(self.packet,self.ir)
        self.ir['findings']=[];self.source['text']='x'*14001
        with self.assertRaisesRegex(ValueError,'bounded_complete_abstract'): prepare_proposal(self.packet,self.ir)
