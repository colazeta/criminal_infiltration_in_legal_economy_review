from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CuratorQueueSurfaceTests(unittest.TestCase):
    def test_queue_cards_are_bibliographic_and_paginated(self) -> None:
        javascript = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        self.assertIn("const PAGE_SIZE = 12", javascript)
        self.assertIn("candidate-queue-pager", javascript)
        self.assertIn("queue-card-authors", javascript)
        self.assertIn("queue-card-citation", javascript)
        self.assertIn("queue-card-doi", javascript)
        self.assertIn("candidate?.venue", javascript)
        self.assertIn("candidate?.year", javascript)
        self.assertIn("candidate?.doi", javascript)
        self.assertNotIn(".innerHTML", javascript)
        self.assertNotIn("localStorage", javascript)

    def test_abstract_availability_is_lazy_bounded_and_multi_source(self) -> None:
        javascript = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        self.assertIn("const MAX_ENRICHMENT_CONCURRENCY = 3", javascript)
        self.assertIn("IntersectionObserver", javascript)
        self.assertIn('rootMargin: "180px 0px"', javascript)
        self.assertIn('/api/enrichment', javascript)
        self.assertIn('/api/resolved-abstract', javascript)
        self.assertIn("Abstract disponibile", javascript)
        self.assertIn("Ricerca web necessaria", javascript)
        self.assertIn("Abstract non trovato", javascript)
        self.assertIn("Abstract non verificato", javascript)
        self.assertIn("providersTried", javascript)
        self.assertIn("needs_web_search", javascript)
        self.assertIn("web_search_exhausted", javascript)
        self.assertNotIn('badge.textContent = "Abstract assente"', javascript)

    def test_queue_uses_authenticated_candidate_projection(self) -> None:
        javascript = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        self.assertIn('/api/candidates', javascript)
        self.assertIn('sessionStorage.getItem(SESSION_KEY)', javascript)
        self.assertIn('Authorization: `Bearer ${token}`', javascript)

    def test_queue_component_is_loaded_and_served_by_worker(self) -> None:
        config = (ROOT / "site/curator-config.js").read_text(encoding="utf-8")
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        self.assertIn('loadCuratorComponent("./curator-queue.js", "curator-queue")', config)
        self.assertIn('"/curator-queue.js"', worker)
        self.assertIn('"/curator-queue.css"', worker)
        self.assertIn('curator-queue.js', worker)
        self.assertIn('curator-queue', worker)

    def test_deploy_and_ci_track_queue_assets(self) -> None:
        deploy = (ROOT / ".github/workflows/deploy-curator-worker.yml").read_text(encoding="utf-8")
        archive = (ROOT / ".github/workflows/archive.yml").read_text(encoding="utf-8")
        self.assertIn('site/curator-queue.js', deploy)
        self.assertIn('site/curator-queue.css', deploy)
        self.assertIn('candidate-queue-pager', deploy)
        self.assertIn('EXA_API_KEY', deploy)
        self.assertGreaterEqual(archive.count('node --check site/curator-queue.js'), 2)
        self.assertGreaterEqual(archive.count('node --check curator-app/src/scholarly-providers.js'), 2)

    def test_queue_styles_prioritise_readability(self) -> None:
        css = (ROOT / "site/curator-queue.css").read_text(encoding="utf-8")
        self.assertIn(".queue-card-authors", css)
        self.assertIn(".queue-card-citation", css)
        self.assertIn(".queue-card-doi", css)
        self.assertIn(".queue-card-chip", css)
        self.assertIn(".candidate-queue-pager", css)


if __name__ == "__main__":
    unittest.main()
