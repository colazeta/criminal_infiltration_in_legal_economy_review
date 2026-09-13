import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ParallelSearchBatch14Tests(unittest.TestCase):
    def test_batch14_is_candidate_bound_and_evidence_aware(self):
        payload = json.loads((ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8"))
        records = {row["candidateId"]: row for row in payload["records"]}
        with (ROOT / "data/curation/review_queue.csv").open(encoding="utf-8", newline="") as handle:
            queue_ids = {row["candidate_id"] for row in csv.DictReader(handle)}

        expected = {
            "CAND-ACADEMIC-2026-09-12-EXTRA-3ad3ee04659d-002": (
                "www.francoangeli.it",
                "verified_abstract_source",
                "abstract_only",
            ),
            "CAND-ACADEMIC-2026-09-12-EXTRA-335f7df7ae34-001": (
                "pmc.ncbi.nlm.nih.gov",
                "full_text_intro",
                "full_text",
            ),
            "CAND-ACADEMIC-2026-09-11-EXTRA-61e4d03af5c4-001": (
                "series.francoangeli.it",
                "full_text_intro",
                "full_text",
            ),
        }

        for candidate, (host, kind, coverage) in expected.items():
            self.assertIn(candidate, queue_ids)
            row = records[candidate]
            self.assertEqual(row["kind"], kind)
            self.assertTrue(row["sourceUrl"].startswith("https://"))
            self.assertIn(host, row["sourceUrl"])
            self.assertNotIn("parallel-search", row["sourceUrl"].lower())
            self.assertLess(len(row["synopsis"]), 900)
            self.assertIn("Parallel Search", row["note"])
            self.assertIn(coverage, row["note"])

        financial = records["CAND-ACADEMIC-2026-09-12-EXTRA-3ad3ee04659d-002"]
        self.assertIn("10.3280/fr202519624", financial["note"])
        self.assertIn("purchase-controlled", financial["note"])
        self.assertIn("not_verifiable", financial["note"])

        shaping = records["CAND-ACADEMIC-2026-09-12-EXTRA-335f7df7ae34-001"]
        self.assertIn("10.1007/s12117-021-09415-0", shaping["note"])
        self.assertIn("private full-text ingestion", shaping["note"])

        mafia_firm = records["CAND-ACADEMIC-2026-09-11-EXTRA-61e4d03af5c4-001"]
        self.assertIn("FrancoAngeli Open Access", mafia_firm["sourceLabel"])
        self.assertIn("private full-text retention", mafia_firm["note"])


if __name__ == "__main__":
    unittest.main()
