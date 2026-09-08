import unittest
from unittest.mock import patch

from scripts.review_v2 import prepare_cloudflare as provisioning


class AccountSelectionTests(unittest.TestCase):
    def test_missing_configuration_selects_only_a_unique_authorised_account(self):
        with patch.dict(provisioning.os.environ, {"CLOUDFLARE_ACCOUNT_ID": ""}), patch.object(provisioning, "_resolved_account", None):
            with patch.object(provisioning, "request_api", return_value=[{"id": "a" * 32}]) as request:
                self.assertEqual(provisioning.resolve_account(), "a" * 32)
                request.assert_called_once_with("accounts?per_page=50&page=1")
        with patch.dict(provisioning.os.environ, {"CLOUDFLARE_ACCOUNT_ID": ""}), patch.object(provisioning, "_resolved_account", None):
            with patch.object(provisioning, "request_api", return_value=[{"id": "a" * 32}, {"id": "b" * 32}]):
                with self.assertRaisesRegex(RuntimeError, "unique Cloudflare account"):
                    provisioning.resolve_account()


if __name__ == "__main__":
    unittest.main()
