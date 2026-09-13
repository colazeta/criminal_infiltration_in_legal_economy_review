import copy
import json
import unittest
from pathlib import Path
from scripts.enrichment.public_research_check import check, digest, public_get
from scripts.ontology.validate_ontology import check_public_research_contract


class PublicResearchCheckTests(unittest.TestCase):
    def fixture(self):
        candidate = {'id': 'CAND-TEST', 'title': 'Synthetic test', 'doi': '', 'sourceLinks': []}
        data = {'schema_version': 1, 'projection_version': 'CILE-PUBLIC-RESEARCH-1', 'candidate': candidate,
                'availability': 'available', 'research': {'framework': {'primary': 'diagnosis'}, 'summary': 'Original test'}}
        data['revision'] = digest(data)
        audit = {'projection_version': 'CILE-PUBLIC-RESEARCH-1', 'counts': {'available': 1},
                 'records': [{'id': candidate['id'], 'availability': 'available', 'revision': data['revision']}]}
        return candidate, data, audit

    def test_source_to_served_readback(self):
        candidate, data, audit = self.fixture()
        result = check('a' * 40, caller=lambda *a, **kw: audit,
                       fetcher=lambda url: {'records': [candidate]} if 'paper-register.json' in url else data)
        self.assertTrue(result['verified'])
        self.assertEqual(result['verified_http_records'], 1)
        self.assertFalse(result['private_content_exported'])
        self.assertFalse(result['scientific_approval_performed'])

    def test_same_count_changed_content_fails_even_with_forged_old_revision(self):
        candidate, data, audit = self.fixture()
        data['research']['summary'] = 'Changed content'
        result = check('a' * 40, caller=lambda *a, **kw: audit,
                       fetcher=lambda url: {'records': [candidate]} if 'paper-register.json' in url else data)
        self.assertFalse(result['verified'])
        self.assertEqual(result['mismatched_records'], ['CAND-TEST'])

    def test_publication_does_not_validate_a_nonregistered_candidate(self):
        _, data, audit = self.fixture()
        result = check('a' * 40, caller=lambda *a, **kw: audit,
                       fetcher=lambda url: {'records': []} if 'paper-register.json' in url else data)
        self.assertFalse(result['verified'])
        self.assertEqual(result['unregistered_records'], ['CAND-TEST'])

    def test_duplicate_audit_ids_fail(self):
        _, _, audit = self.fixture()
        audit['records'] *= 2
        with self.assertRaisesRegex(RuntimeError, 'invalid_audit_inventory'):
            check('a' * 40, caller=lambda *a, **kw: audit)

    def test_public_fetch_cannot_visit_an_arbitrary_origin(self):
        with self.assertRaisesRegex(RuntimeError, 'unexpected_public_origin'):
            public_get('https://example.org/private')

    def test_projection_has_complete_physical_and_semantic_mapping(self):
        root = Path(__file__).resolve().parents[1]
        profile = json.loads((root / 'ontology/cile-review-profile.yaml').read_text())
        check_public_research_contract(profile)

    def test_source_schema_stays_private_and_calibration_gate_stays_separate(self):
        root = Path(__file__).resolve().parents[1]
        public = json.loads((root / 'schema/public-paper-research.schema.json').read_text())
        props = public['properties']['research']['properties']
        self.assertEqual(props['assessment_state'], {'const': 'unreviewed_proposal'})
        for key in ['target_id', 'source_ids', 'input_sha256', 'generated_by', 'analyst_limitations']:
            self.assertNotIn(key, props)
        code = (root / 'curator-app/src/public-paper-research.js').read_text()
        for token in ['INSERT INTO', 'UPDATE enrichment', 'DELETE FROM', 'activateEnrichment', 'runEnrichment(']:
            self.assertNotIn(token, code)


if __name__ == '__main__':
    unittest.main()
