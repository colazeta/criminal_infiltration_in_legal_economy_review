import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ParallelSearchSelectedPaperLaneBatch7Tests(unittest.TestCase):
    def test_seventh_batch_preserves_identity_version_and_evidence_boundaries(self):
        payload = json.loads((ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8"))
        records = {row["candidateId"]: row for row in payload["records"]}
        with (ROOT / "data/curation/review_queue.csv").open(encoding="utf-8", newline="") as handle:
            queue_ids = {row["candidate_id"] for row in csv.DictReader(handle)}

        expected = {
            "CAND-ACADEMIC-2026-09-09-014": (
                "uif.bancaditalia.it/pubblicazioni/quaderni/2025/quaderno-32-2025/QAR-32.pdf",
                "full_text_intro",
                "full_text",
            ),
            "CAND-ACADEMIC-2026-09-09-EXTRA-5e31cc756b0e-004": (
                "papers.ssrn.com/sol3/papers.cfm?abstract_id=4960619",
                "verified_abstract_source",
                "abstract_only",
            ),
            "CAND-ACADEMIC-2026-09-09-EXTRA-5e31cc756b0e-011": (
                "cepr.org/publications/dp19322",
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
            self.assertEqual(row["checkedAt"], "2026-09-13")

        loan = records["CAND-ACADEMIC-2026-09-09-014"]
        self.assertIn("UIF 2025 manifestation", loan["note"])
        self.assertIn("not silently substituted", loan["note"])
        self.assertIn("private full-text ingestion", loan["note"])

        godfather = records["CAND-ACADEMIC-2026-09-09-EXTRA-5e31cc756b0e-004"]
        self.assertIn("first posted 29 October 2024", godfather["note"])
        self.assertIn("last revised 25 June 2025", godfather["note"])
        self.assertIn("not_verifiable", godfather["note"])

        predictions = records["CAND-ACADEMIC-2026-09-09-EXTRA-5e31cc756b0e-011"]
        self.assertIn("DP19322", predictions["sourceLabel"])
        self.assertIn("difference-in-discontinuities", predictions["note"])
        self.assertIn("not_verifiable", predictions["note"])


if __name__ == "__main__":
    unittest.main()
