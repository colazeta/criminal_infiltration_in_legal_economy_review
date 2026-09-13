import csv
import json
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_SOURCES = {
    "CAND-ACADEMIC-2026-09-10-EXTRA-65282d1dbeff-003":
        "https://www.anticorruzione.it/documents/91439/126610/LA+PREVENZIONE+COLLABORATIVA_art_+94bis+Codice+Antimafia.pdf/464cb231-9c8f-8600-7f5c-1b8f7178a2f9?t=1694780817920",
    "CAND-ACADEMIC-2026-09-10-EXTRA-65282d1dbeff-004":
        "https://mpra.ub.uni-muenchen.de/9138/1/MPRA_paper_9138.pdf",
    "CAND-ACADEMIC-2026-09-10-EXTRA-8af43493861b-002":
        "https://chicagounbound.uchicago.edu/cgi/viewcontent.cgi?article=5018&context=uclrev",
}


class ParallelSearchSelectedPaperLaneBatch13Tests(unittest.TestCase):
    def test_batch13_adds_three_existing_full_text_candidates_without_scientific_decisions(self) -> None:
        payload = json.loads(
            (ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8")
        )
        records = {row["candidateId"]: row for row in payload["records"]}
        with (ROOT / "data/curation/review_queue.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            queue_ids = [row["candidate_id"] for row in csv.DictReader(handle)]

        for candidate, source in EXPECTED_SOURCES.items():
            with self.subTest(candidate=candidate):
                # A dict alone would silently hide duplicate overrides or queue rows.
                self.assertEqual(queue_ids.count(candidate), 1)
                self.assertEqual(
                    sum(row["candidateId"] == candidate for row in payload["records"]), 1
                )
                row = records[candidate]
                self.assertEqual(row["kind"], "full_text_intro")
                # Substring checks would also accept an unrelated host or manifestation.
                self.assertEqual(row["sourceUrl"], source)
                parsed = urlsplit(row["sourceUrl"])
                self.assertEqual(parsed.scheme, "https")
                self.assertIsNone(parsed.username)
                self.assertIsNone(parsed.password)
                self.assertLess(len(row["synopsis"]), 900)
                self.assertIn("Parallel Search", row["note"])
                self.assertIn("Evidence basis: full_text", row["note"])
                self.assertNotIn("eligible_", row["note"])

        private_ordering = "CAND-ACADEMIC-2026-09-10-EXTRA-8af43493861b-002"
        self.assertIn("metadata reconciliation", records[private_ordering]["note"])


if __name__ == "__main__":
    unittest.main()
