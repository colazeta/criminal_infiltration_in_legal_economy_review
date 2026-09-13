import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ParallelSearchSelectedPaperLaneBatch13Tests(unittest.TestCase):
    def test_batch13_adds_three_existing_full_text_candidates_without_scientific_decisions(self) -> None:
        payload = json.loads(
            (ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8")
        )
        records = {row["candidateId"]: row for row in payload["records"]}
        with (ROOT / "data/curation/review_queue.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            queue_ids = {row["candidate_id"] for row in csv.DictReader(handle)}

        anac = "CAND-ACADEMIC-2026-09-10-EXTRA-65282d1dbeff-003"
        suppa = "CAND-ACADEMIC-2026-09-10-EXTRA-65282d1dbeff-004"
        private_ordering = "CAND-ACADEMIC-2026-09-10-EXTRA-8af43493861b-002"

        for candidate in (anac, suppa, private_ordering):
            self.assertIn(candidate, queue_ids)
            row = records[candidate]
            self.assertEqual(row["kind"], "full_text_intro")
            self.assertTrue(row["sourceUrl"].startswith("https://"))
            self.assertNotIn("parallel-search", row["sourceUrl"].lower())
            self.assertLess(len(row["synopsis"]), 900)
            self.assertIn("Parallel Search", row["note"])
            self.assertIn("Evidence basis: full_text", row["note"])
            self.assertNotIn("eligible_", row["note"])

        self.assertIn("anticorruzione.it", records[anac]["sourceUrl"])
        self.assertIn("MPRA_paper_9138.pdf", records[suppa]["sourceUrl"])
        self.assertIn("chicagounbound.uchicago.edu/cgi/viewcontent.cgi", records[private_ordering]["sourceUrl"])
        self.assertIn("blank authors/year", records[private_ordering]["note"])
        self.assertIn("metadata reconciliation", records[private_ordering]["note"])


if __name__ == "__main__":
    unittest.main()
