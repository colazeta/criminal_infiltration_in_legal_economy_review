from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.metrics.evaluate_discovery_benchmark import evaluate, normalise_doi, normalise_title


ROOT = Path(__file__).resolve().parents[1]


class DiscoveryBenchmarkTests(unittest.TestCase):
    def test_identifier_and_title_normalisation(self) -> None:
        self.assertEqual(normalise_doi("https://doi.org/10.1000/ABC.1"), "10.1000/abc.1")
        self.assertEqual(normalise_title("Mafia-Type: firms’ control"), "mafia type firms control")

    def test_doi_match_takes_priority(self) -> None:
        benchmark = {
            "schema_version": 1,
            "minimum_interpretable_size": 1,
            "records": [
                {
                    "benchmark_id": "B1",
                    "title": "Different display title",
                    "year": 2026,
                    "doi": "10.1000/test",
                    "calibration_uses": ["formal_search"],
                }
            ],
        }
        report = evaluate(benchmark, [{"title": "Other", "year": 2010, "doi": "https://doi.org/10.1000/TEST"}], "formal_search")
        self.assertEqual(report["recovered"], 1)
        self.assertEqual(report["proxy_recall"], 1.0)

    def test_title_year_fallback_is_exact_and_conservative(self) -> None:
        benchmark = {
            "schema_version": 1,
            "minimum_interpretable_size": 1,
            "records": [
                {
                    "benchmark_id": "B1",
                    "title": "Mafias and Firms",
                    "year": 2026,
                    "doi": None,
                    "calibration_uses": ["formal_search"],
                }
            ],
        }
        hit = evaluate(benchmark, [{"title": "Mafias and Firms", "year": 2026}], "formal_search")
        miss = evaluate(benchmark, [{"title": "Mafias and Firms", "year": 2025}], "formal_search")
        self.assertEqual(hit["recovered"], 1)
        self.assertEqual(miss["recovered"], 0)

    def test_bootstrap_refuses_interpretable_recall_claim(self) -> None:
        benchmark = json.loads((ROOT / "docs/methodology/discovery-benchmark.json").read_text(encoding="utf-8"))
        report = evaluate(benchmark, [], "formal_search")
        self.assertLess(report["benchmark_size"], report["minimum_interpretable_size"])
        self.assertFalse(report["interpretable"])
        self.assertIsNone(report["proxy_recall"])
        self.assertIn("Bootstrap calibration only", report["interpretation"])

    def test_benchmark_contains_no_eligibility_decision_field(self) -> None:
        benchmark = json.loads((ROOT / "docs/methodology/discovery-benchmark.json").read_text(encoding="utf-8"))
        for record in benchmark["records"]:
            self.assertNotIn("decision", record)
            self.assertNotIn("eligible", record)
            self.assertIn(record["basis"], {"canonical_seed", "canonical_review_record", "daily_plausible_core"})


if __name__ == "__main__":
    unittest.main()
