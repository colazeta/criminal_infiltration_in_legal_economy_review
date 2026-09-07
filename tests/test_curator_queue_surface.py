from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CuratorQueueSurfaceTests(unittest.TestCase):
    def test_queue_rows_are_bibliographic_and_paginated(self) -> None:
        javascript = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        self.assertIn("const PAGE_SIZE = 12", javascript)
        self.assertIn("candidate-queue-pager", javascript)
        self.assertIn("candidate-grid-header", javascript)
        self.assertIn("queue-card-authors", javascript)
        self.assertIn("queue-card-citation", javascript)
        self.assertIn("queue-card-doi", javascript)
        self.assertIn("candidate?.venue", javascript)
        self.assertIn("candidate?.year", javascript)
        self.assertIn("candidate?.doi", javascript)
        self.assertNotIn(".innerHTML", javascript)
        self.assertNotIn("localStorage", javascript)

    def test_queue_is_navigation_only_and_never_runs_scholarly_retrieval(self) -> None:
        javascript = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        self.assertNotIn("MAX_ENRICHMENT_CONCURRENCY", javascript)
        self.assertNotIn("IntersectionObserver", javascript)
        self.assertNotIn("enrichmentQueue", javascript)
        self.assertNotIn("enrichmentCache", javascript)
        self.assertNotIn("/api/enrichment", javascript)
        self.assertNotIn("/api/resolved-abstract", javascript)
        self.assertNotIn("/api/free-web-search", javascript)
        for provider_marker in (
            "api.openalex.org",
            "api.crossref.org",
            "api.semanticscholar.org",
            "google.serper.dev",
            "api.exa.ai",
            "api.tavily.com",
            "r.jina.ai",
        ):
            self.assertNotIn(provider_marker, javascript)

    def test_queue_uses_authenticated_candidate_projection(self) -> None:
        javascript = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        self.assertIn('/api/candidates', javascript)
        self.assertIn('sessionStorage.getItem(SESSION_KEY)', javascript)
        self.assertIn('Authorization: `Bearer ${token}`', javascript)

    def test_queue_priority_view_uses_only_materialised_provenance(self) -> None:
        javascript = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        self.assertIn('provenanceValue(candidate, "Intake assessment")', javascript)
        self.assertIn('provenanceValue(candidate, "Legacy scope label")', javascript)
        self.assertIn("priority_core", javascript)
        self.assertIn("boundary", javascript)
        self.assertIn("legacy_fast_recheck", javascript)

    def test_queue_component_is_loaded_and_served_by_worker(self) -> None:
        config = (ROOT / "site/curator-config.js").read_text(encoding="utf-8")
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        self.assertIn('loadCuratorComponent("./curator-queue.js", "curator-queue")', config)
        self.assertIn('"/curator-queue.js"', worker)
        self.assertIn('"/curator-queue.css"', worker)

    def test_deploy_and_ci_track_queue_assets(self) -> None:
        deploy = (ROOT / ".github/workflows/deploy-curator-worker.yml").read_text(encoding="utf-8")
        archive = (ROOT / ".github/workflows/archive.yml").read_text(encoding="utf-8")
        self.assertIn('site/curator-queue.js', deploy)
        self.assertIn('site/curator-queue.css', deploy)
        self.assertIn('candidate-queue-pager', deploy)
        self.assertGreaterEqual(archive.count('node --check site/curator-queue.js'), 2)

    def test_queue_styles_prioritise_master_table_readability(self) -> None:
        css = (ROOT / "site/curator-queue.css").read_text(encoding="utf-8")
        self.assertIn(".candidate-grid-header", css)
        self.assertIn(".queue-card-authors", css)
        self.assertIn(".queue-card-citation", css)
        self.assertIn(".queue-card-doi", css)
        self.assertIn(".candidate-queue-pager", css)
        self.assertIn("grid-template-columns:", css)


if __name__ == "__main__":
    unittest.main()
