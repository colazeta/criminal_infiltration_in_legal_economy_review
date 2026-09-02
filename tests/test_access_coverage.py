from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "access" / "classify_access.py"
SPEC = importlib.util.spec_from_file_location("classify_access", MODULE_PATH)
assert SPEC and SPEC.loader
classifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(classifier)


class AccessCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.row = {
            "candidate_id": "CAND-TEST-001",
            "title": "Organised crime and firms",
            "doi": "10.1000/example",
            "year": "2025",
        }
        self.original_openalex = classifier.openalex_match
        self.original_unpaywall = classifier.unpaywall_match
        self.original_probe = classifier.probe_public_full_text

    def tearDown(self) -> None:
        classifier.openalex_match = self.original_openalex
        classifier.unpaywall_match = self.original_unpaywall
        classifier.probe_public_full_text = self.original_probe

    def test_verified_governed_pdf_is_open(self) -> None:
        result = classifier.classify_row(
            self.row,
            {"full_text_url": "https://example.org/paper.pdf"},
            {
                "coverage_status": "available",
                "match_type": "resolved_pdf",
                "article_url": "https://example.org/paper.pdf",
            },
            "2026-09-02",
        )
        self.assertEqual(result["access_status"], "open")
        self.assertEqual(result["access_kind"], "public_full_text")
        self.assertEqual(result["evidence_source"], "Governed PDF fetch")

    def test_explicit_oa_location_is_open_without_provider_calls(self) -> None:
        classifier.openalex_match = lambda row: (_ for _ in ()).throw(AssertionError("OpenAlex should not be called"))
        classifier.unpaywall_match = lambda row, email: (_ for _ in ()).throw(AssertionError("Unpaywall should not be called"))
        classifier.probe_public_full_text = lambda url, title: (_ for _ in ()).throw(AssertionError("probe should not be called"))
        result = classifier.classify_row(
            self.row,
            {"open_access_url": "https://repository.example/paper"},
            {},
            "2026-09-02",
        )
        self.assertEqual(result["access_status"], "open")
        self.assertEqual(result["access_kind"], "open_access_location")

    def test_observed_public_full_text_overrides_openalex_closed(self) -> None:
        classifier.probe_public_full_text = lambda url, title: (
            True,
            "Anonymous full-text probe returned application/xml and matched the candidate title.",
        )
        classifier.openalex_match = lambda row: (
            {"open_access": {"is_oa": False, "oa_status": "closed"}},
            "",
        )
        classifier.unpaywall_match = lambda row, email: (None, "")
        result = classifier.classify_row(
            self.row,
            {"full_text_url": "https://publisher.example/doi/full-xml/10.1000/example"},
            {},
            "2026-09-02",
        )
        self.assertEqual(result["access_status"], "open")
        self.assertEqual(result["access_kind"], "public_full_text")
        self.assertEqual(result["evidence_source"], "Full-text probe")

    def test_openalex_closed_is_restricted_not_merely_not_found(self) -> None:
        classifier.openalex_match = lambda row: (
            {"open_access": {"is_oa": False, "oa_status": "closed"}},
            "",
        )
        classifier.unpaywall_match = lambda row, email: (None, "")
        result = classifier.classify_row(
            self.row,
            {"doi_url": "https://doi.org/10.1000/example"},
            {},
            "2026-09-02",
        )
        self.assertEqual(result["access_status"], "restricted")
        self.assertIn("closed", result["evidence_detail"].lower())

    def test_failed_full_text_probe_does_not_itself_imply_restricted(self) -> None:
        classifier.probe_public_full_text = lambda url, title: (False, "HTTP 403")
        classifier.openalex_match = lambda row: (None, "")
        classifier.unpaywall_match = lambda row, email: (None, "")
        result = classifier.classify_row(
            self.row,
            {"full_text_url": "https://publisher.example/full-text"},
            {},
            "2026-09-02",
        )
        self.assertEqual(result["access_status"], "unknown")
        self.assertIn("Full-text probe:HTTP 403", result["notes"])

    def test_no_positive_access_evidence_stays_unknown(self) -> None:
        classifier.openalex_match = lambda row: (None, "HTTP 429")
        classifier.unpaywall_match = lambda row, email: (None, "")
        result = classifier.classify_row(
            self.row,
            {"doi_url": "https://doi.org/10.1000/example"},
            {},
            "2026-09-02",
        )
        self.assertEqual(result["access_status"], "unknown")
        self.assertIn("OpenAlex:HTTP 429", result["notes"])

    def test_probe_rejects_non_public_targets(self) -> None:
        self.assertEqual(classifier.safe_probe_url("https://localhost/paper"), "")
        self.assertEqual(classifier.safe_probe_url("https://192.168.1.2/paper"), "")
        self.assertEqual(classifier.safe_probe_url("https://doi.org/10.1000/example"), "")
        self.assertEqual(classifier.safe_probe_url("http://example.org/paper"), "")

    def test_contract_is_one_row_per_queue_candidate(self) -> None:
        queue = [
            {"candidate_id": "A", "title": "A"},
            {"candidate_id": "B", "title": "B"},
        ]
        coverage = [classifier.access_row(queue[0], "unknown", "insufficient_evidence", "", "test", "none", "2026-09-02", "")]
        with self.assertRaises(classifier.AccessCoverageError):
            classifier.validate_coverage(queue, coverage, classifier.FIELDS)

    def test_access_workflow_has_no_paid_or_web_search_provider(self) -> None:
        workflow = (ROOT / ".github/workflows/access-coverage.yml").read_text(encoding="utf-8")
        script = MODULE_PATH.read_text(encoding="utf-8")
        for forbidden in ("TAVILY_API_KEY", "EXA_API_KEY", "api.tavily", "api.exa"):
            self.assertNotIn(forbidden, workflow)
            self.assertNotIn(forbidden, script)
        self.assertIn("UNPAYWALL_EMAIL", workflow)
        self.assertIn("access_coverage.csv", workflow)
        self.assertIn("sync_issue_access.py", workflow)
        self.assertIn("PROBE_BYTES = 500_000", script)
        self.assertIn('"Range": f"bytes=0-{PROBE_BYTES - 1}"', script)

    def test_issue_sync_explains_conservative_semantics(self) -> None:
        sync = (ROOT / "scripts/access/sync_issue_access.py").read_text(encoding="utf-8")
        self.assertIn("## Access status — mechanical", sync)
        self.assertIn("failure to find an OA copy alone is not", sync)
        self.assertIn("Access status", sync)


if __name__ == "__main__":
    unittest.main()
