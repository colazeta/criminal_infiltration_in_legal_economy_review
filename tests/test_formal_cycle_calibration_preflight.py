from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.metrics.calibrate_cycle_results import calibrate


ROOT = Path(__file__).resolve().parents[1]


class FormalCycleCalibrationPreflightTests(unittest.TestCase):
    def test_combines_positive_and_boundary_diagnostics(self) -> None:
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
        neighbours = {
            "schema_version": 1,
            "records": [
                {
                    "benchmark_id": "NN1",
                    "title": "Money laundering primer",
                    "year": 2015,
                    "doi": "10.1000/ml",
                    "phenomenon": "money_laundering",
                    "guard_question": "Is relational evidence present?",
                }
            ],
        }
        results = [
            {"title": "Mafias and Firms", "year": 2026},
            {"doi": "https://doi.org/10.1000/ML"},
        ]
        report = calibrate(results, benchmark, neighbours)
        self.assertEqual(report["benchmark"]["recovered"], 1)
        self.assertEqual(report["near_neighbours"]["near_neighbour_hits"], 1)
        self.assertEqual(report["review_required"]["benchmark_misses"], [])
        self.assertEqual(report["review_required"]["near_neighbour_hits"], ["NN1"])

    def test_current_formal_benchmark_is_interpretable_but_not_saturation(self) -> None:
        benchmark = json.loads((ROOT / "docs/methodology/discovery-benchmark.json").read_text(encoding="utf-8"))
        neighbours = json.loads((ROOT / "docs/methodology/discovery-near-neighbours.json").read_text(encoding="utf-8"))
        report = calibrate([], benchmark, neighbours)
        self.assertTrue(report["benchmark"]["interpretable"])
        self.assertEqual(report["benchmark"]["benchmark_size"], 20)
        self.assertIn("sensitivity proxy", report["interpretation"])
        self.assertIn("conceptual-drift diagnostic", report["interpretation"])
        self.assertIn("Neither", report["interpretation"])
        self.assertNotIn("eligible_core", json.dumps(report))
        self.assertNotIn("not_eligible", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
