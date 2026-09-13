import copy
import json
import unittest
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError
from pathlib import Path
from scripts.enrichment.public_research_check import check, digest, public_get, PublicFetchError, ORIGIN, PUBLIC_ORIGIN
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

    def test_public_probe_is_identified_and_checks_browser_cors_without_credentials(self):
        class Response(BytesIO):
            headers = {'Access-Control-Allow-Origin': PUBLIC_ORIGIN}
        url = ORIGIN + '/api/public-paper-research?id=CAND-TEST'
        with patch('scripts.enrichment.public_research_check._PRIVATE_HTTP.open', return_value=Response(b'{}')) as opened:
            self.assertEqual(public_get(url), {})
            request = opened.call_args.args[0]
            headers = {k.lower(): v for k, v in request.header_items()}
            self.assertEqual(headers['user-agent'], 'cile-public-research-check/1.0')
            self.assertEqual(headers['origin'], PUBLIC_ORIGIN)
            self.assertFalse(set(headers) & {'authorization', 'cookie', 'x-enrichment-signature'})

    def test_http_403_is_reported_without_body_or_credential_fallback(self):
        url = ORIGIN + '/api/public-paper-research?id=CAND-TEST'
        error = HTTPError(url, 403, 'Forbidden', {'Content-Type': 'text/html'}, BytesIO(b'PRIVATE BODY MUST NOT BE LOGGED'))
        with patch('scripts.enrichment.public_research_check._PRIVATE_HTTP.open', side_effect=error) as opened:
            with self.assertRaises(PublicFetchError) as raised:
                public_get(url)
            self.assertEqual(raised.exception.details, {'code': 'public_http_error', 'http_status': 403, 'content_type': 'text/html'})
            self.assertEqual(opened.call_count, 1)
            self.assertNotIn('PRIVATE BODY', str(raised.exception))

    def test_transport_failures_keep_source_counts_but_never_report_success(self):
        candidate, _, audit = self.fixture()
        def fetch(url):
            if 'paper-register.json' in url:
                return {'records': [candidate]}
            raise PublicFetchError('public_http_error', status=403)
        result = check('a' * 40, caller=lambda *a, **kw: audit, fetcher=fetch)
        self.assertFalse(result['verified'])
        self.assertEqual(result['source_counts'], {'available': 1})
        self.assertEqual(result['verified_http_records'], 0)
        self.assertFalse(result['all_populated_records_checked'])
        self.assertEqual(result['transport_errors'][0]['http_status'], 403)

    def test_missing_cors_permission_is_a_failed_public_read(self):
        class Response(BytesIO):
            headers = {}
        with patch('scripts.enrichment.public_research_check._PRIVATE_HTTP.open', return_value=Response(b'{}')):
            with self.assertRaisesRegex(PublicFetchError, 'public_cors_mismatch'):
                public_get(ORIGIN + '/api/public-paper-research?id=CAND-TEST')

    def test_public_probe_rejects_extra_paths_parameters_and_credentials(self):
        for url in [ORIGIN + '.evil/api/public-paper-research?id=CAND-TEST',
                    ORIGIN + '/api/public-paper-research?id=CAND-TEST&sql=SELECT',
                    ORIGIN + '/api/public-paper-research?id=CAND-TEST&id=CAND-OTHER',
                    PUBLIC_ORIGIN + '/criminal_infiltration_in_legal_economy_review/data/paper-register.json.evil']:
            with self.assertRaisesRegex(RuntimeError, 'unexpected_public_origin'):
                public_get(url)

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
