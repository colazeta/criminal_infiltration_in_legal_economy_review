from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "retrieval" / "resolve_queue.py"
SPEC = importlib.util.spec_from_file_location("resolve_queue", MODULE_PATH)
assert SPEC and SPEC.loader
resolver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resolver)


class RetrievalResolutionTests(unittest.TestCase):
    def test_title_similarity_accepts_same_work_and_rejects_unrelated_title(self) -> None:
        self.assertGreater(
            resolver.title_similarity(
                "Mafia Infiltration and Ownership Dynamics in Italian Companies during Covid-19",
                "Mafia infiltration & ownership dynamics in Italian companies during COVID 19",
            ),
            0.9,
        )
        self.assertLess(
            resolver.title_similarity(
                "Mafia Infiltration and Ownership Dynamics in Italian Companies during Covid-19",
                "Climate adaptation and coastal fisheries",
            ),
            0.2,
        )

    def test_direct_discovery_pdf_is_preserved_as_full_text(self) -> None:
        original_openalex = resolver.openalex_match
        original_crossref = resolver.crossref_match
        original_unpaywall = resolver.unpaywall_match
        try:
            resolver.openalex_match = lambda row, key: (None, "title_year", "")
            resolver.crossref_match = lambda row: (None, "title_year", "")
            resolver.unpaywall_match = lambda row, email: (None, "not_configured", "")
            row = {
                "candidate_id": "CAND-TEST-001",
                "title": "A test paper",
                "doi": "",
                "year": "2025",
                "source_links": "https://example.org/paper.pdf; https://example.org/landing",
            }
            result = resolver.resolve_row(row, "2026-09-02")
        finally:
            resolver.openalex_match = original_openalex
            resolver.crossref_match = original_crossref
            resolver.unpaywall_match = original_unpaywall

        self.assertEqual(result["resolution_status"], "full_text")
        self.assertEqual(result["best_url"], "https://example.org/paper.pdf")
        self.assertEqual(result["best_url_kind"], "full_text")
        self.assertEqual(result["full_text_url"], "https://example.org/paper.pdf")

    def test_coverage_contract_requires_exactly_one_row_per_queue_candidate(self) -> None:
        queue = [
            {"candidate_id": "A", "title": "A"},
            {"candidate_id": "B", "title": "B"},
        ]
        base = {
            "title": "A",
            "doi": "",
            "resolution_status": "unresolved",
            "best_url": "",
            "best_url_kind": "none",
            "full_text_url": "",
            "open_access_url": "",
            "landing_url": "",
            "doi_url": "",
            "source_urls": "",
            "resolved_doi": "",
            "resolution_sources": "",
            "match_method": "source_only",
            "match_confidence": "low",
            "checked_at": "2026-09-02",
            "notes": "",
        }
        coverage = [dict(base, candidate_id="A")]
        with self.assertRaises(resolver.ResolutionError):
            resolver.validate_coverage(queue, coverage, resolver.FIELDS)

    def test_workflows_make_resolution_persistent_and_self_applying(self) -> None:
        workflow = (ROOT / ".github/workflows/retrieval-resolution.yml").read_text(encoding="utf-8")
        intake = (ROOT / ".github/workflows/intake-to-curation.yml").read_text(encoding="utf-8")
        materialize = (ROOT / ".github/workflows/materialize-curation.yml").read_text(encoding="utf-8")
        self.assertIn("data/curation/review_queue.csv", workflow)
        self.assertIn("schedule:", workflow)
        self.assertIn("python scripts/retrieval/resolve_queue.py", workflow)
        self.assertIn("gh pr merge", workflow)
        self.assertIn("resolve_queue.py", intake)
        self.assertIn("retrieval_coverage.csv", materialize)
        self.assertIn("sync_issue_retrieval.py", materialize)

    def test_retrieval_ledger_is_metadata_only(self) -> None:
        script = MODULE_PATH.read_text(encoding="utf-8")
        fields = resolver.FIELDS
        self.assertNotIn("abstract", fields)
        self.assertNotIn("full_text", fields)
        self.assertIn("full_text_url", fields)
        self.assertNotIn("urlretrieve", script)
        self.assertNotIn("requests.get", script)


if __name__ == "__main__":
    unittest.main()
