import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/retrieval/resolve_queue.py"
SPEC = importlib.util.spec_from_file_location("retrieval_resolver", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class RetrievalEnrichmentPreservationTests(unittest.TestCase):
    def queue_row(self):
        return {
            "candidate_id": "CAND-TEST-1",
            "title": "Exact Work",
            "doi": "",
            "source_links": "https://discovery.example/record",
        }

    def selected_previous(self):
        return {
            "candidate_id": "CAND-TEST-1",
            "title": "Exact Work",
            "doi": "",
            "resolution_status": "full_text",
            "best_url": "https://repository.example/paper.pdf",
            "best_url_kind": "full_text",
            "full_text_url": "https://repository.example/paper.pdf",
            "open_access_url": "https://repository.example/record",
            "landing_url": "https://publisher.example/article",
            "doi_url": "",
            "source_urls": "https://discovery.example/record; https://repository.example/paper.pdf",
            "resolved_doi": "",
            "resolution_sources": "OpenAlex; Repository via Parallel Search",
            "match_method": "OpenAlex:title_year; Parallel Search:exact_title_authors_year; Repository:full_text",
            "match_confidence": "high",
            "checked_at": "2026-09-12",
            "notes": "Parallel Search selected-paper OA lane: exact title/authors matched; no canonical merge.",
        }

    def test_enrichment_extra_url_does_not_force_immediate_refresh(self):
        self.assertFalse(
            MODULE.should_refresh(
                self.queue_row(),
                self.selected_previous(),
                "2026-09-13",
                30,
            )
        )

    def test_new_queue_source_still_forces_refresh(self):
        row = self.queue_row()
        row["source_links"] = "https://discovery.example/record; https://new.example/record"
        self.assertTrue(
            MODULE.should_refresh(
                row,
                self.selected_previous(),
                "2026-09-13",
                30,
            )
        )

    def test_metadata_refresh_cannot_downgrade_verified_selected_full_text(self):
        refreshed = {
            "candidate_id": "CAND-TEST-1",
            "title": "Exact Work",
            "doi": "",
            "resolution_status": "open_access_landing",
            "best_url": "https://new.example/oa",
            "best_url_kind": "open_access",
            "full_text_url": "",
            "open_access_url": "https://new.example/oa",
            "landing_url": "",
            "doi_url": "",
            "source_urls": "https://discovery.example/record",
            "resolved_doi": "",
            "resolution_sources": "OpenAlex",
            "match_method": "OpenAlex:title_year",
            "match_confidence": "medium",
            "checked_at": "2026-10-12",
            "notes": "Unpaywall:not_configured",
        }
        result = MODULE.preserve_selected_paper_resolution(
            self.queue_row(), self.selected_previous(), refreshed
        )
        self.assertEqual(result["resolution_status"], "full_text")
        self.assertEqual(result["best_url_kind"], "full_text")
        self.assertEqual(result["full_text_url"], "https://repository.example/paper.pdf")
        self.assertIn("https://repository.example/paper.pdf", result["source_urls"])
        self.assertIn("Repository via Parallel Search", result["resolution_sources"])
        self.assertIn("Parallel Search:exact_title_authors_year", result["match_method"])
        self.assertIn(MODULE.SELECTED_PAPER_NOTE, result["notes"])
        self.assertEqual(result["match_confidence"], "high")

    def test_fresh_full_text_may_become_primary_but_verified_evidence_is_retained(self):
        refreshed = {
            "candidate_id": "CAND-TEST-1",
            "title": "Exact Work",
            "doi": "",
            "resolution_status": "full_text",
            "best_url": "https://new.example/paper.pdf",
            "best_url_kind": "full_text",
            "full_text_url": "https://new.example/paper.pdf",
            "open_access_url": "",
            "landing_url": "",
            "doi_url": "",
            "source_urls": "https://discovery.example/record",
            "resolved_doi": "",
            "resolution_sources": "OpenAlex",
            "match_method": "OpenAlex:title_year",
            "match_confidence": "medium",
            "checked_at": "2026-10-12",
            "notes": "",
        }
        result = MODULE.preserve_selected_paper_resolution(
            self.queue_row(), self.selected_previous(), refreshed
        )
        self.assertEqual(result["full_text_url"], "https://new.example/paper.pdf")
        self.assertIn("https://repository.example/paper.pdf", result["source_urls"])
        self.assertIn("Repository via Parallel Search", result["resolution_sources"])

    def test_identity_change_disables_preservation(self):
        row = self.queue_row()
        row["title"] = "Different Work"
        refreshed = dict(self.selected_previous())
        refreshed.update(
            {
                "title": "Different Work",
                "resolution_status": "landing_page",
                "best_url": "https://new.example/record",
                "best_url_kind": "landing",
                "full_text_url": "",
                "landing_url": "https://new.example/record",
                "notes": "",
            }
        )
        result = MODULE.preserve_selected_paper_resolution(
            row, self.selected_previous(), refreshed
        )
        self.assertEqual(result["resolution_status"], "landing_page")
        self.assertEqual(result["full_text_url"], "")


if __name__ == "__main__":
    unittest.main()
