import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ParallelSearchSelectedPaperLaneBatch12Tests(unittest.TestCase):
    def test_batch12_improves_three_existing_candidates_with_bounded_evidence(self) -> None:
        payload = json.loads(
            (ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8")
        )
        records = {row["candidateId"]: row for row in payload["records"]}
        with (ROOT / "data/curation/review_queue.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            queue_ids = {row["candidate_id"] for row in csv.DictReader(handle)}

        covid = "CAND-ACADEMIC-2026-09-09-EXTRA-6b5b5e038ac4-030"
        sciarrone = "CAND-ACADEMIC-2026-09-10-EXTRA-f276bc827f57-007"
        yakuza = "CAND-ACADEMIC-2026-09-10-007"
        for candidate in (covid, sciarrone, yakuza):
            self.assertIn(candidate, queue_ids)
            row = records[candidate]
            self.assertTrue(row["sourceUrl"].startswith("https://"))
            self.assertNotIn("parallel-search", row["sourceUrl"].lower())
            self.assertLess(len(row["synopsis"]), 900)
            self.assertIn("Parallel Search", row["note"])
            self.assertNotIn("eligible_", row["note"])

        covid_row = records[covid]
        self.assertEqual(covid_row["kind"], "full_text_intro")
        self.assertEqual(
            covid_row["sourceUrl"],
            "https://www.bancaditalia.it/pubblicazioni/temi-discussione/2025/2025-1502/en_tema_1502.pdf",
        )
        self.assertIn("Evidence basis: full_text", covid_row["note"])
        self.assertIn("2023 IFS", covid_row["note"])
        self.assertIn("private full-text ingestion", covid_row["note"])

        sciarrone_row = records[sciarrone]
        self.assertEqual(sciarrone_row["kind"], "verified_abstract_source")
        self.assertEqual(sciarrone_row["sourceUrl"], "https://www.rivisteweb.it/doi/10.1425/23230")
        self.assertIn("Evidence basis: abstract_only", sciarrone_row["note"])
        self.assertIn("not_verifiable", sciarrone_row["note"])
        self.assertNotIn("Evidence basis: full_text", sciarrone_row["note"])

        yakuza_row = records[yakuza]
        self.assertEqual(yakuza_row["kind"], "verified_abstract_source")
        self.assertIn("ojp.gov/ncjrs/virtual-library", yakuza_row["sourceUrl"])
        self.assertIn("NCJ 169383", yakuza_row["note"])
        self.assertIn("Evidence basis: abstract_only", yakuza_row["note"])
        self.assertIn("no download is available", yakuza_row["note"])
        self.assertIn("not_verifiable", yakuza_row["note"])
        self.assertNotIn("Evidence basis: full_text", yakuza_row["note"])


if __name__ == "__main__":
    unittest.main()
