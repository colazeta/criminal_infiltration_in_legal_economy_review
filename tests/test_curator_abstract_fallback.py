from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CuratorAbstractFallbackTests(unittest.TestCase):
    def test_queue_does_not_retrieve_abstracts_and_reader_is_context_first(self) -> None:
        queue = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        reading = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        for endpoint in ("/api/enrichment", "/api/resolved-abstract", "/api/free-web-search"):
            self.assertNotIn(endpoint, queue)
        self.assertIn("/api/retrieval", reading)
        self.assertIn('target.searchParams.set("mode", "locator_only")', reading)
        self.assertIn("/api/enrichment", reading)
        self.assertIn("/api/resolved-abstract", reading)
        self.assertIn("/api/free-web-search", reading)
        self.assertIn("promoteSynthesis(context)", reading)
        self.assertIn("metadataFallback", reading)
        self.assertIn('dataset.evidenceMode = "synthesis"', reading)
        self.assertIn('dataset.evidenceMode = "metadata"', reading)
        self.assertIn('dataset.evidenceMode = "abstract"', reading)

    def test_reader_uses_same_origin_materialised_support_not_direct_github(self) -> None:
        reading = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        self.assertNotIn("https://api.github.com", reading)
        self.assertIn("reviewSupport", reading)
        self.assertIn("Review synopsis", reading)
        self.assertIn("contextCache", reading)
        self.assertIn('"## Reading aid — preparatory"', worker)
        self.assertIn('"## Review guidance — preparatory"', worker)
        self.assertIn("reviewSupport", worker)
        self.assertIn("assistedResolution", worker)

    def test_worker_deduplicates_candidate_issue_reads(self) -> None:
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        self.assertIn("CANDIDATE_ISSUE_CACHE_MS", worker)
        self.assertIn("candidateIssueCache", worker)
        self.assertIn("candidateIssueInFlight", worker)
        self.assertIn("fetchCandidateIssue", worker)
        self.assertIn("fetchWithTimeout", worker)
        self.assertIn("6000", worker)

    def test_verified_locator_has_fast_non_search_mode(self) -> None:
        module = (ROOT / "curator-app/src/free-web-search.js").read_text(encoding="utf-8")
        self.assertIn('mode === "locator_only"', module)
        self.assertIn("readVerifiedAbstractLocator", module)
        self.assertIn("JINA_TIMEOUT_MS = 6500", module)
        self.assertLess(module.index('if (mode === "locator_only")'), module.index("resolveFreeWebCapabilities"))

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
        reading = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        self.assertNotIn("data/curation", module)
        self.assertNotIn("review_queue.csv", module)
        self.assertNotIn("retrieval_coverage.csv", module)
        self.assertNotIn("githubRequest", module)
        self.assertNotIn("localStorage", reading)


if __name__ == "__main__":
    unittest.main()
