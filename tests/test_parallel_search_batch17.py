from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OVERRIDES = ROOT / "data" / "curation" / "reading_aid_overrides.json"
RETRIEVAL = ROOT / "data" / "curation" / "retrieval_coverage.csv"
ABSTRACT = ROOT / "data" / "curation" / "abstract_coverage.csv"
QUEUE = ROOT / "data" / "curation" / "review_queue.csv"

CAPTURED_POLITICIANS = "CAND-ACADEMIC-2026-09-13-EXTRA-4b57a3081215-004"
MAFIA_STRATEGIES = "CAND-ACADEMIC-2026-09-13-EXTRA-4b57a3081215-005"
NEUTRALIZING_TENTACLES = "CAND-ACADEMIC-2026-09-13-EXTRA-4b57a3081215-006"

CAPTURED_POLITICIANS_RECORD = "https://academic.oup.com/jleo/article/38/3/774/6409959"
MAFIA_STRATEGIES_RECORD = "https://cris.unibo.it/handle/11585/1029770"
NEUTRALIZING_TENTACLES_RECORD = "https://www.sciencedirect.com/science/article/pii/S0167268124001628"


class ParallelSearchBatch17Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        cls.overrides = {row["candidateId"]: row for row in payload["records"]}
        with RETRIEVAL.open(newline="", encoding="utf-8-sig") as handle:
            cls.retrieval = {row["candidate_id"]: row for row in csv.DictReader(handle)}
        with ABSTRACT.open(newline="", encoding="utf-8-sig") as handle:
            cls.abstract = {row["candidate_id"]: row for row in csv.DictReader(handle)}
        with QUEUE.open(newline="", encoding="utf-8-sig") as handle:
            cls.queue = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    def test_batch_is_candidate_bound_and_preserves_registered_dois(self) -> None:
        self.assertEqual(self.queue[CAPTURED_POLITICIANS]["doi"], "10.1093/jleo/ewab015")
        self.assertEqual(self.queue[MAFIA_STRATEGIES]["doi"], "10.1177/00323217251384494")
        self.assertEqual(self.queue[NEUTRALIZING_TENTACLES]["doi"], "10.1016/j.jebo.2024.04.027")

    def test_final_sources_and_abstract_only_boundaries_are_recorded(self) -> None:
        expected = {
            CAPTURED_POLITICIANS: CAPTURED_POLITICIANS_RECORD,
            MAFIA_STRATEGIES: MAFIA_STRATEGIES_RECORD,
            NEUTRALIZING_TENTACLES: NEUTRALIZING_TENTACLES_RECORD,
        }
        for candidate_id, url in expected.items():
            record = self.overrides[candidate_id]
            self.assertEqual(record["kind"], "verified_abstract_source")
            self.assertEqual(record["sourceUrl"], url)
            self.assertIn("Evidence basis: abstract_only", record["note"])
            self.assertIn("Parallel Search", record["sourceLabel"] + record["note"])
            self.assertLess(len(record["synopsis"].split()), 90)

    def test_verified_sources_are_materialized_in_abstract_coverage(self) -> None:
        expected = {
            CAPTURED_POLITICIANS: CAPTURED_POLITICIANS_RECORD,
            MAFIA_STRATEGIES: MAFIA_STRATEGIES_RECORD,
            NEUTRALIZING_TENTACLES: NEUTRALIZING_TENTACLES_RECORD,
        }
        for candidate_id, url in expected.items():
            row = self.abstract[candidate_id]
            self.assertEqual(row["abstract_status"], "available")
            self.assertEqual(row["abstract_kind"], "verified_abstract_source")
            self.assertEqual(row["abstract_source_url"], url)

    def test_abstract_only_records_are_not_promoted_to_full_text(self) -> None:
        for candidate_id, source_url in (
            (CAPTURED_POLITICIANS, CAPTURED_POLITICIANS_RECORD),
            (MAFIA_STRATEGIES, MAFIA_STRATEGIES_RECORD),
            (NEUTRALIZING_TENTACLES, NEUTRALIZING_TENTACLES_RECORD),
        ):
            row = self.retrieval[candidate_id]
            self.assertNotEqual(row["full_text_url"].strip(), source_url)

    def test_version_and_access_limits_remain_explicit(self) -> None:
        self.assertIn("working-paper", self.overrides[CAPTURED_POLITICIANS]["note"])
        self.assertIn("restricted access", self.overrides[MAFIA_STRATEGIES]["note"].lower())
        self.assertIn("working-paper", self.overrides[NEUTRALIZING_TENTACLES]["note"])


if __name__ == "__main__":
    unittest.main()
