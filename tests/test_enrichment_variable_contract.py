"""Regression for generation/conversion disagreement; synthetic evidence only."""
import unittest
from scripts.enrichment.pilot import FACT_FIELDS, bound_schema, prepare_proposal

class VariableContractTests(unittest.TestCase):
    def setUp(self):
        self.target={'target_id':'t'*16,'input_sha256':'a'*64}
        self.packet={'target':self.target,'sources':[{'source_id':'s'*16,**self.target,'evidence_kind':'abstract','text':'Synthetic study description with an explicitly named measure.'}]}
        self.ir={k:None for k in FACT_FIELDS}
        self.ir.update({'summary':{'value':'Synthetic study.','evidence_ids':['b1']},'variables':[],'findings':[],'framework':{'category':None,'rationale':None}})

    def test_generator_cannot_request_a_nameless_variable(self):
        variable=bound_schema(self.packet['sources'][0]['text'])['properties']['variables']['items']
        self.assertEqual(variable['properties']['name']['type'],'object')
        self.assertIn('name',variable['required'])
        self.assertEqual(variable['properties']['name']['properties']['evidence_ids']['items']['enum'],['b1'])

    def test_existing_converter_still_rejects_nameless_variable(self):
        self.ir['variables']=[{'name':None,'operationalisation':None,'role':None}]
        with self.assertRaisesRegex(ValueError,'pilot_variable_shape'): prepare_proposal(self.packet,self.ir)

    def test_empty_array_does_not_invent_unmeasured_variables(self):
        proposal=prepare_proposal(self.packet,self.ir)
        self.assertEqual(proposal['variable_uses'],[])
        self.assertEqual(proposal['infiltration_operationalisation']['status'],'not_verifiable')

    def test_named_variable_retains_unknown_role_and_measurement(self):
        self.ir['variables']=[{'name':{'value':'Synthetic measure','evidence_ids':['b1']},'operationalisation':None,'role':None}]
        proposal=prepare_proposal(self.packet,self.ir)
        self.assertEqual(proposal['variable_uses'][0]['original_name']['value'],'Synthetic measure')
        self.assertEqual(proposal['variable_uses'][0]['role']['status'],'not_verifiable')
