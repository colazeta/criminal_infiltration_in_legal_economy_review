from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "data/legacy/pre-oa-reset-2026-09-08" / "curation" / "abstract_coverage.csv"
RESOLUTION = ROOT / "data/legacy/pre-oa-reset-2026-09-08" / "curation" / "residual_abstract_resolution.json"


class ResidualAbstractResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        with COVERAGE.open(newline="", encoding="utf-8-sig") as handle:
            self.coverage = list(csv.DictReader(handle))
        self.payload = json.loads(RESOLUTION.read_text(encoding="utf-8"))
        self.records = self.payload["records"]

    def test_registry_exactly_matches_current_needs_web_search_set(self) -> None:
        unresolved = {
            row["candidate_id"]
            for row in self.coverage
            if row["coverage_status"] == "needs_web_search"
        }
        registered = {record["candidateId"] for record in self.records}
        self.assertEqual(unresolved, registered)
        self.assertEqual(len(registered), 23)

    def test_resolution_classes_are_controlled_and_non_existence_is_not_asserted(self) -> None:
        self.assertEqual(self.payload["schemaVersion"], 1)
        allowed = {
            "full_text_or_intro_ready",
            "publisher_summary_ready",
            "metadata_only",
            "known_noise",
        }
        counts = Counter(record["resolutionClass"] for record in self.records)
        self.assertEqual(set(counts), allowed)
        self.assertEqual(counts["full_text_or_intro_ready"], 6)
        self.assertEqual(counts["publisher_summary_ready"], 12)
        self.assertEqual(counts["metadata_only"], 1)
        self.assertEqual(counts["known_noise"], 4)
        for record in self.records:
            self.assertIn(record["resolutionClass"], allowed)
            self.assertIn(
                record["standaloneAbstractStatus"],
                {"not_verified_after_targeted_search", "not_applicable_noise"},
            )
            self.assertNotIn("does_not_exist", record["standaloneAbstractStatus"])
            self.assertTrue(record["sourceUrl"].startswith("https://"))
            self.assertTrue(record["sourceLabel"].strip())
            self.assertTrue(record["nextAction"].strip())
            self.assertTrue(record["note"].strip())
            self.assertIn(record["checkedAt"], {"2026-09-06", "2026-09-07"})

        refreshed = {
            record["candidateId"]: record["checkedAt"]
            for record in self.records
            if record["candidateId"] in {"E0R1-C013", "E0R1-C031"}
        }
        self.assertEqual(refreshed, {"E0R1-C013": "2026-09-07", "E0R1-C031": "2026-09-07"})

    def test_known_noise_is_limited_to_verified_legacy_noise(self) -> None:
        noise = {
            record["candidateId"]
            for record in self.records
            if record["resolutionClass"] == "known_noise"
        }
        self.assertEqual(noise, {"E0R1-C049", "E0R1-C051", "E0R1-C052", "E0R1-C053"})

    def test_review_ready_residuals_are_separate_from_abstract_availability(self) -> None:
        ready = {
            record["candidateId"]
            for record in self.records
            if record["resolutionClass"] in {"full_text_or_intro_ready", "publisher_summary_ready"}
        }
        self.assertEqual(len(ready), 18)
        unresolved = {
            row["candidate_id"]
            for row in self.coverage
            if row["coverage_status"] == "needs_web_search"
        }
        self.assertTrue(ready <= unresolved)


if __name__ == "__main__":
    unittest.main()
