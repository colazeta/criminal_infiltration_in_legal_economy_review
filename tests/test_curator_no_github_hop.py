from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DirectCuratorWorkflowTests(unittest.TestCase):
    def test_curator_keeps_operational_flow_inside_the_site(self) -> None:
        javascript = (ROOT / "site/curator.js").read_text(encoding="utf-8")
        self.assertIn("configureDirectCuratorNavigation", javascript)
        self.assertIn("Apri nel curatore →", javascript)
        self.assertIn("La proposta richiede la revisione umana della PR prima di essere applicata.", javascript)
        self.assertIn("Continua con la coda", javascript)
        self.assertNotIn("Apri l’istruzione #", javascript)

    def test_scientific_proposal_cannot_merge_automatically(self) -> None:
        workflow = (ROOT / ".github/workflows/candidate-curation.yml").read_text()
        self.assertNotIn("gh pr merge", workflow)
        self.assertIn("An authorised human must review the exact diff", workflow)


if __name__ == "__main__":
    unittest.main()
