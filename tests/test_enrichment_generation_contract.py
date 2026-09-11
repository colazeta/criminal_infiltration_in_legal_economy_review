"""Synthetic generation-contract tests; not a real-paper scientific benchmark."""
import hashlib
import json
import unittest
from scripts.enrichment.pilot import FACT_FIELDS, bound_schema, model_request, prepare_proposal

TEXT = 'Synthetic source: Researchers compare business outcomes using panel regression.'

class GenerationContractTests(unittest.TestCase):
    def packet(self):
        target = {'target_id': 't' * 16, 'input_sha256': 'a' * 64}
        source = {'source_id': 's' * 16, **target, 'evidence_kind': 'abstract', 'text': TEXT}
        return {'target': target, 'sources': [source]}

    def extracted(self):
        return {**dict.fromkeys(FACT_FIELDS),
                'summary': {'value': 'Synthetic comparison.', 'evidence_ids': ['b1']},
                'findings': [], 'variables': [],
                'framework': {'category': None, 'rationale': None}}

    def test_summary_contract_matches_unchanged_converter_requirement(self):
        self.assertEqual(bound_schema(TEXT)['properties']['summary']['type'], 'object')
        invalid = self.extracted()
        invalid['summary'] = None
        with self.assertRaisesRegex(ValueError, 'pilot_summary_required'):
            prepare_proposal(self.packet(), invalid)

    def test_schema_is_visible_to_model_and_decoder(self):
        payload = model_request(TEXT)
        visible = payload['messages'][0]['content'].split('Required output JSON schema:\n', 1)[1]
        self.assertEqual(json.loads(visible), payload['response_format']['schema'])
        blocks = json.loads(payload['messages'][1]['content'])['abstract_blocks']
        self.assertEqual(''.join(b['text'] for b in blocks), TEXT)
        self.assertEqual(payload['max_tokens'], 2500)

    def test_provenance_hash_covers_exact_model_request(self):
        proposal = prepare_proposal(self.packet(), self.extracted())
        expected = hashlib.sha256(json.dumps(model_request(TEXT), sort_keys=True,
                                             separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(proposal['generated_by']['prompt_sha256'], expected)
