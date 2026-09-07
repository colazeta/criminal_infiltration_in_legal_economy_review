from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CuratorInlineReviewSupportTests(unittest.TestCase):
    def test_worker_parses_governed_support_once_with_retrieval_context(self) -> None:
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        self.assertIn("Reading aid — preparatory", worker)
        self.assertIn("Review guidance — preparatory", worker)
        self.assertIn("Abstract resolution — assisted", worker)
        self.assertIn("parseReviewSupport", worker)
        self.assertIn("reviewSupport", worker)
        self.assertIn("assistedResolution", worker)
        self.assertIn("Candidate-specific focus", (ROOT / "site/curator-reading.js").read_text(encoding="utf-8"))

    def test_reading_surface_consumes_support_from_same_origin_context(self) -> None:
        javascript = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        self.assertIn("/api/retrieval", javascript)
        self.assertIn("context?.reviewSupport", javascript)
        self.assertIn("Review synopsis", javascript)
        self.assertIn("promoteSynthesis", javascript)
        self.assertIn("metadataFallback", javascript)
        self.assertIn("contextCache", javascript)
        self.assertNotIn("api.github.com", javascript)
        self.assertNotIn("payload?.body", javascript)

    def test_support_is_read_only_and_does_not_become_a_decision(self) -> None:
        javascript = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        self.assertNotIn('/api/decisions', javascript)
        self.assertNotIn('decision-rationale', javascript)
        self.assertNotIn('explicit-confirmation', javascript)
        self.assertNotIn('.innerHTML', javascript)
        self.assertIn("Sintesi sostitutiva", javascript)
        self.assertIn("Fallback descrittivo limitato ai metadati", javascript)
        self.assertIn("non è l’abstract dell’autore", javascript)

    def test_support_is_bound_to_selected_candidate_and_aborted_on_navigation(self) -> None:
        javascript = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        self.assertIn("selectedIssueNumber", javascript)
        self.assertIn("activeCandidateId", javascript)
        self.assertIn('activeController?.abort("candidate_changed")', javascript)
        self.assertIn("contextCache", javascript)
        self.assertIn("activeCandidateId !== candidateId", javascript)


if __name__ == "__main__":
    unittest.main()
