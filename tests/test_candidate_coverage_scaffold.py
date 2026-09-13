from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.curation.scaffold_candidate_coverage import (
    ABSTRACT_FIELDS,
    ACCESS_FIELDS,
    RETRIEVAL_FIELDS,
    CoverageScaffoldError,
    scaffold_all,
)


QUEUE_FIELDS = ["candidate_id", "title", "doi", "source_links"]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


class CandidateCoverageScaffoldTests(unittest.TestCase):
    def make_root(self) -> Path:
        root = Path(self.tempdir.name)
        queue = [
            {
                "candidate_id": "CAND-TEST-001",
                "title": "Existing enriched candidate",
                "doi": "10.1000/existing",
                "source_links": "https://example.org/existing",
            },
            {
                "candidate_id": "CAND-TEST-002",
                "title": "Newly preserved candidate",
                "doi": "",
                "source_links": "https://example.org/new",
            },
        ]
        write_csv(root / "data/curation/review_queue.csv", QUEUE_FIELDS, queue)
        return root

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_scaffold_preserves_enriched_rows_and_adds_only_missing_candidates(self) -> None:
        root = self.make_root()
        enriched_retrieval = {field: "" for field in RETRIEVAL_FIELDS}
        enriched_retrieval.update(
            {
                "candidate_id": "CAND-TEST-001",
                "title": "Existing enriched candidate",
                "doi": "10.1000/existing",
                "resolution_status": "full_text",
                "best_url": "https://example.org/existing.pdf",
                "best_url_kind": "full_text",
                "full_text_url": "https://example.org/existing.pdf",
                "checked_at": "2026-09-12",
                "notes": "verified evidence",
            }
        )
        write_csv(
            root / "data/curation/retrieval_coverage.csv",
            RETRIEVAL_FIELDS,
            [enriched_retrieval],
        )

        result = scaffold_all(root, "2026-09-13")
        self.assertEqual(result, {"retrieval": 1, "abstract": 2, "access": 2})

        retrieval = read_csv(root / "data/curation/retrieval_coverage.csv")
        abstract = read_csv(root / "data/curation/abstract_coverage.csv")
        access = read_csv(root / "data/curation/access_coverage.csv")

        self.assertEqual([row["candidate_id"] for row in retrieval], ["CAND-TEST-001", "CAND-TEST-002"])
        self.assertEqual(retrieval[0], enriched_retrieval)
        self.assertEqual(retrieval[1]["resolution_status"], "unresolved")
        self.assertEqual(retrieval[1]["best_url_kind"], "none")
        self.assertIn("enrichment pending", retrieval[1]["notes"])

        self.assertEqual([row["candidate_id"] for row in abstract], ["CAND-TEST-001", "CAND-TEST-002"])
        self.assertTrue(all(row["coverage_status"] == "needs_web_search" for row in abstract))
        self.assertEqual([row["candidate_id"] for row in access], ["CAND-TEST-001", "CAND-TEST-002"])
        self.assertTrue(all(row["access_status"] == "unknown" for row in access))

    def test_second_run_is_idempotent(self) -> None:
        root = self.make_root()
        scaffold_all(root, "2026-09-13")
        paths = [
            root / "data/curation/retrieval_coverage.csv",
            root / "data/curation/abstract_coverage.csv",
            root / "data/curation/access_coverage.csv",
        ]
        before = [path.read_bytes() for path in paths]
        result = scaffold_all(root, "2026-09-14")
        after = [path.read_bytes() for path in paths]
        self.assertEqual(result, {"retrieval": 0, "abstract": 0, "access": 0})
        self.assertEqual(before, after)

    def test_unknown_coverage_identity_fails_closed(self) -> None:
        root = self.make_root()
        rogue = {field: "" for field in ABSTRACT_FIELDS}
        rogue.update(
            {
                "candidate_id": "CAND-ROGUE-999",
                "title": "Rogue",
                "coverage_status": "needs_web_search",
                "checked_at": "2026-09-13",
            }
        )
        write_csv(root / "data/curation/abstract_coverage.csv", ABSTRACT_FIELDS, [rogue])
        with self.assertRaises(CoverageScaffoldError):
            scaffold_all(root, "2026-09-13")

    def test_duplicate_queue_identity_fails_closed(self) -> None:
        root = Path(self.tempdir.name)
        duplicate = {
            "candidate_id": "CAND-TEST-001",
            "title": "Duplicate",
            "doi": "",
            "source_links": "https://example.org/duplicate",
        }
        write_csv(
            root / "data/curation/review_queue.csv",
            QUEUE_FIELDS,
            [duplicate, duplicate],
        )
        with self.assertRaises(CoverageScaffoldError):
            scaffold_all(root, "2026-09-13")

    def test_placeholder_shapes_match_governed_headers(self) -> None:
        root = self.make_root()
        scaffold_all(root, "2026-09-13")
        with (root / "data/curation/retrieval_coverage.csv").open(newline="", encoding="utf-8") as handle:
            self.assertEqual(list(csv.DictReader(handle).fieldnames or []), RETRIEVAL_FIELDS)
        with (root / "data/curation/abstract_coverage.csv").open(newline="", encoding="utf-8") as handle:
            self.assertEqual(list(csv.DictReader(handle).fieldnames or []), ABSTRACT_FIELDS)
        with (root / "data/curation/access_coverage.csv").open(newline="", encoding="utf-8") as handle:
            self.assertEqual(list(csv.DictReader(handle).fieldnames or []), ACCESS_FIELDS)


if __name__ == "__main__":
    unittest.main()
