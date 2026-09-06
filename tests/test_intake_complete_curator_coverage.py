from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IntakeCompleteCuratorCoverageTests(unittest.TestCase):
    def test_intake_builds_all_reviewability_layers_before_validation(self) -> None:
        workflow = (ROOT / ".github/workflows/intake-to-curation.yml").read_text(encoding="utf-8")
        retrieval = workflow.index("Resolve paper access for the complete queue")
        abstracts = workflow.index("Backfill abstract coverage for the expanded queue")
        aids = workflow.index("Reconcile reading aids for unresolved abstracts")
        access = workflow.index("Classify access for the expanded queue")
        validation = workflow.index("Validate the complete archive")
        self.assertLess(retrieval, abstracts)
        self.assertLess(abstracts, aids)
        self.assertLess(aids, access)
        self.assertLess(access, validation)
        self.assertIn("scripts/curation/reconcile_reading_aids.py --check", workflow)
        self.assertIn("scripts/access/classify_access.py --check", workflow)
        self.assertIn("scripts/access/reconcile_access_evidence.py --check", workflow)

    def test_researched_overrides_cover_current_new_unresolved_records(self) -> None:
        payload = json.loads(
            (ROOT / "config/curation/intake-reading-aid-overrides.json").read_text(encoding="utf-8")
        )
        records = {row["candidateId"]: row for row in payload["records"]}
        self.assertEqual(
            set(records),
            {"CAND-ACADEMIC-2026-09-06-002", "CAND-ACADEMIC-2026-09-06-007"},
        )
        self.assertEqual(records["CAND-ACADEMIC-2026-09-06-002"]["kind"], "verified_abstract_source")
        self.assertEqual(records["CAND-ACADEMIC-2026-09-06-007"]["kind"], "publisher_summary")
        for record in records.values():
            self.assertTrue(record["sourceUrl"].startswith("https://"))
            self.assertTrue(record["synopsis"])
            self.assertTrue(record["note"])

    def test_reconciler_preserves_human_boundary(self) -> None:
        script = (ROOT / "scripts/curation/reconcile_reading_aids.py").read_text(encoding="utf-8")
        self.assertIn('"review_synopsis"', script)
        self.assertIn("not an author abstract", script)
        self.assertIn("cannot determine eligibility", script)
        self.assertIn("daily_surveillance", script)
        self.assertNotIn("eligible_core", script)
        self.assertNotIn("current_decision", script)


if __name__ == "__main__":
    unittest.main()
