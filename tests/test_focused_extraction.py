"""Synthetic focused-extractor tests. No real sources, inference or gold labels."""
import json
import subprocess
import unittest
from unittest.mock import patch
from scripts.enrichment.focused import (STAGES, LIMITS, focused_requests, focused_proposal,
                                       sanitise_critical_literals, prompt_contract,
                                       canonical, UNKNOWN, CONTENT, VARIABLES, FRAMEWORK,
                                       prompt_fingerprint)
from scripts.enrichment.pilot import FACT_FIELDS

TEXT = 'Synthetic study: 20 firms in 2010–2012. We compare profitability. Profitability means net income divided by revenue.'

def fact(value):
    return {'value':value,'evidence_ids':['b1']}

class FocusedTests(unittest.TestCase):
    def data(self):
        target={'target_id':'t'*16,'input_sha256':'a'*64}
        source={**target,'source_id':'s'*16,'evidence_kind':'abstract','text':TEXT}
        content={**dict.fromkeys(FACT_FIELDS),'summary':fact('A synthetic profitability comparison.'),
                 'research_question':fact('Profitability comparison.'),'sample_size':fact('20 firms'),
                 'period':fact('2010–2012'),'method':fact('Comparison'), 'findings':[]}
        outputs={'content':content,'variables':{'variables':[{'name':fact('profitability'),
                   'operationalisation':fact('net income divided by revenue'),'role':None}]},
                 'framework':{'category':None,'rationale':None,'abstention_reason':'outside_framework'}}
        return {'target':target,'sources':[source]},outputs

    def test_three_independent_source_bound_requests_and_budget(self):
        requests=focused_requests(TEXT)
        self.assertEqual(tuple(requests),STAGES)
        self.assertEqual(sum(r['max_tokens'] for r in requests.values()),3700)
        for stage,request in requests.items():
            visible=request['messages'][0]['content'].split('Required output JSON schema:\n')[1]
            self.assertEqual(json.loads(visible),request['response_format']['schema'])
            self.assertEqual(request['max_tokens'],LIMITS[stage])
            self.assertEqual(json.loads(request['messages'][1]['content'])['abstract_blocks'][0]['text'],TEXT)
            self.assertEqual(request['temperature'],0)
            self.assertNotIn('tools',request)

    def test_prompt_identity_is_source_independent_but_requests_remain_source_bound(self):
        fingerprint=prompt_fingerprint()
        self.assertRegex(fingerprint,r'^[a-f0-9]{64}$')
        other='Synthetic study: 31 contracts in 2019. We analyse bidding.'
        self.assertEqual(prompt_fingerprint(),fingerprint)
        self.assertNotEqual(canonical(focused_requests(TEXT)),canonical(focused_requests(other)))
        self.assertNotIn(TEXT,canonical(prompt_contract()))
        self.assertIn('<SOURCE_BLOCK_TEXT>',canonical(prompt_contract()))

    def test_prompt_identity_changes_with_actual_request_contract(self):
        original=prompt_fingerprint()
        with patch.dict(LIMITS, {'content': LIMITS['content']+1}):
            self.assertNotEqual(prompt_fingerprint(),original)
        self.assertEqual(prompt_fingerprint(),original)

    def test_complete_literal_proposal_passes_existing_native_schema(self):
        packet,outputs=self.data()
        combined,proposal=focused_proposal(packet,outputs)
        self.assertEqual(proposal['framework']['status'],'outside_framework')
        self.assertIsNone(proposal['variable_uses'][0]['role']['value'])
        self.assertEqual(proposal['variable_uses'][0]['original_name']['value'],'profitability')
        js="import{validateExtraction}from'./curator-app/src/paper-enrichment.js';let s='';for await(const c of process.stdin)s+=c;let p=JSON.parse(s);validateExtraction(p.proposal,p.target,p.sources);"
        result=subprocess.run(['node','--input-type=module','-e',js],input=json.dumps({**packet,'proposal':proposal}),text=True,capture_output=True)
        self.assertEqual(result.returncode,0,'Synthetic packet failed native schema validation')
        self.assertEqual(proposal['generated_by']['prompt_sha256'],prompt_fingerprint())

    def test_unknown_strings_must_be_null(self):
        for value in ['Not specified in the abstract.', 'unknown', 'Not reported', 'N/A', 'null']:
            packet,outputs=self.data();outputs['content']['sample_size']=fact(value)
            with self.assertRaisesRegex(ValueError,'invalid_missingness'): focused_proposal(packet,outputs)
        self.assertIsNone(UNKNOWN.fullmatch('The model did not report a significant difference.'))

    def test_nonliteral_critical_values_fail_closed_to_unresolved_with_warnings(self):
        packet,outputs=self.data()
        outputs['variables']['variables'][0]['operationalisation']=fact('return on equity')
        outputs['content']['sample_size']=fact('21 firms')
        clean,warnings=sanitise_critical_literals(packet,outputs)
        self.assertIsNone(clean['variables']['variables'][0]['operationalisation'])
        self.assertIsNone(clean['content']['sample_size'])
        self.assertEqual({w['reason'] for w in warnings},
                         {'nonliteral_operationalisation_dropped','nonliteral_critical_value_dropped'})
        combined,proposal=focused_proposal(packet,outputs)
        self.assertEqual(proposal['sample_size']['status'],'not_verifiable')
        self.assertIsNone(proposal['sample_size']['value'])
        self.assertEqual(proposal['variable_uses'][0]['operationalisation']['status'],'not_verifiable')

    def test_nonliteral_variable_name_drops_the_variable_not_the_evidence_gate(self):
        packet,outputs=self.data()
        outputs['variables']['variables'][0]['name']=fact('profit margin')
        clean,warnings=sanitise_critical_literals(packet,outputs)
        self.assertEqual(clean['variables']['variables'],[])
        self.assertEqual(warnings[0]['reason'],'nonliteral_variable_dropped')
        self.assertEqual(focused_proposal(packet,outputs)[1]['variable_uses'],[])

    def test_invented_author_limitations_are_not_filled_by_converter(self):
        packet,outputs=self.data()
        self.assertIsNone(focused_proposal(packet,outputs)[1]['authors_limitations']['value'])
        outputs['content']['authors_limitations']=fact('Single-country research limits generalisability.')
        clean,warnings=sanitise_critical_literals(packet,outputs)
        self.assertIsNone(clean['content']['authors_limitations'])
        self.assertEqual(warnings[0]['field'],'authors_limitations')
        self.assertIsNone(focused_proposal(packet,outputs)[1]['authors_limitations']['value'])

    def test_reference_must_cover_the_exact_critical_value(self):
        packet,outputs=self.data();packet['sources'][0]['text']='x '*300+TEXT
        outputs['content']['sample_size']['evidence_ids']=['b1']
        clean,warnings=sanitise_critical_literals(packet,outputs)
        self.assertIsNone(clean['content']['sample_size'])
        self.assertEqual(warnings[0]['reason'],'nonliteral_critical_value_dropped')
        self.assertEqual(focused_proposal(packet,outputs)[1]['sample_size']['status'],'not_verifiable')

    def test_incomplete_stages_and_inconsistent_abstention_fail_closed(self):
        packet,outputs=self.data();del outputs['variables']
        with self.assertRaisesRegex(ValueError,'stages_incomplete'): focused_proposal(packet,outputs)
        packet,outputs=self.data();outputs['framework']['category']='diagnosis'
        with self.assertRaisesRegex(ValueError,'invalid_abstention'): focused_proposal(packet,outputs)

    def test_methodological_instructions_do_not_encode_real_paper_labels(self):
        self.assertIn('ground-truth',CONTENT)
        self.assertIn('not',VARIABLES.lower())
        self.assertIn('already identified',FRAMEWORK)
        self.assertIn('outside_framework',FRAMEWORK)
        for prompt in [CONTENT,VARIABLES,FRAMEWORK]:
            self.assertNotIn('10.1111',prompt)
            self.assertNotIn('108 Italian',prompt)
