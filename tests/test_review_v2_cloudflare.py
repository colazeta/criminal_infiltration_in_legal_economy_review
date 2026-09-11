import unittest
import tempfile
import json
from pathlib import Path
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

    def test_storage_only_provisioning_never_requires_discovery_queues(self):
        calls = []
        def fake_api(resource, **kwargs):
            calls.append(resource)
            if resource.startswith("d1/database?"): return [{"name": provisioning.NAME, "uuid": "test-db"}]
            if resource.endswith("/query"):
                if "sqlite_master" in kwargs.get("payload", {}).get("sql", ""): return [{"results": []}]
                return [{"results": []}]
            if resource == "r2/buckets": return {"buckets": [{"name": provisioning.NAME}]}
            if resource.endswith("/domains/managed"): return {"enabled": False}
            if resource.endswith("/domains/custom"): return {"domains": []}
            raise AssertionError(resource)
        with tempfile.TemporaryDirectory() as folder, patch.object(provisioning, "api", side_effect=fake_api):
            output = Path(folder) / "bindings.json"
            provisioning.prepare(output, storage_only=True)
            data = json.loads(output.read_text())
            self.assertNotIn("queues", data)
            self.assertIn("d1_databases", data)
            self.assertFalse(any("queues" in value for value in calls))


if __name__ == "__main__":
    unittest.main()
