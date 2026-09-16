import hashlib
import io
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.enrichment import service_client as client


class EnrichmentReadinessErrorTests(unittest.TestCase):
    def test_authenticated_store_readiness_code_is_reported_without_raw_body(self):
        body = io.BytesIO(b'{"error_code":"additive_schedule_migration_required","private":"never disclose"}')
        error = HTTPError(client.ORIGIN, 500, 'failure', {}, body)
        with patch.dict(os.environ, {'CURATOR_SESSION_SECRET': 'synthetic-test-only-' + 'x' * 40}), \
             patch.object(client._PRIVATE_HTTP, 'open', side_effect=error):
            with self.assertRaisesRegex(RuntimeError, r'enrichment_service_http_500:additive_schedule_migration_required') as caught:
                client.call('verify', expected_commit='a' * 40)
        self.assertNotIn('never disclose', str(caught.exception))

    def test_signed_auth_state_failure_is_reported_as_service_unavailable(self):
        body = io.BytesIO(b'{"error_code":"service_auth_state_unavailable"}')
        error = HTTPError(client.ORIGIN, 503, 'failure', {}, body)
        with patch.dict(os.environ, {'CURATOR_SESSION_SECRET': 'synthetic-test-only-' + 'x' * 40}), \
             patch.object(client._PRIVATE_HTTP, 'open', side_effect=error):
            with self.assertRaisesRegex(RuntimeError, r'^enrichment_service_http_503:service_auth_state_unavailable$'):
                client.call('verify', expected_commit='a' * 40)

    def test_sql_failures_are_classified_without_returning_server_text(self):
        raw = 'SQLITE_ERROR: no such table: private_internal_name'
        body = io.BytesIO(json_bytes({'error_code': raw}))
        error = HTTPError(client.ORIGIN, 500, 'failure', {}, body)
        with patch.dict(os.environ, {'CURATOR_SESSION_SECRET': 'synthetic-test-only-' + 'x' * 40}), \
             patch.object(client._PRIVATE_HTTP, 'open', side_effect=error):
            with self.assertRaisesRegex(RuntimeError, r'^enrichment_service_http_500:store_sql_missing_table$') as caught:
                client.call('verify', expected_commit='a' * 40)
        self.assertNotIn('private_internal_name', str(caught.exception))

    def test_unrecognised_server_error_gets_only_one_way_fingerprint(self):
        raw = 'unexpected private implementation detail'
        fingerprint = hashlib.sha256(raw.encode()).hexdigest()[:12]
        body = io.BytesIO(json_bytes({'error_code': raw}))
        error = HTTPError(client.ORIGIN, 500, 'failure', {}, body)
        with patch.dict(os.environ, {'CURATOR_SESSION_SECRET': 'synthetic-test-only-' + 'x' * 40}), \
             patch.object(client._PRIVATE_HTTP, 'open', side_effect=error):
            with self.assertRaisesRegex(RuntimeError, rf'^enrichment_service_http_500:store_unknown_error_{fingerprint}$') as caught:
                client.call('verify', expected_commit='a' * 40)
        self.assertNotIn(raw, str(caught.exception))


def json_bytes(value):
    import json
    return json.dumps(value, separators=(',', ':')).encode()


if __name__ == '__main__':
    unittest.main()
