from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CandidateConservationWorkflowTests(unittest.TestCase):
    def _workflow(self) -> str:
        return (ROOT / ".github/workflows/recover-intake-backlog.yml").read_text(encoding="utf-8")

    def test_recovery_runs_after_terminal_and_has_periodic_safety_sweep(self) -> None:
        workflow = self._workflow()
        self.assertIn("issue_comment:", workflow)
        self.assertIn("github.event.issue.number == 30", workflow)
        self.assertIn("surveillance-run:v3", workflow)
        self.assertIn('cron: "55 * * * *"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("group: intake-to-curation-main", workflow)

    def test_automatic_recovery_never_comments_on_or_closes_the_ledger(self) -> None:
        workflow = self._workflow()
        self.assertIn('if [ "$EVENT_NAME" = "issues" ]', workflow)
        self.assertIn("Candidate-conservation recovery", workflow)
        self.assertIn("Enforce candidate-conservation invariant", workflow)
        self.assertIn("Candidate conservation failed", workflow)

    def test_candidate_records_cross_persistence_barrier_before_enrichment(self) -> None:
        workflow = self._workflow()
        barrier = workflow.index("Persist recovered CandidateRecords first")
        finalise = workflow.index("Finalise intake issues after preservation barrier")
        retrieval = workflow.index("Resolve paper access for preserved candidates")
        abstracts = workflow.index("Backfill abstract coverage for preserved candidates")
        self.assertLess(barrier, finalise)
        self.assertLess(finalise, retrieval)
        self.assertLess(barrier, abstracts)
        self.assertIn("continue-on-error: true", workflow)
        self.assertIn("Optional enrichment may continue independently", workflow)

    def test_core_persistence_failure_is_a_conservation_failure(self) -> None:
        workflow = self._workflow()
        self.assertIn("steps.core_persist.outputs.persisted != 'true'", workflow)
        self.assertIn("did not cross the persistence barrier", workflow)


if __name__ == "__main__":
    unittest.main()
