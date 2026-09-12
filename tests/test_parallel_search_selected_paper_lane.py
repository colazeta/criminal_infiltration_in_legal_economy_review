import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ParallelSearchSelectedPaperLaneTests(unittest.TestCase):
    def test_governance_distinguishes_daily_fallback_from_selected_paper_lane(self):
        sources = (ROOT / "docs/governance/sources.md").read_text(encoding="utf-8")
        web = (ROOT / "docs/governance/web-capabilities.md").read_text(encoding="utf-8")
        targeted = (ROOT / "docs/operations/targeted-reading-retrieval.md").read_text(encoding="utf-8")
        self.assertIn("Parallel Search selected-paper OA lane", sources)
        self.assertIn("does not change the Exa-primary W1–W7 rule", sources)
        self.assertIn("final publisher/repository/document URL", sources)
        self.assertIn("Connector-side Parallel Search lane", web)
        self.assertIn("not a Cloudflare Worker runtime provider", web)
        self.assertIn("abstract_only", targeted)
        self.assertIn("full_text", targeted)
        self.assertIn("not_verifiable", targeted)

    def test_initial_parallel_search_upgrades_are_existing_candidates_only(self):
        with (ROOT / "data/curation/retrieval_coverage.csv").open(encoding="utf-8", newline="") as handle:
            rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}
        mafias = rows["CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-003"]
        accounting = rows["CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-005"]
        self.assertEqual(mafias["resolution_status"], "full_text")
        self.assertEqual(mafias["full_text_url"], "https://www.econstor.eu/bitstream/10419/295916/1/dp16893.pdf")
        self.assertIn("EconStor", mafias["resolution_sources"])
        self.assertEqual(accounting["resolution_status"], "full_text")
        self.assertTrue(accounting["full_text_url"].startswith("https://papers.ssrn.com/sol3/Delivery.cfm/4912709.pdf"))
        self.assertIn("SSRN", accounting["resolution_sources"])

    def test_reading_aids_use_final_sources_and_do_not_store_verbatim_abstracts(self):
        payload = json.loads((ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8"))
        records = {row["candidateId"]: row for row in payload["records"]}
        for candidate in [
            "CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-001",
            "CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-003",
            "CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-005",
        ]:
            row = records[candidate]
            self.assertTrue(row["sourceUrl"].startswith("https://"))
            self.assertNotIn("parallel-search", row["sourceUrl"].lower())
            self.assertIn(row["kind"], {"verified_abstract_source", "full_text_intro", "publisher_summary"})
            self.assertLess(len(row["synopsis"]), 900)
            self.assertIn("Parallel Search", row["note"])
        self.assertIn("aeaweb.org", records["CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-001"]["sourceUrl"])
        self.assertIn("econstor.eu", records["CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-003"]["sourceUrl"])
        self.assertIn("ssrn.com", records["CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-005"]["sourceUrl"])


if __name__ == "__main__":
    unittest.main()
