from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IntakeAbstractCoverageTests(unittest.TestCase):
    def test_intake_updates_abstract_coverage_before_repository_validation(self) -> None:
        workflow = (ROOT / ".github/workflows/intake-to-curation.yml").read_text(encoding="utf-8")
        backfill = workflow.index("Backfill abstract coverage for the expanded queue")
        validation = workflow.index("Validate the complete archive")
        self.assertLess(backfill, validation)
        self.assertIn("scripts/abstracts/backfill_coverage.mjs", workflow)
        self.assertIn("--summary \"$RUNNER_TEMP/abstract-coverage-summary.json\"", workflow)
        self.assertIn("scripts/abstracts/backfill_coverage.mjs --check", workflow)
        self.assertIn("pdftotext", workflow)
        self.assertIn("node-version: 22", workflow)

    def test_failed_intake_can_be_replayed_on_the_same_governed_issue(self) -> None:
        workflow = (ROOT / ".github/workflows/intake-to-curation.yml").read_text(encoding="utf-8")
        self.assertIn("types: [opened, reopened]", workflow)
        self.assertIn("github.event.issue.number", workflow)
        self.assertIn("github.actor == github.repository_owner", workflow)

    def test_intake_branch_persists_all_curation_coverage_artifacts(self) -> None:
        workflow = (ROOT / ".github/workflows/intake-to-curation.yml").read_text(encoding="utf-8")
        self.assertIn("git add data/curation site/data/curator-stats.json", workflow)
        self.assertIn("Abstract coverage:", workflow)
        self.assertIn("Reading-aid reconciliation:", workflow)
        self.assertIn("Access coverage:", workflow)
        self.assertIn("the preceding steps only make each paper reviewable and auditable", workflow)


if __name__ == "__main__":
    unittest.main()
