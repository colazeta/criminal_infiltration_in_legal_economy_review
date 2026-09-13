from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IntakeAbstractCoverageTests(unittest.TestCase):
    def test_preservation_scaffolds_abstracts_without_network_enrichment(self) -> None:
        source = (ROOT / "scripts/curation/recover_intake_backlog.py").read_text()
        workflow = (ROOT / ".github/workflows/recover-intake-backlog.yml").read_text()
        self.assertLess(source.index("scaffold_all(root, args.date)"), source.index("args.output.write_text"))
        self.assertIn("data/curation/abstract_coverage.csv", workflow)
        self.assertNotIn("backfill_coverage.mjs", workflow)
        self.assertIn("backfill_coverage.mjs", (ROOT / ".github/workflows/abstract-coverage.yml").read_text())

    def test_failed_intake_can_be_replayed_on_the_same_governed_issue(self) -> None:
        workflow = (ROOT / ".github/workflows/intake-to-curation.yml").read_text(encoding="utf-8")
        self.assertIn("types: [opened, reopened]", workflow)
        self.assertIn("github.event.issue.number", workflow)
        self.assertIn("github.actor == github.repository_owner", workflow)

    def test_preservation_persists_every_projection_before_finalisation(self) -> None:
        workflow = (ROOT / ".github/workflows/recover-intake-backlog.yml").read_text()
        for path in ("review_queue.csv", "retrieval_coverage.csv", "abstract_coverage.csv", "access_coverage.csv", "site/data"):
            self.assertIn(path, workflow)
        self.assertLess(workflow.index("Build and validate the complete preservation transaction"), workflow.index("Persist recovered CandidateRecords"))
        self.assertLess(workflow.index("Read back persisted candidate identities"), workflow.index("Finalise source intake issues"))
        self.assertIn("Public deployment is tracked separately", workflow)


if __name__ == "__main__":
    unittest.main()
