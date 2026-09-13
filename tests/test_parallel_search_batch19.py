from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OVERRIDES = ROOT / "data" / "curation" / "reading_aid_overrides.json"
RETRIEVAL = ROOT / "data" / "curation" / "retrieval_coverage.csv"
ABSTRACTS = ROOT / "data" / "curation" / "abstract_coverage.csv"
QUEUE = ROOT / "data" / "curation" / "review_queue.csv"

EXTORTION = "CAND-ACADEMIC-2026-09-13-EXTRA-a5ca7bf0f145-001"
ENABLERS = "CAND-ACADEMIC-2026-09-13-EXTRA-c8d693f88061-002"
CAPTURE = "CAND-ACADEMIC-2026-09-13-EXTRA-4b57a3081215-007"

EXTORTION_PDF = "https://iris.unipa.it/retrieve/8ac4a071-9d68-445d-bb6b-d9348085c017/1-s2.0-S0147596723000501-main.pdf"
ENABLERS_PMC = "https://pmc.ncbi.nlm.nih.gov/articles/PMC7689635/"
CAPTURE_CEPR = "https://cepr.org/publications/dp21805"


class ParallelSearchBatch19Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        cls.overrides = {row["candidateId"]: row for row in payload["records"]}
        with RETRIEVAL.open(newline="", encoding="utf-8-sig") as handle:
            cls.retrieval = {row["candidate_id"]: row for row in csv.DictReader(handle)}
        with ABSTRACTS.open(newline="", encoding="utf-8-sig") as handle:
            cls.abstracts = {row["candidate_id"]: row for row in csv.DictReader(handle)}
        with QUEUE.open(newline="", encoding="utf-8-sig") as handle:
            cls.queue = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    def test_batch_is_candidate_bound_and_preserves_registered_identity(self) -> None:
        self.assertEqual(self.queue[EXTORTION]["doi"], "")
        self.assertEqual(self.queue[EXTORTION]["year"], "2023")
        self.assertEqual(self.queue[ENABLERS]["doi"], "10.1007/s12117-020-09401-y")
        self.assertEqual(self.queue[ENABLERS]["authors"], "Michael Levi")
        self.assertEqual(self.queue[CAPTURE]["doi"], "")
        self.assertEqual(self.queue[CAPTURE]["year"], "")

    def test_verified_sources_and_evidence_boundaries_are_recorded(self) -> None:
        expected = {
            EXTORTION: ("full_text_intro", EXTORTION_PDF, "Evidence basis: full_text"),
            ENABLERS: ("full_text_intro", ENABLERS_PMC, "Evidence basis: full_text"),
            CAPTURE: ("verified_abstract_source", CAPTURE_CEPR, "Evidence basis: abstract_only"),
        }
        for candidate_id, (kind, url, evidence) in expected.items():
            record = self.overrides[candidate_id]
            self.assertEqual(record["kind"], kind)
            self.assertEqual(record["sourceUrl"], url)
            self.assertIn(evidence, record["note"])
            self.assertIn("Parallel Search", record["sourceLabel"] + record["note"])
            self.assertLess(len(record["synopsis"].split()), 90)

    def test_verified_full_text_is_materialized_with_exact_locators(self) -> None:
        for candidate_id, url in ((EXTORTION, EXTORTION_PDF), (ENABLERS, ENABLERS_PMC)):
            row = self.retrieval[candidate_id]
            self.assertEqual(row["resolution_status"], "full_text")
            self.assertEqual(row["full_text_url"], url)
            self.assertIn(url, row["source_urls"])
            self.assertEqual(row["match_confidence"], "high")

    def test_cepr_record_stays_abstract_only(self) -> None:
        self.assertEqual(self.overrides[CAPTURE]["kind"], "verified_abstract_source")
        self.assertIn("Discussion Paper 21805", self.overrides[CAPTURE]["note"])
        self.assertEqual(self.abstracts[CAPTURE]["coverage_status"], "available")
        self.assertEqual(self.abstracts[CAPTURE]["source_url"], CAPTURE_CEPR)
        self.assertEqual(self.retrieval[CAPTURE]["resolution_status"], "unresolved")
        self.assertEqual(self.retrieval[CAPTURE]["full_text_url"].strip(), "")

    def test_extortion_working_paper_remains_a_distinct_manifestation(self) -> None:
        note = self.overrides[EXTORTION]["note"]
        self.assertIn("2019 working-paper manifestation", note)
        self.assertIn("not silently substituted", note)


if __name__ == "__main__":
    unittest.main()
