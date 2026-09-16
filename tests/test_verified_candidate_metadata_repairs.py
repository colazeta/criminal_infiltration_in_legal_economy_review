from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.curation.apply_verified_candidate_metadata_repairs import (
    VerifiedMetadataRepairError,
    find_safe_repairs,
    load_declarations,
    reconcile,
)


QUEUE_FIELDS = [
    "candidate_id",
    "title",
    "doi",
    "authors",
    "year",
    "venue",
    "work_type",
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


def queue_row(**overrides: str) -> dict[str, str]:
    row = {
        "candidate_id": "CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-016",
        "title": "Evaluating risks-based communities of Mafia companies: a complex networks perspective",
        "doi": "10.1007/s11156-021-00984-3",
        "authors": "Nicola Giuseppe Castellano; Roy Cerqueti; Bruno Maria Franceschetti",
        "year": "2021",
        "venue": "",
        "work_type": "unknown",
        "source_links": "https://doi.org/10.1007/s11156-021-00984-3",
        "verification_status": "metadata_partial",
        "metadata_confidence": "",
        "intake_assessment": "uncertain",
        "possible_duplicate": "",
        "metadata_conflict": "",
        "origin": "daily_surveillance",
        "review_stage": "metadata_fix",
        "current_status": "pending",
        "current_decision": "",
        "updated_at": "2026-09-08",
    }
    row.update(overrides)
    return row


def ledger(candidate_id: str | None = None) -> dict:
    candidate_id = candidate_id or queue_row()["candidate_id"]
    return {
        "schemaVersion": 1,
        "purpose": "test fixture",
        "repairs": [
            {
                "candidate_id": candidate_id,
                "expected": {
                    "title": queue_row()["title"],
                    "doi": queue_row()["doi"],
                    "authors": queue_row()["authors"],
                    "year": "2021",
                    "venue": "",
                    "verification_status": "metadata_partial",
                    "metadata_confidence": "",
                    "review_stage": "metadata_fix",
                    "current_status": "pending",
                    "current_decision": "",
                    "possible_duplicate": "",
                    "metadata_conflict": "",
                },
                "replacement": {"venue": "Review of Quantitative Finance and Accounting"},
                "evidence": [
                    {"role": "primary_metadata", "url": "https://link.springer.com/article/10.1007/s11156-021-00984-3"},
                    {"role": "independent_institutional", "url": "https://iris.uniroma1.it/handle/11573/1542906"},
                ],
                "checked_at": "2026-09-15",
                "basis": "Two independent bibliographic sources agree on the article manifestation.",
            }
        ],
    }


def write_queue(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=QUEUE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_ledger(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class VerifiedCandidateMetadataRepairTests(unittest.TestCase):
    def test_reviewed_repair_updates_only_bibliographic_and_mechanical_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = queue_row()
            write_queue(root / "data/curation/review_queue.csv", [original])
            write_ledger(root / "data/curation/verified_candidate_metadata_repairs.json", ledger())
            summary = reconcile(root, "2026-09-16")
            self.assertEqual(summary["candidate_ids"], [original["candidate_id"]])
            with (root / "data/curation/review_queue.csv").open(newline="", encoding="utf-8") as handle:
                repaired = next(csv.DictReader(handle))
            self.assertEqual(repaired["venue"], "Review of Quantitative Finance and Accounting")
            self.assertEqual(repaired["verification_status"], "metadata_verified")
            self.assertEqual(repaired["metadata_confidence"], "high")
            self.assertEqual(repaired["review_stage"], "abstract_full_text_review")
            self.assertEqual(repaired["intake_assessment"], original["intake_assessment"])
            self.assertEqual(repaired["current_status"], "pending")
            self.assertEqual(repaired["current_decision"], "")
            self.assertEqual(repaired["source_links"], original["source_links"])
            self.assertEqual(repaired["updated_at"], "2026-09-16")
            self.assertEqual(reconcile(root, "2026-09-16")["safe_verified_metadata_repairs"], 0)

    def test_stale_expected_value_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_queue(root / "data/curation/review_queue.csv", [queue_row(venue="Already changed")])
            write_ledger(root / "data/curation/verified_candidate_metadata_repairs.json", ledger())
            with self.assertRaises(VerifiedMetadataRepairError):
                reconcile(root, "2026-09-16")

    def test_existing_decision_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_queue(root / "data/curation/review_queue.csv", [queue_row(current_status="reviewed", current_decision="not_eligible")])
            payload = ledger()
            payload["repairs"][0]["expected"]["current_status"] = "reviewed"
            payload["repairs"][0]["expected"]["current_decision"] = "not_eligible"
            write_ledger(root / "data/curation/verified_candidate_metadata_repairs.json", payload)
            with self.assertRaises(VerifiedMetadataRepairError):
                reconcile(root, "2026-09-16")

    def test_duplicate_or_conflict_fails_closed(self) -> None:
        for field in ("possible_duplicate", "metadata_conflict"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                row = queue_row(**{field: "unresolved"})
                payload = ledger()
                payload["repairs"][0]["expected"][field] = "unresolved"
                write_queue(root / "data/curation/review_queue.csv", [row])
                write_ledger(root / "data/curation/verified_candidate_metadata_repairs.json", payload)
                with self.assertRaises(VerifiedMetadataRepairError):
                    reconcile(root, "2026-09-16")

    def test_ledger_requires_independent_https_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_queue(root / "data/curation/review_queue.csv", [queue_row()])
            payload = ledger()
            payload["repairs"][0]["evidence"] = [
                {"role": "primary_metadata", "url": "https://example.test/one"},
                {"role": "independent_institutional", "url": "https://example.test/one"},
            ]
            write_ledger(root / "data/curation/verified_candidate_metadata_repairs.json", payload)
            with self.assertRaises(VerifiedMetadataRepairError):
                load_declarations(root)

    def test_check_fails_while_reviewed_repair_is_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_queue(root / "data/curation/review_queue.csv", [queue_row()])
            write_ledger(root / "data/curation/verified_candidate_metadata_repairs.json", ledger())
            declarations = load_declarations(root)
            self.assertEqual(len(find_safe_repairs([queue_row()], declarations)), 1)
            with self.assertRaises(VerifiedMetadataRepairError):
                reconcile(root, "2026-09-16", check=True)


if __name__ == "__main__":
    unittest.main()
