import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/retrieval/apply_verified_reading_locators.py"
SPEC = importlib.util.spec_from_file_location("verified_reading_locator_sync", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class VerifiedReadingLocatorSyncTests(unittest.TestCase):
    def test_full_text_intro_is_promoted_without_scientific_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            coverage = tmp / "retrieval_coverage.csv"
            overrides = tmp / "reading_aid_overrides.json"
            fields = [
                "candidate_id",
                "title",
                "doi",
                "resolution_status",
                "best_url",
                "best_url_kind",
                "full_text_url",
                "open_access_url",
                "landing_url",
                "doi_url",
                "source_urls",
                "resolved_doi",
                "resolution_sources",
                "match_method",
                "match_confidence",
                "checked_at",
                "notes",
            ]
            with coverage.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerow(
                    {
                        "candidate_id": "CAND-TEST-1",
                        "title": "Test work",
                        "resolution_status": "source_link_only",
                        "best_url": "https://example.org/landing",
                        "best_url_kind": "source",
                        "source_urls": "https://example.org/landing",
                        "match_method": "source_only",
                        "match_confidence": "low",
                        "checked_at": "2026-09-01",
                    }
                )
            overrides.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "records": [
                            {
                                "candidateId": "CAND-TEST-1",
                                "kind": "full_text_intro",
                                "sourceUrl": "https://repository.example/paper.pdf",
                                "checkedAt": "2026-09-12",
                                "note": "Evidence basis: full_text. No scientific decision.",
                            },
                            {
                                "candidateId": "CAND-IGNORED",
                                "kind": "publisher_summary",
                                "sourceUrl": "https://publisher.example/summary",
                                "checkedAt": "2026-09-12",
                                "note": "Evidence basis: partial_text.",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = MODULE.apply(coverage, overrides)
            self.assertEqual(result, {"eligible_overrides": 1, "changed": 1})
            with coverage.open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["resolution_status"], "full_text")
            self.assertEqual(row["best_url_kind"], "full_text")
            self.assertEqual(row["full_text_url"], "https://repository.example/paper.pdf")
            self.assertIn("https://repository.example/paper.pdf", row["source_urls"])
            self.assertIn(MODULE.SOURCE_LABEL, row["resolution_sources"])
            self.assertIn(MODULE.MATCH_LABEL, row["match_method"])
            self.assertEqual(row["match_confidence"], "high")
            self.assertEqual(row["checked_at"], "2026-09-12")
            self.assertIn("no eligibility or canonicalisation decision", row["notes"])
            self.assertEqual(MODULE.apply(coverage, overrides, check=True)["eligible_overrides"], 1)

    def test_existing_full_text_is_preserved_and_locator_is_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            coverage = tmp / "retrieval_coverage.csv"
            overrides = tmp / "reading_aid_overrides.json"
            fields = [
                "candidate_id", "title", "doi", "resolution_status", "best_url", "best_url_kind",
                "full_text_url", "open_access_url", "landing_url", "doi_url", "source_urls",
                "resolved_doi", "resolution_sources", "match_method", "match_confidence",
                "checked_at", "notes",
            ]
            existing_pdf = "https://publisher.example/full.pdf"
            with coverage.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerow(
                    {
                        "candidate_id": "CAND-TEST-2",
                        "title": "Test work 2",
                        "resolution_status": "full_text",
                        "best_url": existing_pdf,
                        "best_url_kind": "full_text",
                        "full_text_url": existing_pdf,
                        "source_urls": existing_pdf,
                        "resolution_sources": "Publisher",
                        "match_method": "publisher:doi",
                        "match_confidence": "high",
                        "checked_at": "2026-09-10",
                    }
                )
            overrides.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "records": [
                            {
                                "candidateId": "CAND-TEST-2",
                                "kind": "full_text_intro",
                                "sourceUrl": "https://repository.example/author-copy.pdf",
                                "checkedAt": "2026-09-12",
                                "note": "Evidence basis: full_text.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            MODULE.apply(coverage, overrides)
            with coverage.open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["full_text_url"], existing_pdf)
            self.assertEqual(row["best_url"], existing_pdf)
            self.assertIn("https://repository.example/author-copy.pdf", row["source_urls"])
            MODULE.apply(coverage, overrides, check=True)

    def test_repository_overrides_expose_only_explicit_full_text_intro_records(self):
        eligible = {row["candidate_id"] for row in MODULE.eligible_overrides(MODULE.OVERRIDES_PATH)}
        self.assertIn("CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-014", eligible)
        self.assertIn("CAND-ACADEMIC-2026-09-09-001", eligible)
        self.assertNotIn("CAND-ACADEMIC-2026-09-09-EXTRA-5e31cc756b0e-010", eligible)
        self.assertNotIn("CAND-ACADEMIC-2026-09-09-EXTRA-6b5b5e038ac4-002", eligible)

    def test_workflow_runs_bridge_before_coverage_check(self):
        workflow = (ROOT / ".github/workflows/retrieval-resolution.yml").read_text(encoding="utf-8")
        self.assertIn("data/curation/reading_aid_overrides.json", workflow)
        self.assertIn("scripts/retrieval/apply_verified_reading_locators.py", workflow)
        apply_at = workflow.index("python scripts/retrieval/apply_verified_reading_locators.py\n")
        check_at = workflow.index("python scripts/retrieval/resolve_queue.py --check")
        self.assertLess(apply_at, check_at)
        self.assertIn("python scripts/retrieval/apply_verified_reading_locators.py --check", workflow)
        self.assertIn("cancel-in-progress: false", workflow)


if __name__ == "__main__":
    unittest.main()
