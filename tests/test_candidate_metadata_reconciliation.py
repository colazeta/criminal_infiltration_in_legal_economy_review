from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.curation.reconcile_candidate_metadata import (
    MetadataReconciliationError,
    find_safe_repairs,
    reconcile,
)


QUEUE_FIELDS = [
    "candidate_id",
    "title",
    "doi",
    "source_links",
    "verification_status",
    "metadata_confidence",
    "intake_assessment",
    "possible_duplicate",
    "metadata_conflict",
    "origin",
    "review_stage",
    "current_status",
    "current_decision",
    "updated_at",
]
RETRIEVAL_FIELDS = [
    "candidate_id",
    "title",
    "resolved_doi",
    "doi_url",
    "resolution_sources",
    "match_method",
    "match_confidence",
    "checked_at",
]


def queue_row(**overrides: str) -> dict[str, str]:
    row = {
        "candidate_id": "CAND-ACADEMIC-2026-09-01-002",
        "title": "Testing the reliability of OSINT network data",
        "doi": "",
        "source_links": "https://example.test/intake",
        "verification_status": "metadata_partial",
        "metadata_confidence": "",
        "intake_assessment": "plausible_core",
        "possible_duplicate": "",
        "metadata_conflict": "",
        "origin": "daily_surveillance",
        "review_stage": "metadata_fix",
        "current_status": "pending",
        "current_decision": "",
        "updated_at": "2026-09-01",
    }
    row.update(overrides)
    return row


def retrieval_row(**overrides: str) -> dict[str, str]:
    row = {
        "candidate_id": "CAND-ACADEMIC-2026-09-01-002",
        "title": "Testing the reliability of OSINT network data",
        "resolved_doi": "10.1080/17440572.2025.2567277",
        "doi_url": "https://doi.org/10.1080/17440572.2025.2567277",
        "resolution_sources": "OpenAlex; Crossref",
        "match_method": "OpenAlex:title_year; Crossref:title_year",
        "match_confidence": "medium",
        "checked_at": "2026-09-02",
    }
    row.update(overrides)
    return row


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class CandidateMetadataReconciliationTests(unittest.TestCase):
    def test_dual_source_title_year_match_is_safe_repair(self) -> None:
        repairs = find_safe_repairs([queue_row()], [retrieval_row()])
        self.assertEqual(len(repairs), 1)
        self.assertEqual(repairs[0]["doi"], "10.1080/17440572.2025.2567277")

    def test_single_source_never_repairs(self) -> None:
        repairs = find_safe_repairs(
            [queue_row()],
            [retrieval_row(resolution_sources="Crossref", match_method="Crossref:title_year")],
        )
        self.assertEqual(repairs, [])

    def test_conflict_or_duplicate_never_repairs(self) -> None:
        self.assertEqual(find_safe_repairs([queue_row(metadata_conflict="Year conflict")], [retrieval_row()]), [])
        self.assertEqual(find_safe_repairs([queue_row(possible_duplicate="Possible duplicate")], [retrieval_row()]), [])

    def test_existing_decision_never_repairs(self) -> None:
        repairs = find_safe_repairs(
            [queue_row(current_decision="not_eligible", current_status="reviewed")],
            [retrieval_row()],
        )
        self.assertEqual(repairs, [])

    def test_reconcile_changes_only_mechanical_metadata_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = queue_row(intake_assessment="plausible_core")
            write_csv(root / "data/curation/review_queue.csv", QUEUE_FIELDS, [original])
            write_csv(root / "data/curation/retrieval_coverage.csv", RETRIEVAL_FIELDS, [retrieval_row()])
            summary = reconcile(root, "2026-09-05")
            self.assertEqual(summary["safe_repairs"], 1)
            with (root / "data/curation/review_queue.csv").open(newline="", encoding="utf-8") as handle:
                repaired = next(csv.DictReader(handle))
            self.assertEqual(repaired["doi"], "10.1080/17440572.2025.2567277")
            self.assertEqual(repaired["verification_status"], "metadata_verified")
            self.assertEqual(repaired["metadata_confidence"], "high")
            self.assertEqual(repaired["review_stage"], "abstract_full_text_review")
            self.assertEqual(repaired["intake_assessment"], "plausible_core")
            self.assertEqual(repaired["current_decision"], "")
            self.assertIn("https://doi.org/10.1080/17440572.2025.2567277", repaired["source_links"])
            self.assertEqual(repaired["updated_at"], "2026-09-05")
            with self.assertRaises(MetadataReconciliationError):
                # Check passes only after re-reading the now repaired queue; a stale in-memory
                # repair cannot be silently ignored.
                find_safe_repairs([queue_row(metadata_conflict="x")], [retrieval_row(), retrieval_row()])

    def test_check_fails_when_safe_repair_remains(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_csv(root / "data/curation/review_queue.csv", QUEUE_FIELDS, [queue_row()])
            write_csv(root / "data/curation/retrieval_coverage.csv", RETRIEVAL_FIELDS, [retrieval_row()])
            with self.assertRaises(MetadataReconciliationError):
                reconcile(root, "2026-09-05", check=True)


if __name__ == "__main__":
    unittest.main()
