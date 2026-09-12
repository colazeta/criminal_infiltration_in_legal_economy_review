import csv
import json
import unittest
from pathlib import Path
from urllib.parse import urlsplit

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

    def test_initial_parallel_search_upgrades_remain_retrievable_after_resolver_refresh(self):
        with (ROOT / "data/curation/retrieval_coverage.csv").open(encoding="utf-8", newline="") as handle:
            rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}
        # The selected-paper pass established full-text access for both works. A
        # later mechanical resolver refresh is allowed to prefer another exact
        # manifestation of the same work (for example an OpenAlex OSF copy), so
        # this regression test must enforce the access contract rather than pin
        # one provider URL forever. Provider-specific evidence remains in the
        # reading-aid provenance tests below.
        for candidate in (
            "CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-003",
            "CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-005",
        ):
            row = rows[candidate]
            self.assertEqual(row["resolution_status"], "full_text")
            full_text_url = row["full_text_url"]
            parsed = urlsplit(full_text_url)
            self.assertEqual(parsed.scheme, "https")
            self.assertTrue(parsed.netloc)
            self.assertEqual(row["best_url_kind"], "full_text")

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
        # The reading aid is grounded in the RePEc abstract record; retrieval may
        # independently prefer any exact verified full-text manifestation.
        self.assertIn("ideas.repec.org", records["CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-003"]["sourceUrl"])
        self.assertIn("ssrn.com", records["CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-005"]["sourceUrl"])

    def test_parallel_search_followup_batch_preserves_evidence_boundaries(self):
        payload = json.loads((ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8"))
        records = {row["candidateId"]: row for row in payload["records"]}
        with (ROOT / "data/curation/review_queue.csv").open(encoding="utf-8", newline="") as handle:
            queue_ids = {row["candidate_id"] for row in csv.DictReader(handle)}

        expected = {
            "CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-014": ("core.ac.uk", "full_text_intro", "full_text"),
            "CAND-ACADEMIC-2026-09-09-013": ("iris.unipa.it", "verified_abstract_source", "abstract_only"),
            "CAND-ACADEMIC-2026-09-09-012": ("riviste.unimi.it", "verified_abstract_source", "full_text"),
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

        self.assertIn("not_verifiable", records["CAND-ACADEMIC-2026-09-09-013"]["note"])

    def test_third_parallel_search_batch_is_version_aware_and_bounded(self):
        payload = json.loads((ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8"))
        records = {row["candidateId"]: row for row in payload["records"]}
        with (ROOT / "data/curation/review_queue.csv").open(encoding="utf-8", newline="") as handle:
            queue_ids = {row["candidate_id"] for row in csv.DictReader(handle)}

        expected = {
            "CAND-ACADEMIC-2026-09-09-001": ("ifs.org.uk", "full_text_intro", "full_text"),
            "CAND-ACADEMIC-2026-09-09-EXTRA-5e31cc756b0e-010": ("op.europa.eu", "full_text_intro", "full_text"),
            "CAND-ACADEMIC-2026-09-09-EXTRA-6b5b5e038ac4-002": ("op.europa.eu", "full_text_intro", "full_text"),
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

        covid = records["CAND-ACADEMIC-2026-09-09-001"]
        self.assertIn("2023", covid["sourceLabel"])
        self.assertIn("2025", covid["note"])
        self.assertIn("not silently substituted", covid["note"])
        final_report = records["CAND-ACADEMIC-2026-09-09-EXTRA-5e31cc756b0e-010"]
        annexes = records["CAND-ACADEMIC-2026-09-09-EXTRA-6b5b5e038ac4-002"]
        self.assertIn("10.2837/64101", final_report["note"])
        self.assertIn("10.2837/442937", annexes["note"])
        self.assertNotEqual(final_report["sourceUrl"], annexes["sourceUrl"])
        self.assertIn("distinct", final_report["note"])
        self.assertIn("distinct", annexes["note"])

    def test_fourth_parallel_search_batch_promotes_only_verified_full_text(self):
        payload = json.loads((ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8"))
        records = {row["candidateId"]: row for row in payload["records"]}
        with (ROOT / "data/curation/review_queue.csv").open(encoding="utf-8", newline="") as handle:
            queue_ids = {row["candidate_id"] for row in csv.DictReader(handle)}

        candidate = "CAND-ACADEMIC-2026-09-09-EXTRA-6b5b5e038ac4-003"
        self.assertIn(candidate, queue_ids)
        row = records[candidate]
        self.assertEqual(row["kind"], "full_text_intro")
        self.assertIn("www.ojp.gov/pdffiles1/Digitization/93999NCJRS.pdf", row["sourceUrl"])
        self.assertIn("NCJ 93999", row["note"])
        self.assertIn("Evidence basis: full_text", row["note"])
        self.assertNotIn("parallel-search", row["sourceUrl"].lower())
        self.assertLess(len(row["synopsis"]), 900)


if __name__ == "__main__":
    unittest.main()
