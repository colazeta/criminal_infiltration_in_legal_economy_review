from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CuratorAccessLabelTests(unittest.TestCase):
    def test_full_text_locator_is_not_presented_as_verified_access(self) -> None:
        javascript = (ROOT / "site/curator-resolved-link.js").read_text(encoding="utf-8")
        self.assertIn("Full text pubblico verificato", javascript)
        self.assertIn("Locator full text risolto · accesso non verificato", javascript)
        self.assertIn("Apri full text verificato", javascript)
        self.assertIn("Apri locator full text", javascript)
        self.assertIn('payload?.accessStatus === "open"', javascript)
        self.assertIn("dataset.accessStatus", javascript)


if __name__ == "__main__":
    unittest.main()
