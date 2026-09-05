from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.curation.reconcile_candidate_metadata import (
    MetadataReconciliationError,
    find_safe_repairs,
    identity_repair_blockers,
    read_csv,
    reconcile,
    retrieval_index,
)


ROOT = Path(__file__).resolve().parents[1]
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

    def test_current_governed_data_supports_exactly_four_pre_or_post_repair_records(self) -> None:
        _, queue_rows = read_csv(ROOT / "data/curation/review_queue.csv")
        _, retrieval_rows = read_csv(ROOT / "data/curation/retrieval_coverage.csv")
        queue = {row["candidate_id"]: row for row in queue_rows}
        retrieval = retrieval_index(retrieval_rows)
        expected = {
            "CAND-ACADEMIC-2026-09-01-002": "10.1080/17440572.2025.2567277",
            "CAND-ACADEMIC-2026-09-01-003": "10.1007/s13278-025-01506-y",
            "CAND-ACADEMIC-2026-09-01-004": "10.1016/j.ejpoleco.2025.102752",
            "CAND-ACADEMIC-2026-09-01-005": "10.1007/s10610-025-09654-9",
        }

        repairable = {repair["candidate_id"] for repair in find_safe_repairs(queue_rows, retrieval_rows)}
        for candidate_id, expected_doi in expected.items():
            row = queue[candidate_id]
            blockers = identity_repair_blockers(row, retrieval[candidate_id])
            if candidate_id in repairable:
                self.assertEqual(blockers, [])
                self.assertEqual(row["doi"], "")
                self.assertEqual(row["verification_status"], "metadata_partial")
                self.assertEqual(row["review_stage"], "metadata_fix")
            else:
                # The workflow runs this suite after applying repairs, so the
                # governed integration test must also validate the idempotent
                # post-repair state rather than demand that repair stays pending.
                self.assertEqual(row["doi"].lower(), expected_doi.lower())
                self.assertEqual(row["verification_status"], "metadata_verified")
                self.assertEqual(row["metadata_confidence"], "high")
                self.assertEqual(row["review_stage"], "abstract_full_text_review")
                self.assertEqual(row["current_status"], "pending")
                self.assertEqual(row["current_decision"], "")
                self.assertEqual(row["possible_duplicate"], "")
                self.assertEqual(row["metadata_conflict"], "")
                self.assertIn("doi_already_present", blockers)

        self.assertTrue(repairable.issubset(set(expected)))
        self.assertIn(
            "missing_dual_source",
            identity_repair_blockers(
                queue["CAND-ACADEMIC-2026-09-01-006"],
                retrieval["CAND-ACADEMIC-2026-09-01-006"],
            ),
        )

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

    def test_check_fails_when_safe_repair_remains(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_csv(root / "data/curation/review_queue.csv", QUEUE_FIELDS, [queue_row()])
            write_csv(root / "data/curation/retrieval_coverage.csv", RETRIEVAL_FIELDS, [retrieval_row()])
            with self.assertRaises(MetadataReconciliationError):
                reconcile(root, "2026-09-05", check=True)


if __name__ == "__main__":
    unittest.main()
