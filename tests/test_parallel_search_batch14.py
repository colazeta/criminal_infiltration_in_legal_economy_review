from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OVERRIDES = ROOT / "data" / "curation" / "reading_aid_overrides.json"
RETRIEVAL = ROOT / "data" / "curation" / "retrieval_coverage.csv"

MAFIA_TIES = "CAND-ACADEMIC-2026-09-12-EXTRA-3ad3ee04659d-002"
SHAPING_SPACE = "CAND-ACADEMIC-2026-09-12-EXTRA-335f7df7ae34-001"
TARGETING_REVENUE = "CAND-ACADEMIC-2026-09-13-EXTRA-a6766e6649ed-003"


class ParallelSearchBatch14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        cls.overrides = {row["candidateId"]: row for row in payload["records"]}
        with RETRIEVAL.open(newline="", encoding="utf-8-sig") as handle:
            cls.retrieval = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    def test_final_sources_are_candidate_bound(self) -> None:
        expected = {
            MAFIA_TIES: (
                "verified_abstract_source",
                "https://www.francoangeli.it/riviste/SchedaRivista.aspx?DOI=10.3280/fr202519624",
            ),
            SHAPING_SPACE: (
                "full_text_intro",
                "https://pmc.ncbi.nlm.nih.gov/articles/PMC8024936/",
            ),
            TARGETING_REVENUE: (
                "verified_abstract_source",
                "https://academic.oup.com/jleo/article/39/3/722/6552195",
            ),
        }
        for candidate_id, (kind, source_url) in expected.items():
            record = self.overrides[candidate_id]
            self.assertEqual(record["kind"], kind)
            self.assertEqual(record["sourceUrl"], source_url)
            self.assertIn("Parallel Search", record["sourceLabel"])

    def test_only_verified_full_text_is_promoted(self) -> None:
        full_text = self.retrieval[SHAPING_SPACE]
        self.assertEqual(full_text["resolution_status"], "full_text")
        self.assertEqual(full_text["full_text_url"], "https://pmc.ncbi.nlm.nih.gov/articles/PMC8024936/")
        self.assertIn("Curator verified full text", full_text["resolution_sources"])

        self.assertNotEqual(self.retrieval[MAFIA_TIES]["resolution_status"], "full_text")
        self.assertNotEqual(self.retrieval[TARGETING_REVENUE]["resolution_status"], "full_text")

    def test_public_notes_keep_scientific_and_version_boundaries(self) -> None:
        self.assertIn("abstract_only", self.overrides[MAFIA_TIES]["note"])
        self.assertIn("Evidence basis: full_text", self.overrides[SHAPING_SPACE]["note"])
        self.assertIn("2018 working-paper manifestation", self.overrides[TARGETING_REVENUE]["note"])
        self.assertIn("not silently substituted", self.overrides[TARGETING_REVENUE]["note"])


if __name__ == "__main__":
    unittest.main()
