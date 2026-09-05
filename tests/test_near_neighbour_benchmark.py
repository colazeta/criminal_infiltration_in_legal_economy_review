from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.metrics.evaluate_near_neighbours import evaluate


ROOT = Path(__file__).resolve().parents[1]


class NearNeighbourBenchmarkTests(unittest.TestCase):
    def test_set_covers_required_adjacent_phenomena_without_decisions(self) -> None:
        payload = json.loads((ROOT / "docs/methodology/discovery-near-neighbours.json").read_text(encoding="utf-8"))
        records = payload["records"]
        phenomena = {record["phenomenon"] for record in records}
        self.assertGreaterEqual(len(records), 10)
        self.assertIn("money_laundering", phenomena)
        self.assertIn("corruption_procurement_risk", phenomena)
        self.assertIn("passive_investment_and_asset_conversion", phenomena)
        self.assertIn("corporate_crime", phenomena)
        for record in records:
            self.assertTrue(record["guard_question"].endswith("?"))
            self.assertNotIn("decision", record)
            self.assertNotIn("eligible", record)
            self.assertNotIn("excluded", record)

    def test_drift_evaluator_does_not_label_hits_as_false_positives(self) -> None:
        neighbours = {
            "schema_version": 1,
            "records": [
                {
                    "benchmark_id": "NN1",
                    "title": "Money laundering primer",
                    "year": 2020,
                    "doi": "10.1000/example",
                    "phenomenon": "money_laundering",
                    "guard_question": "Is relational evidence present?",
                }
            ],
        }
        report = evaluate(neighbours, [{"doi": "https://doi.org/10.1000/EXAMPLE"}])
        self.assertEqual(report["near_neighbour_hits"], 1)
        self.assertEqual(report["near_neighbour_hit_share"], 1.0)
        self.assertIn("not a false positive", report["interpretation"])
        self.assertIn("not", report["interpretation"].lower())
        self.assertNotIn("precision", report.keys())

    def test_current_neighbours_do_not_overlap_discovery_calibration_ids(self) -> None:
        neighbours = json.loads((ROOT / "docs/methodology/discovery-near-neighbours.json").read_text(encoding="utf-8"))
        positive = json.loads((ROOT / "docs/methodology/discovery-benchmark.json").read_text(encoding="utf-8"))
        neighbour_dois = {str(record.get("doi") or "").lower() for record in neighbours["records"] if record.get("doi")}
        positive_dois = {str(record.get("doi") or "").lower() for record in positive["records"] if record.get("doi")}
        self.assertFalse(neighbour_dois & positive_dois)


if __name__ == "__main__":
    unittest.main()
