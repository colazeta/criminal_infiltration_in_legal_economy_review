from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OVERRIDES = ROOT / "data" / "curation" / "reading_aid_overrides.json"
RETRIEVAL = ROOT / "data" / "curation" / "retrieval_coverage.csv"
QUEUE = ROOT / "data" / "curation" / "review_queue.csv"

CHAMPEYRACHE = "CAND-ACADEMIC-2026-09-13-EXTRA-60872f2c2bf0-001"
OJP_INDICATORS = "CAND-ACADEMIC-2026-09-13-EXTRA-7450b0e2f8a2-001"

CHAMPEYRACHE_URL = "https://www.persee.fr/doc/ecoap_0013-0494_2012_num_65_3_3609"
OJP_INDICATORS_URL = "https://nij.ojp.gov/library/publications/indicators-impacts-organized-crime"


class ParallelSearchBatch20Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        cls.overrides = {row["candidateId"]: row for row in payload["records"]}
        with RETRIEVAL.open(newline="", encoding="utf-8-sig") as handle:
            cls.retrieval = {row["candidate_id"]: row for row in csv.DictReader(handle)}
        with QUEUE.open(newline="", encoding="utf-8-sig") as handle:
            cls.queue = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    def test_batch_is_candidate_bound_and_does_not_invent_dois(self) -> None:
        self.assertIn(CHAMPEYRACHE, self.queue)
        self.assertIn(OJP_INDICATORS, self.queue)
        self.assertEqual(self.queue[CHAMPEYRACHE]["doi"], "")
        self.assertEqual(self.queue[OJP_INDICATORS]["doi"], "")
        self.assertEqual(
            self.queue[CHAMPEYRACHE]["title"],
            "Mafia et économie légale : typologie des marchés infiltrés",
        )
        self.assertEqual(
            self.queue[OJP_INDICATORS]["title"],
            "Indicators of the Impacts of Organized Crime",
        )

    def test_verified_sources_preserve_evidence_boundaries(self) -> None:
        champeyrache = self.overrides[CHAMPEYRACHE]
        self.assertEqual(champeyrache["kind"], "full_text_intro")
        self.assertEqual(champeyrache["sourceUrl"], CHAMPEYRACHE_URL)
        self.assertIn("Evidence basis: full_text", champeyrache["note"])
        self.assertIn("Parallel Search", champeyrache["sourceLabel"] + champeyrache["note"])
        self.assertLess(len(champeyrache["synopsis"].split()), 90)

        indicators = self.overrides[OJP_INDICATORS]
        self.assertEqual(indicators["kind"], "verified_abstract_source")
        self.assertEqual(indicators["sourceUrl"], OJP_INDICATORS_URL)
        self.assertIn("Evidence basis: abstract_only", indicators["note"])
        self.assertIn("Parallel Search", indicators["sourceLabel"] + indicators["note"])
        self.assertLess(len(indicators["synopsis"].split()), 90)

    def test_abstract_only_ojp_source_never_claims_full_text(self) -> None:
        indicators = self.retrieval[OJP_INDICATORS]
        self.assertNotEqual(indicators["full_text_url"].strip(), OJP_INDICATORS_URL)
        self.assertNotEqual(indicators["resolution_status"], "full_text")


if __name__ == "__main__":
    unittest.main()
