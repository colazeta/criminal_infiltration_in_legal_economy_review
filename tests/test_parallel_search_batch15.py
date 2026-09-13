from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OVERRIDES = ROOT / "data" / "curation" / "reading_aid_overrides.json"
RETRIEVAL = ROOT / "data" / "curation" / "retrieval_coverage.csv"

DATA_SOURCES = "CAND-ACADEMIC-2026-09-12-EXTRA-38a999646d3f-001"
ATLANTIC_CITY = "CAND-ACADEMIC-2026-09-12-EXTRA-38a999646d3f-003"
ASIAN_MAFIA = "CAND-ACADEMIC-2026-09-12-EXTRA-426cdea055d3-002"

DATA_SOURCES_PDF = "https://www.ncjrs.gov/pdffiles1/Digitization/95266NCJRS.pdf"
ATLANTIC_CITY_PDF = "https://www.ncjrs.gov/pdffiles1/Digitization/55801NCJRS.pdf"
ASIAN_MAFIA_RECORD = (
    "https://www.ojp.gov/ncjrs/virtual-library/abstracts/"
    "chinese-triads-and-japanese-yakuza-how-dangerous-asian-mafia"
)


class ParallelSearchBatch15Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        cls.overrides = {row["candidateId"]: row for row in payload["records"]}
        with RETRIEVAL.open(newline="", encoding="utf-8-sig") as handle:
            cls.retrieval = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    def test_verified_final_sources_are_recorded(self) -> None:
        expected = {
            DATA_SOURCES: ("full_text_intro", DATA_SOURCES_PDF, "Evidence basis: full_text"),
            ATLANTIC_CITY: ("full_text_intro", ATLANTIC_CITY_PDF, "Evidence basis: full_text"),
            ASIAN_MAFIA: ("verified_abstract_source", ASIAN_MAFIA_RECORD, "Evidence basis: abstract_only"),
        }
        for candidate_id, (kind, url, evidence) in expected.items():
            record = self.overrides[candidate_id]
            self.assertEqual(record["kind"], kind)
            self.assertEqual(record["sourceUrl"], url)
            self.assertIn(evidence, record["note"])
            self.assertIn("Parallel Search", record["sourceLabel"] + record["note"])

    def test_abstract_only_record_is_not_promoted_to_full_text(self) -> None:
        row = self.retrieval[ASIAN_MAFIA]
        self.assertNotEqual(row["resolution_status"], "full_text")
        self.assertFalse(row["full_text_url"].strip())

    def test_full_text_overrides_are_eligible_for_deterministic_bridge(self) -> None:
        for candidate_id, url in ((DATA_SOURCES, DATA_SOURCES_PDF), (ATLANTIC_CITY, ATLANTIC_CITY_PDF)):
            record = self.overrides[candidate_id]
            self.assertEqual(record["kind"], "full_text_intro")
            self.assertTrue(url.startswith("https://www.ncjrs.gov/pdffiles1/Digitization/"))
            row = self.retrieval[candidate_id]
            self.assertIn(row["resolution_status"], {"source_link_only", "full_text"})
            if row["resolution_status"] == "full_text":
                self.assertEqual(row["full_text_url"], url)
                self.assertIn(url, row["source_urls"])
                self.assertEqual(row["match_confidence"], "high")


if __name__ == "__main__":
    unittest.main()
