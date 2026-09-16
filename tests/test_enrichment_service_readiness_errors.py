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

    def test_unrecognised_server_error_remains_generic(self):
        body = io.BytesIO(b'{"error_code":"unexpected_private_detail"}')
        error = HTTPError(client.ORIGIN, 500, 'failure', {}, body)
        with patch.dict(os.environ, {'CURATOR_SESSION_SECRET': 'synthetic-test-only-' + 'x' * 40}), \
             patch.object(client._PRIVATE_HTTP, 'open', side_effect=error):
            with self.assertRaisesRegex(RuntimeError, r'^enrichment_service_http_500$'):
                client.call('verify', expected_commit='a' * 40)


if __name__ == '__main__':
    unittest.main()
