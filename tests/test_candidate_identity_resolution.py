from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.curation.resolve_candidate_identity import (
    IdentityResolutionError,
    load_ledger,
    resolve,
    validate_resolution,
)


ROOT = Path(__file__).resolve().parents[1]
QUEUE_FIELDS = [
    "candidate_id",
    "title",
    "doi",
    "source_links",
    "verification_status",
    "metadata_confidence",
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


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def queue_row(**overrides: str) -> dict[str, str]:
    note = "Possible working-paper manifestation; unresolved."
    row = {
        "candidate_id": "CAND-TEST-001",
        "title": "Mafias and Firms",
        "doi": "",
        "source_links": "https://example.test/intake",
        "verification_status": "metadata_partial",
        "metadata_confidence": "",
        "possible_duplicate": note,
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
        "candidate_id": "CAND-TEST-001",
        "title": "Mafias and Firms",
        "resolved_doi": "10.31235/osf.io/sr6ep_v1",
        "doi_url": "https://doi.org/10.31235/osf.io/sr6ep_v1",
        "resolution_sources": "OpenAlex; Crossref; EconStor via Parallel Search",
        "match_method": "OpenAlex:title_year; Crossref:title_year; Parallel Search:exact_title_authors_year; EconStor:repository_pdf",
        "match_confidence": "high",
        "checked_at": "2026-09-12",
    }
    row.update(overrides)
    return row


def write_ledger(path: Path, blocker: str, **overrides: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry: dict[str, object] = {
        "candidate_id": "CAND-TEST-001",
        "resolution": "same_work_manifestation",
        "expected_possible_duplicate_sha256": hashlib.sha256(blocker.encode("utf-8")).hexdigest(),
        "resolved_doi": "10.31235/osf.io/sr6ep_v1",
        "evidence_sources": ["OpenAlex", "Crossref", "EconStor via Parallel Search"],
        "evidence_methods": [
            "OpenAlex:title_year",
            "Crossref:title_year",
            "Parallel Search:exact_title_authors_year",
            "EconStor:repository_pdf",
        ],
        "checked_at": "2026-09-15",
        "basis": "Reviewed exact title/authors/year evidence resolves the stale manifestation ambiguity.",
    }
    entry.update(overrides)
    path.write_text(json.dumps({"schemaVersion": 1, "resolutions": [entry]}), encoding="utf-8")


class CandidateIdentityResolutionTests(unittest.TestCase):
    def test_reviewed_resolution_clears_only_stale_identity_blocker_and_advances_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = queue_row()
            write_csv(root / "data/curation/review_queue.csv", QUEUE_FIELDS, [original])
            write_csv(root / "data/curation/retrieval_coverage.csv", RETRIEVAL_FIELDS, [retrieval_row()])
            write_ledger(root / "data/curation/verified_identity_resolutions.json", original["possible_duplicate"])

            summary = resolve(root, "2026-09-15")
            self.assertEqual(summary["safe_identity_resolutions"], 1)
            with (root / "data/curation/review_queue.csv").open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["possible_duplicate"], "")
            self.assertEqual(row["doi"], "10.31235/osf.io/sr6ep_v1")
            self.assertEqual(row["verification_status"], "metadata_verified")
            self.assertEqual(row["metadata_confidence"], "high")
            self.assertEqual(row["review_stage"], "abstract_full_text_review")
            self.assertEqual(row["current_status"], "pending")
            self.assertEqual(row["current_decision"], "")
            self.assertEqual(row["metadata_conflict"], "")
            self.assertIn("https://doi.org/10.31235/osf.io/sr6ep_v1", row["source_links"])
            self.assertEqual(row["updated_at"], "2026-09-15")

    def test_changed_blocker_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = queue_row()
            write_csv(root / "data/curation/review_queue.csv", QUEUE_FIELDS, [original])
            write_csv(root / "data/curation/retrieval_coverage.csv", RETRIEVAL_FIELDS, [retrieval_row()])
            write_ledger(root / "data/curation/verified_identity_resolutions.json", "different historical note")
            with self.assertRaises(IdentityResolutionError):
                resolve(root, "2026-09-15")

    def test_conflict_or_non_high_confidence_fails_closed(self) -> None:
        blocker = queue_row()["possible_duplicate"]
        declaration = {
            "candidate_id": "CAND-TEST-001",
            "resolution": "same_work_manifestation",
            "expected_possible_duplicate_sha256": hashlib.sha256(blocker.encode("utf-8")).hexdigest(),
            "resolved_doi": "10.31235/osf.io/sr6ep_v1",
            "evidence_sources": ["OpenAlex", "Crossref", "EconStor via Parallel Search"],
            "evidence_methods": [
                "OpenAlex:title_year",
                "Crossref:title_year",
                "Parallel Search:exact_title_authors_year",
                "EconStor:repository_pdf",
            ],
            "checked_at": "2026-09-15",
            "basis": "reviewed",
        }
        with self.assertRaises(IdentityResolutionError):
            validate_resolution(declaration, queue_row(metadata_conflict="year conflict"), retrieval_row())
        with self.assertRaises(IdentityResolutionError):
            validate_resolution(declaration, queue_row(), retrieval_row(match_confidence="medium"))

    def test_check_fails_until_reviewed_resolution_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = queue_row()
            write_csv(root / "data/curation/review_queue.csv", QUEUE_FIELDS, [original])
            write_csv(root / "data/curation/retrieval_coverage.csv", RETRIEVAL_FIELDS, [retrieval_row()])
            write_ledger(root / "data/curation/verified_identity_resolutions.json", original["possible_duplicate"])
            with self.assertRaises(IdentityResolutionError):
                resolve(root, "2026-09-15", check=True)
            resolve(root, "2026-09-15")
            self.assertEqual(resolve(root, "2026-09-15", check=True)["safe_identity_resolutions"], 0)

    def test_current_governed_mafias_and_firms_declaration_is_live_or_already_applied(self) -> None:
        declarations = load_ledger(ROOT)
        target = next(
            item
            for item in declarations
            if item["candidate_id"] == "CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-003"
        )
        with (ROOT / "data/curation/review_queue.csv").open(newline="", encoding="utf-8-sig") as handle:
            queue = {row["candidate_id"]: row for row in csv.DictReader(handle)}
        with (ROOT / "data/curation/retrieval_coverage.csv").open(newline="", encoding="utf-8-sig") as handle:
            retrieval = {row["candidate_id"]: row for row in csv.DictReader(handle)}
        result = validate_resolution(target, queue[target["candidate_id"]], retrieval[target["candidate_id"]])
        self.assertIn(result["status"], {"apply", "already_applied"})


if __name__ == "__main__":
    unittest.main()
