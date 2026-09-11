"""No network requests and no production credentials in service-client tests."""
import contextlib
import io
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from scripts.enrichment import service_client as client

class EnrichmentServiceTests(unittest.TestCase):
    def test_failed_record_is_not_successful_cli(self):
        with patch('sys.argv',['service','run','--expected-commit','a'*40]),patch.object(client,'call',return_value={'status':'failed','error_code':'registry_unavailable'}),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError,'enrichment_job_not_successful'): client.main()

    def test_successful_record_passes_cli(self):
        with patch('sys.argv',['service','run','--expected-commit','a'*40]),patch.object(client,'call',return_value={'status':'completed'}),contextlib.redirect_stdout(io.StringIO()):
            client.main()

    def test_server_body_is_not_disclosed(self):
        error=HTTPError(client.ORIGIN,403,'Denied',{},io.BytesIO(b'private text never logged'))
        with patch.dict(os.environ,{'CURATOR_SESSION_SECRET':'synthetic-test-only-'+'x'*40}),patch.object(client._PRIVATE_HTTP,'open',side_effect=error):
            with self.assertRaisesRegex(RuntimeError,'enrichment_service_http_403:non_json_response') as caught: client.call('verify',expected_commit='a'*40)
            self.assertNotIn('private text',str(caught.exception))

    def test_request_identity_and_redirect_policy(self):
        with patch.dict(os.environ,{'CURATOR_SESSION_SECRET':'synthetic-test-only-'+'x'*40}),patch.object(client._PRIVATE_HTTP,'open',return_value=io.BytesIO(b'{"verified":true}')) as opening:
            self.assertTrue(client.call('verify',expected_commit='a'*40)['verified'])
            request=opening.call_args.args[0]
            self.assertEqual(request.get_header('User-agent'),'cile-enrichment-service/1.0')
            self.assertEqual(request.get_header('Accept'),'application/json')
            self.assertFalse(request.has_header('Authorization'))
            with self.assertRaisesRegex(RuntimeError,'service_redirect_refused'):
                client.NoRedirect().redirect_request(None,None,302,'',{},'https://unapproved.example')
