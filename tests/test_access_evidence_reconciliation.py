from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "access" / "reconcile_access_evidence.py"
SPEC = importlib.util.spec_from_file_location("reconcile_access_evidence", MODULE_PATH)
assert SPEC and SPEC.loader
reconcile_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reconcile_module)


class AccessEvidenceReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.queue = [{"candidate_id": "CAND-TEST-001", "title": "Test"}]
        self.coverage = [{
            "candidate_id": "CAND-TEST-001",
            "title": "Test",
            "doi": "10.1000/test",
            "access_status": "restricted",
            "access_kind": "closed_metadata",
            "access_url": "https://doi.org/10.1000/test",
            "evidence_source": "OpenAlex",
            "evidence_detail": "OpenAlex reports closed.",
            "checked_at": "2026-09-02",
            "notes": "",
        }]

    def test_conflicting_governed_full_text_downgrades_restricted_to_unknown(self) -> None:
        rows, changes = reconcile_module.reconcile(
            self.queue,
            self.coverage,
            {"CAND-TEST-001": {"full_text_url": "https://publisher.example/full-text"}},
            {},
        )
        self.assertEqual(rows[0]["access_status"], "unknown")
        self.assertEqual(rows[0]["access_kind"], "conflicting_full_text_evidence")
        self.assertEqual(changes["conflict_to_unknown"], 1)

    def test_positive_assisted_evidence_overrides_closed_metadata(self) -> None:
        evidence = {
            "CAND-TEST-001": {
                "candidate_id": "CAND-TEST-001",
                "access_status": "open",
                "access_kind": "public_full_text",
                "access_url": "https://publisher.example/paper.pdf",
                "evidence_source": "Web browsing verification",
                "evidence_detail": "Full article returned without authentication.",
                "verified_at": "2026-09-02",
            }
        }
        rows, changes = reconcile_module.reconcile(
            self.queue,
            self.coverage,
            {"CAND-TEST-001": {}},
            evidence,
        )
        self.assertEqual(rows[0]["access_status"], "open")
        self.assertEqual(rows[0]["evidence_source"], "Web browsing verification")
        self.assertEqual(changes["assisted_open"], 1)

    def test_reconciliation_is_idempotent(self) -> None:
        evidence = {
            "CAND-TEST-001": {
                "candidate_id": "CAND-TEST-001",
                "access_status": "open",
                "access_kind": "public_full_text",
                "access_url": "https://publisher.example/paper.pdf",
                "evidence_source": "Web browsing verification",
                "evidence_detail": "Full article returned without authentication.",
                "verified_at": "2026-09-02",
            }
        }
        retrieval = {"CAND-TEST-001": {"full_text_url": "https://publisher.example/full-text"}}
        once, _ = reconcile_module.reconcile(self.queue, self.coverage, retrieval, evidence)
        twice, _ = reconcile_module.reconcile(self.queue, once, retrieval, evidence)
        self.assertEqual(twice, once)
        self.assertEqual(
            once[0]["notes"].count("Positive access independently verified by assisted web research."),
            1,
        )

    def test_assisted_evidence_may_not_force_restricted(self) -> None:
        fields = reconcile_module.EVIDENCE_FIELDS
        rows = [{
            "candidate_id": "CAND-TEST-001",
            "access_status": "restricted",
            "access_kind": "closed",
            "access_url": "https://publisher.example/paper",
            "evidence_source": "manual",
            "evidence_detail": "claimed closed",
            "verified_at": "2026-09-02",
        }]
        with self.assertRaises(reconcile_module.EvidenceError):
            reconcile_module.validate_evidence({"CAND-TEST-001"}, fields, rows)

    def test_repository_evidence_file_contains_only_open_positive_rows(self) -> None:
        fields, rows = reconcile_module.read_csv(ROOT / "data/curation/access_evidence.csv")
        validated = reconcile_module.validate_evidence(
            {row["candidate_id"] for row in reconcile_module.read_csv(ROOT / "data/curation/review_queue.csv")[1]},
            fields,
            rows,
        )
        self.assertEqual(len(validated), 2)
        self.assertTrue(all(row["access_status"] == "open" for row in validated.values()))

    def test_workflow_applies_reconciliation_before_persistence(self) -> None:
        workflow = (ROOT / ".github/workflows/access-coverage.yml").read_text(encoding="utf-8")
        self.assertIn("data/curation/access_evidence.csv", workflow)
        self.assertIn("python scripts/access/reconcile_access_evidence.py", workflow)
        self.assertIn("python scripts/access/reconcile_access_evidence.py --check", workflow)
        self.assertIn("scripts/access/reconcile_access_evidence.py", workflow)


if __name__ == "__main__":
    unittest.main()
