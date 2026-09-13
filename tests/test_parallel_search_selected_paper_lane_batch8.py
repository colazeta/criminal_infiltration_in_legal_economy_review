import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ParallelSearchSelectedPaperLaneBatch8Tests(unittest.TestCase):
    def test_eighth_batch_preserves_identity_dates_and_evidence_boundaries(self):
        payload = json.loads((ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8"))
        records = {row["candidateId"]: row for row in payload["records"]}
        with (ROOT / "data/curation/review_queue.csv").open(encoding="utf-8", newline="") as handle:
            queue_ids = {row["candidate_id"] for row in csv.DictReader(handle)}

        expected = {
            "CAND-ACADEMIC-2026-09-09-EXTRA-5e31cc756b0e-013": (
                "taylorfrancis.com/chapters/edit/10.4324/9781315640617-2/organised-criminals-legal-economy-giulia-berlusconi",
                "review_synopsis",
                "publisher/institutional summary",
            ),
            "CAND-ACADEMIC-2026-09-10-003": (
                "publicsafety.gc.ca/cnt/rsrcs/pblctns/rgnzd-crm-brf-27/rgnzd-crm-brf-27-eng.pdf",
                "full_text_intro",
                "full_text",
            ),
            "CAND-ACADEMIC-2026-09-09-EXTRA-6b5b5e038ac4-004": (
                "rand.org/content/dam/rand/pubs/reports/2007/R3525.pdf",
                "full_text_intro",
                "full_text",
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

        berlusconi = records["CAND-ACADEMIC-2026-09-09-EXTRA-5e31cc756b0e-013"]
        self.assertIn("2016", berlusconi["note"])
        self.assertIn("2017", berlusconi["note"])
        self.assertIn("not silently reconciled", berlusconi["note"])
        self.assertIn("not_verifiable", berlusconi["note"])

        canada = records["CAND-ACADEMIC-2026-09-10-003"]
        self.assertIn("21 December 2018", canada["note"])
        self.assertIn("does not invent missing authorship", canada["note"])
        self.assertIn("private full-text ingestion", canada["note"])

        rand = records["CAND-ACADEMIC-2026-09-09-EXTRA-6b5b5e038ac4-004"]
        self.assertIn("R-3525-NIJ", rand["note"])
        self.assertIn("October 1987", rand["note"])
        self.assertIn("private full-text ingestion", rand["note"])


if __name__ == "__main__":
    unittest.main()
