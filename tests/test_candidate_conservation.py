from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CandidateConservationWorkflowTests(unittest.TestCase):
    def _recovery(self) -> str:
        return (ROOT / ".github/workflows/recover-intake-backlog.yml").read_text(encoding="utf-8")

    def _intake(self) -> str:
        return (ROOT / ".github/workflows/intake-to-curation.yml").read_text(encoding="utf-8")

    def test_recovery_runs_after_terminal_and_has_periodic_safety_sweep(self) -> None:
        workflow = self._recovery()
        self.assertIn("issue_comment:", workflow)
        self.assertIn("github.event.issue.number == 30", workflow)
        self.assertIn("surveillance-run:v3", workflow)
        self.assertIn('cron: "55 * * * *"', workflow)
        self.assertIn("workflow_dispatch:", workflow)

    def test_terminal_recovery_is_single_candidate_writer(self) -> None:
        recovery = self._recovery()
        intake = self._intake()
        self.assertIn("group: candidate-conservation-main", recovery)
        self.assertIn("cancel-in-progress: false", recovery)
        self.assertIn("sole automatic CandidateRecord writer", recovery)
        self.assertNotIn("stage_intake.py", intake)
        self.assertNotIn("resolve_queue.py", intake)
        self.assertIn("defer-to-terminal-recovery", intake)
        self.assertIn("surveillance terminal is written after the intake", intake)

    def test_recovery_persists_before_source_intake_finalisation(self) -> None:
        workflow = self._recovery()
        barrier = workflow.index("Persist recovered CandidateRecords")
        finalise = workflow.index("Finalise source intake issues after persistence")
        self.assertLess(barrier, finalise)
        self.assertIn("data/curation/review_queue.csv", workflow)
        self.assertIn("data/curation/intake_access", workflow)

    def test_recovery_contains_no_optional_enrichment_before_completion(self) -> None:
        workflow = self._recovery()
        self.assertNotIn("resolve_queue.py", workflow)
        self.assertNotIn("backfill_coverage.mjs", workflow)
        self.assertNotIn("classify_access.py", workflow)
        self.assertNotIn("reconcile_reading_aids.py", workflow)

    def test_persistence_failure_is_a_conservation_failure(self) -> None:
        workflow = self._recovery()
        self.assertIn("steps.persist.outputs.persisted != 'true'", workflow)
        self.assertIn("did not cross the persistence barrier", workflow)


if __name__ == "__main__":
    unittest.main()
