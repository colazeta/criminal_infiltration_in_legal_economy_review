from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CuratorPriorityViewTests(unittest.TestCase):
    def test_priority_views_use_only_existing_provenance(self) -> None:
        javascript = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        self.assertIn('provenanceValue(candidate, "Intake assessment")', javascript)
        self.assertIn('assessment === "plausible_core"', javascript)
        self.assertIn('assessment === "plausible_contextual"', javascript)
        self.assertIn('provenanceValue(candidate, "Legacy scope label")', javascript)
        self.assertIn('legacyScope === "outside_scope"', javascript)
        self.assertIn('candidate.stageLabel === "stage:legacy-rejection-review"', javascript)

    def test_priority_views_are_presentational_not_decisional(self) -> None:
        javascript = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        self.assertIn("candidate-triage-filter", javascript)
        self.assertIn("Priorità core (intake)", javascript)
        self.assertIn("Confine da valutare", javascript)
        self.assertIn("Riesame rapido (segnale legacy)", javascript)
        self.assertIn("non è una decisione scientifica", javascript)
        self.assertNotIn('/api/decisions', javascript)
        self.assertNotIn('eligible_core', javascript)
        self.assertNotIn('not_eligible', javascript)

    def test_queue_filter_remains_client_side(self) -> None:
        javascript = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        self.assertIn('card.dataset.triage', javascript)
        self.assertIn('currentCards()', javascript)
        self.assertNotIn('innerHTML', javascript)


if __name__ == "__main__":
    unittest.main()
