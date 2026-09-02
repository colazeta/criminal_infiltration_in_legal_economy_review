from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "site" / "curator-config.js"
EXPECTED_SECURE_APP_URL = (
    "https://criminal-infiltration-curator.colazeta-research.workers.dev/curate.html"
)


def config_value(source: str, key: str) -> str:
    match = re.search(rf'{re.escape(key)}:\s*"([^\"]*)"', source)
    if not match:
        raise AssertionError(f"Missing {key} in curator public config")
    return match.group(1)


class CuratorPublicEndpointTest(unittest.TestCase):
    def test_pages_exposes_only_verified_worker_console(self) -> None:
        source = CONFIG.read_text(encoding="utf-8")
        self.assertEqual(config_value(source, "apiBaseUrl"), "")
        self.assertEqual(config_value(source, "secureAppUrl"), EXPECTED_SECURE_APP_URL)


if __name__ == "__main__":
    unittest.main()
