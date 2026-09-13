from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OVERRIDES = ROOT / "data" / "curation" / "reading_aid_overrides.json"
RETRIEVAL = ROOT / "data" / "curation" / "retrieval_coverage.csv"
QUEUE = ROOT / "data" / "curation" / "review_queue.csv"

MANAGING_CARTELS = "CAND-ACADEMIC-2026-09-13-EXTRA-4b57a3081215-001"
STRONG_BY_CONCEALMENT = "CAND-ACADEMIC-2026-09-13-EXTRA-4b57a3081215-002"
MAFIA_LOCAL_INSTITUTIONS = "CAND-ACADEMIC-2026-09-13-EXTRA-4b57a3081215-003"

MANAGING_CARTELS_PDF = "https://link.springer.com/content/pdf/10.1007/s10610-016-9329-7.pdf"
STRONG_BY_CONCEALMENT_PDF = "https://repub.eur.nl/pub/116716/RePub-116716-OA.pdf"
MAFIA_LOCAL_INSTITUTIONS_RECORD = "https://journals.sagepub.com/doi/10.1177/1477370818803050"


class ParallelSearchBatch16Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        cls.overrides = {row["candidateId"]: row for row in payload["records"]}
        with RETRIEVAL.open(newline="", encoding="utf-8-sig") as handle:
            cls.retrieval = {row["candidate_id"]: row for row in csv.DictReader(handle)}
        with QUEUE.open(newline="", encoding="utf-8-sig") as handle:
            cls.queue = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    def test_batch_is_candidate_bound_and_preserves_registered_identity(self) -> None:
        self.assertEqual(self.queue[MANAGING_CARTELS]["doi"], "10.1007/s10610-016-9329-7")
        self.assertEqual(self.queue[STRONG_BY_CONCEALMENT]["doi"], "")
        self.assertEqual(self.queue[MAFIA_LOCAL_INSTITUTIONS]["doi"], "10.1177/1477370818803050")
        self.assertEqual(
            self.queue[STRONG_BY_CONCEALMENT]["title"],
            "Strong by concealment? How secrecy, trust, and social embeddedness facilitate corporate crime",
        )

    def test_verified_final_sources_and_evidence_boundaries_are_recorded(self) -> None:
        expected = {
            MANAGING_CARTELS: ("full_text_intro", MANAGING_CARTELS_PDF, "Evidence basis: full_text"),
            STRONG_BY_CONCEALMENT: ("full_text_intro", STRONG_BY_CONCEALMENT_PDF, "Evidence basis: full_text"),
            MAFIA_LOCAL_INSTITUTIONS: (
                "verified_abstract_source",
                MAFIA_LOCAL_INSTITUTIONS_RECORD,
                "Evidence basis: abstract_only",
            ),
        }
        for candidate_id, (kind, url, evidence) in expected.items():
            record = self.overrides[candidate_id]
            self.assertEqual(record["kind"], kind)
            self.assertEqual(record["sourceUrl"], url)
            self.assertIn(evidence, record["note"])
            self.assertIn("Parallel Search", record["sourceLabel"] + record["note"])
            self.assertLess(len(record["synopsis"].split()), 90)

    def test_full_text_records_are_eligible_for_deterministic_locator_bridge(self) -> None:
        for candidate_id, url in (
            (MANAGING_CARTELS, MANAGING_CARTELS_PDF),
            (STRONG_BY_CONCEALMENT, STRONG_BY_CONCEALMENT_PDF),
        ):
            record = self.overrides[candidate_id]
            self.assertEqual(record["kind"], "full_text_intro")
            self.assertTrue(url.startswith("https://"))
            row = self.retrieval[candidate_id]
            self.assertIn(row["resolution_status"], {"unresolved", "source_link_only", "open_access_landing", "full_text"})
            if row["resolution_status"] == "full_text":
                self.assertEqual(row["full_text_url"], url)
                self.assertIn(url, row["source_urls"])
                self.assertEqual(row["match_confidence"], "high")

    def test_restricted_sage_article_is_not_promoted_to_full_text(self) -> None:
        record = self.overrides[MAFIA_LOCAL_INSTITUTIONS]
        self.assertEqual(record["kind"], "verified_abstract_source")
        self.assertIn("restricted access", record["note"].lower())
        self.assertIn("abstract_only", record["note"])
        row = self.retrieval[MAFIA_LOCAL_INSTITUTIONS]
        self.assertNotEqual(row["full_text_url"].strip(), MAFIA_LOCAL_INSTITUTIONS_RECORD)


if __name__ == "__main__":
    unittest.main()
