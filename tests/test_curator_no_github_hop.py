from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DirectCuratorWorkflowTests(unittest.TestCase):
    def test_curator_keeps_operational_flow_inside_the_site(self) -> None:
        javascript = (ROOT / "site/curator.js").read_text(encoding="utf-8")
        self.assertIn("configureDirectCuratorNavigation", javascript)
        self.assertIn("Apri nel curatore →", javascript)
        self.assertIn("Non devi aprire GitHub o approvare una seconda volta.", javascript)
        self.assertIn("Continua con la coda", javascript)
        self.assertNotIn("Apri l’istruzione #", javascript)

    def test_authenticated_decision_is_applied_after_validation(self) -> None:
        workflow = (ROOT / ".github/workflows/candidate-curation.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn('gh pr merge "$pr_url" --merge --delete-branch', workflow)
        self.assertIn("Decision applied automatically after validation", workflow)
        self.assertNotIn("an authorised person must inspect and merge this PR", workflow)


if __name__ == "__main__":
    unittest.main()
