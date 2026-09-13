import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ParallelSearchSelectedPaperLaneBatch11Tests(unittest.TestCase):
    def test_batch11_improves_two_weak_candidates_without_overclaiming(self) -> None:
        payload = json.loads(
            (ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8")
        )
        records = {row["candidateId"]: row for row in payload["records"]}
        with (ROOT / "data/curation/review_queue.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            queue_ids = {row["candidate_id"] for row in csv.DictReader(handle)}

        major = "CAND-ACADEMIC-2026-09-10-EXTRA-f276bc827f57-004"
        sicilian = "CAND-ACADEMIC-2026-09-10-EXTRA-f276bc827f57-005"
        for candidate in (major, sicilian):
            self.assertIn(candidate, queue_ids)
            row = records[candidate]
            self.assertTrue(row["sourceUrl"].startswith("https://"))
            self.assertNotIn("parallel-search", row["sourceUrl"].lower())
            self.assertLess(len(row["synopsis"]), 900)
            self.assertIn("Parallel Search", row["note"])

        major_row = records[major]
        self.assertEqual(major_row["kind"], "full_text_intro")
        self.assertEqual(
            major_row["sourceUrl"],
            "https://dalspace.library.dal.ca/bitstreams/28c9ffcb-3553-4911-8f50-cce77cb8f705/download",
        )
        self.assertIn("NCJ 194003", major_row["note"])
        self.assertIn("Evidence basis: full_text", major_row["note"])
        self.assertIn("private full-text ingestion", major_row["note"])

        sicilian_row = records[sicilian]
        self.assertEqual(sicilian_row["kind"], "publisher_summary")
        self.assertEqual(
            sicilian_row["sourceUrl"],
            "https://www.hup.harvard.edu/books/9780674807426",
        )
        self.assertIn("publisher_summary", sicilian_row["note"])
        self.assertIn("1993/1996", sicilian_row["note"])
        self.assertIn("not_verifiable", sicilian_row["note"])
        self.assertNotIn("Evidence basis: full_text", sicilian_row["note"])


if __name__ == "__main__":
    unittest.main()
