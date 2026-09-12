import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ParallelSearchSelectedPaperLaneBatch6Tests(unittest.TestCase):
    def test_sixth_batch_preserves_source_and_evidence_boundaries(self):
        payload = json.loads((ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8"))
        records = {row["candidateId"]: row for row in payload["records"]}
        with (ROOT / "data/curation/review_queue.csv").open(encoding="utf-8", newline="") as handle:
            queue_ids = {row["candidate_id"] for row in csv.DictReader(handle)}

        expected = {
            "CAND-ACADEMIC-2026-09-09-EXTRA-85e203d4eb5a-004": (
                "sk.sagepub.com",
                "publisher_summary",
                "publisher_summary",
            ),
            "CAND-ACADEMIC-2026-09-09-EXTRA-5e31cc756b0e-001": (
                "www.ojp.gov/pdffiles1/Digitization/2300NCJRS.pdf",
                "full_text_intro",
                "full_text",
            ),
            "CAND-ACADEMIC-2026-09-09-EXTRA-85e203d4eb5a-009": (
                "publicatt.unicatt.it",
                "verified_abstract_source",
                "abstract_only",
            ),
        }
        for candidate, (source_fragment, kind, coverage) in expected.items():
            self.assertIn(candidate, queue_ids)
            row = records[candidate]
            self.assertEqual(row["kind"], kind)
            self.assertTrue(row["sourceUrl"].startswith("https://"))
            self.assertIn(source_fragment, row["sourceUrl"])
            self.assertNotIn("parallel-search", row["sourceUrl"].lower())
            self.assertLess(len(row["synopsis"]), 900)
            self.assertIn("Parallel Search", row["note"])
            self.assertIn(coverage, row["note"])

        sage = records["CAND-ACADEMIC-2026-09-09-EXTRA-85e203d4eb5a-004"]
        self.assertIn("10.4135/9781506305110.n10", sage["note"])
        self.assertIn("not_verifiable", sage["note"])

        bers = records["CAND-ACADEMIC-2026-09-09-EXTRA-5e31cc756b0e-001"]
        self.assertIn("NCJ 2300", bers["note"])
        self.assertIn("Evidence basis: full_text", bers["note"])

        riccardi = records["CAND-ACADEMIC-2026-09-09-EXTRA-85e203d4eb5a-009"]
        self.assertIn("pages 119–140", riccardi["note"])
        self.assertIn("not silently added or reconciled", riccardi["note"])
        self.assertIn("not_verifiable", riccardi["note"])


if __name__ == "__main__":
    unittest.main()
