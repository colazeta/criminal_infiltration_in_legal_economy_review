from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CuratorAbstractFallbackTests(unittest.TestCase):
    def test_queue_and_reading_use_resolved_paper_fallback(self) -> None:
        queue = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        reading = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        for source in (queue, reading):
            self.assertIn("/api/enrichment", source)
            self.assertIn("/api/resolved-abstract", source)
            self.assertIn("resolved_url", source)
            self.assertIn("Paper risolto", source)
        self.assertIn("candidate.issueNumber", queue)
        self.assertIn("selectedIssueNumber", reading)

    def test_worker_binds_resolved_abstract_to_governed_retrieval(self) -> None:
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        module = (ROOT / "curator-app/src/resolved-abstract.js").read_text(encoding="utf-8")
        self.assertIn('url.pathname === "/api/resolved-abstract"', worker)
        self.assertIn("authenticatedRetrieval(request, env)", worker)
        self.assertIn("handleResolvedAbstractRequest(request, retrieval)", worker)
        self.assertNotIn("url.searchParams.get(\"resolved_url\")", module)
        self.assertIn("safePublicHttpsUrl", module)
        self.assertIn("citation_abstract", module)
        self.assertIn("application\\/ld\\+json", module)

    def test_abstract_fallback_remains_ephemeral(self) -> None:
        module = (ROOT / "curator-app/src/resolved-abstract.js").read_text(encoding="utf-8")
        self.assertNotIn("data/curation", module)
        self.assertNotIn("review_queue.csv", module)
        self.assertNotIn("retrieval_coverage.csv", module)
        self.assertNotIn("githubRequest", module)


if __name__ == "__main__":
    unittest.main()
