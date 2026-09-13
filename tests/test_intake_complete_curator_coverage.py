from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IntakeCompleteCuratorCoverageTests(unittest.TestCase):
    def test_reviewability_enrichment_cannot_block_candidate_preservation(self) -> None:
        workflow = (ROOT / ".github/workflows/recover-intake-backlog.yml").read_text()
        for network_script in ("resolve_queue.py", "backfill_coverage.mjs", "reconcile_reading_aids.py", "classify_access.py"):
            self.assertNotIn(network_script, workflow)
        self.assertIn("python scripts/ontology/validate_ontology.py", workflow)
        self.assertIn("python scripts/curation/build_curator_stats.py", workflow)
        self.assertIn("site/data", workflow)
        scaffold = (ROOT / "scripts/curation/scaffold_candidate_coverage.py").read_text()
        for status in ('"unresolved"', '"needs_web_search"', '"unknown"'):
            self.assertIn(status, scaffold)
        self.assertIn("preserves every existing enriched row", scaffold)

    def test_retained_overrides_do_not_reintroduce_the_retired_provider(self) -> None:
        payload = json.loads(
            (ROOT / "config/curation/intake-reading-aid-overrides.json").read_text(encoding="utf-8")
        )
        records = {row["candidateId"]: row for row in payload["records"]}
        self.assertEqual(
            set(records),
            {"CAND-ACADEMIC-2026-09-06-007"},
        )
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
