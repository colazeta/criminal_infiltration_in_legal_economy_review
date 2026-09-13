from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OVERRIDES = ROOT / "data" / "curation" / "reading_aid_overrides.json"
RETRIEVAL = ROOT / "data" / "curation" / "retrieval_coverage.csv"
QUEUE = ROOT / "data" / "curation" / "review_queue.csv"

LEGALITY_EFFICIENCY = "CAND-ACADEMIC-2026-09-13-EXTRA-0da19cdc8206-001"
PIZZO_CERTIFICATION = "CAND-ACADEMIC-2026-09-13-EXTRA-0da19cdc8206-002"
LOAN_CANT_REFUSE = "CAND-ACADEMIC-2026-09-13-EXTRA-0da19cdc8206-003"

LEGALITY_EFFICIENCY_PDF = "https://link.springer.com/content/pdf/10.1007/s10657-025-09848-w.pdf"
PIZZO_SSRN = "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4961758"
RFB_PDF = "https://www.rfberlin.com/wp-content/uploads/2025/10/25101.pdf"


class ParallelSearchBatch18Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        cls.overrides = {row["candidateId"]: row for row in payload["records"]}
        with RETRIEVAL.open(newline="", encoding="utf-8-sig") as handle:
            cls.retrieval = {row["candidate_id"]: row for row in csv.DictReader(handle)}
        with QUEUE.open(newline="", encoding="utf-8-sig") as handle:
            cls.queue = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    def test_batch_is_candidate_bound_and_preserves_registered_identity(self) -> None:
        self.assertEqual(self.queue[LEGALITY_EFFICIENCY]["doi"], "10.1007/s10657-025-09848-w")
        self.assertEqual(self.queue[PIZZO_CERTIFICATION]["doi"], "")
        self.assertEqual(self.queue[LOAN_CANT_REFUSE]["doi"], "")
        self.assertEqual(self.queue[PIZZO_CERTIFICATION]["authors"], "Carmine Pizzo")
        self.assertIn("Paolo Pinotti", self.queue[LOAN_CANT_REFUSE]["authors"])

    def test_verified_sources_and_evidence_boundaries_are_recorded(self) -> None:
        expected = {
            LEGALITY_EFFICIENCY: ("full_text_intro", LEGALITY_EFFICIENCY_PDF, "Evidence basis: full_text"),
            PIZZO_CERTIFICATION: ("verified_abstract_source", PIZZO_SSRN, "Evidence basis: abstract_only"),
            LOAN_CANT_REFUSE: ("full_text_intro", RFB_PDF, "Evidence basis: full_text"),
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
            (LEGALITY_EFFICIENCY, LEGALITY_EFFICIENCY_PDF),
            (LOAN_CANT_REFUSE, RFB_PDF),
        ):
            row = self.retrieval[candidate_id]
            self.assertIn(row["resolution_status"], {"unresolved", "source_link_only", "open_access_landing", "full_text"})
            if row["resolution_status"] == "full_text":
                self.assertEqual(row["full_text_url"], url)
                self.assertIn(url, row["source_urls"])
                self.assertEqual(row["match_confidence"], "high")

    def test_current_pizzo_revision_is_not_promoted_from_earlier_full_text(self) -> None:
        record = self.overrides[PIZZO_CERTIFICATION]
        self.assertEqual(record["kind"], "verified_abstract_source")
        self.assertIn("last revised 20 May 2026", record["note"])
        self.assertIn("earlier version", record["note"])
        self.assertIn("not silently substituted", record["note"])
        self.assertNotEqual(self.retrieval[PIZZO_CERTIFICATION]["full_text_url"].strip(), PIZZO_SSRN)

    def test_related_working_paper_manifestations_remain_explicit(self) -> None:
        self.assertIn("CEIS Research Paper 592", self.overrides[LEGALITY_EFFICIENCY]["note"])
        self.assertIn("UIF Quaderno 32", self.overrides[LOAN_CANT_REFUSE]["note"])
        self.assertIn("not silently", self.overrides[LEGALITY_EFFICIENCY]["note"])
        self.assertIn("not silently", self.overrides[LOAN_CANT_REFUSE]["note"])


if __name__ == "__main__":
    unittest.main()
