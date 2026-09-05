from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ResearchStatsDiagnosticsTests(unittest.TestCase):
    def test_source_yield_is_derived_without_schema_change(self) -> None:
        javascript = (ROOT / "site/stats.js").read_text(encoding="utf-8")
        self.assertIn("safeRate(row.candidateHits, row.uniqueResults)", javascript)
        self.assertIn("safeRate(row.exclusiveCandidates, row.candidateHits)", javascript)
        self.assertIn("resa ${displayPercent(candidateYield)}", javascript)
        self.assertIn("quota ${displayPercent(exclusiveShare)}", javascript)

    def test_stale_ledger_is_presented_as_operational_not_scientific(self) -> None:
        javascript = (ROOT / "site/stats.js").read_text(encoding="utf-8")
        self.assertIn("dataAgeDays", javascript)
        self.assertIn("anomalia operativa, non uno zero scientifico", javascript)
        self.assertNotIn("saturation", javascript.lower())


if __name__ == "__main__":
    unittest.main()
