import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ParallelSearchSelectedPaperLaneBatch9Tests(unittest.TestCase):
    def test_batch9_records_are_candidate_bound_and_source_grounded(self) -> None:
        queue = (ROOT / "data/curation/review_queue.csv").read_text(encoding="utf-8-sig")
        payload = json.loads((ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8"))
        records = {row["candidateId"]: row for row in payload["records"]}

        expected = {
            "CAND-ACADEMIC-2026-09-09-EXTRA-8e1caef4c376-002": (
                "full_text_intro",
                "https://management-aims.com/index.php/mgmt/article/download/3955/9677",
                "Evidence basis: full_text",
            ),
            "CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-017": (
                "full_text_intro",
                "https://riviste.unimi.it/index.php/cross/article/download/5/pdf/35200",
                "Evidence basis: full_text",
            ),
            "CAND-ACADEMIC-2026-09-09-EXTRA-8e1caef4c376-004": (
                "verified_abstract_source",
                "https://dspace.library.uu.nl/handle/1874/414369",
                "abstract_only",
            ),
        }

        for candidate_id, (kind, source_url, evidence_marker) in expected.items():
            self.assertIn(candidate_id, queue)
            self.assertIn(candidate_id, records)
            record = records[candidate_id]
            self.assertEqual(record["kind"], kind)
            self.assertEqual(record["sourceUrl"], source_url)
            self.assertEqual(record["checkedAt"], "2026-09-13")
            self.assertIn("Parallel Search", record["sourceLabel"])
            self.assertIn(evidence_marker, record["note"])
            self.assertNotIn("parallel", record["sourceUrl"].lower())

    def test_netherlands_record_does_not_overclaim_direct_full_text(self) -> None:
        payload = json.loads((ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8"))
        records = {row["candidateId"]: row for row in payload["records"]}
        record = records["CAND-ACADEMIC-2026-09-09-EXTRA-8e1caef4c376-004"]
        self.assertEqual(record["kind"], "verified_abstract_source")
        self.assertIn("stable direct bitstream locator was not independently verified", record["note"])
        self.assertIn("not_verifiable", record["note"])


if __name__ == "__main__":
    unittest.main()
