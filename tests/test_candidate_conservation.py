from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CandidateConservationWorkflowTests(unittest.TestCase):
    def test_recovery_runs_after_terminal_and_has_periodic_safety_sweep(self) -> None:
        workflow = (ROOT / ".github/workflows/recover-intake-backlog.yml").read_text(encoding="utf-8")
        self.assertIn("issue_comment:", workflow)
        self.assertIn("github.event.issue.number == 30", workflow)
        self.assertIn("surveillance-run:v3", workflow)
        self.assertIn('cron: "55 * * * *"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("group: intake-to-curation-main", workflow)

    def test_automatic_recovery_never_comments_on_or_closes_the_ledger(self) -> None:
        workflow = (ROOT / ".github/workflows/recover-intake-backlog.yml").read_text(encoding="utf-8")
        self.assertIn('if [ "$EVENT_NAME" = "issues" ]', workflow)
        self.assertIn("Candidate-conservation recovery", workflow)
        self.assertIn("Enforce candidate-conservation invariant", workflow)
        self.assertIn("Candidate conservation failed", workflow)


if __name__ == "__main__":
    unittest.main()
