from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CuratorInlineReviewSupportTests(unittest.TestCase):
    def test_reading_surface_renders_governed_support_next_to_decision_form(self) -> None:
        javascript = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        self.assertIn("Reading aid — preparatory", javascript)
        self.assertIn("Review guidance — preparatory", javascript)
        self.assertIn("candidate-reading-aid-panel", javascript)
        self.assertIn("candidate-review-guidance-panel", javascript)
        self.assertIn("Candidate-specific focus", javascript)
        self.assertIn("Suggested screening stage", javascript)
        self.assertIn("How to approach this record", javascript)
        self.assertIn("maybe_full_text_needed", javascript)
        self.assertIn("eligible_core", javascript)
        self.assertIn("api.github.com/repos/", javascript)

    def test_support_is_read_only_and_does_not_become_a_decision(self) -> None:
        javascript = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        self.assertNotIn('/api/decisions', javascript)
        self.assertNotIn('decision-rationale', javascript)
        self.assertNotIn('explicit-confirmation', javascript)
        self.assertNotIn('.innerHTML', javascript)
        self.assertIn("La guida non decide per te", javascript)
        self.assertIn("Synopsis preparatoria", javascript)
        self.assertIn("Avviso metadati", javascript)

    def test_support_is_bound_to_the_selected_materialised_issue(self) -> None:
        javascript = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        self.assertIn('selected-candidate-issue', javascript)
        self.assertIn('/issues\\/(\\d+)', javascript)
        self.assertIn('supportCache', javascript)
        self.assertIn('payload?.body', javascript)


if __name__ == "__main__":
    unittest.main()
