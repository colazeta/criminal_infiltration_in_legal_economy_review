from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ZeroCostProviderPolicyTests(unittest.TestCase):
    def test_automatic_registry_contains_no_exa_or_pay_as_you_go_provider(self) -> None:
        providers = (ROOT / "curator-app/src/scholarly-providers.js").read_text(encoding="utf-8")
        self.assertIn('FREE_PROVIDER_REGISTRY', providers)
        self.assertIn('billing: "none"', providers)
        self.assertIn('billing: "free_hard_cap"', providers)
        self.assertNotIn('api.exa.ai', providers)
        self.assertNotIn('provider: "Exa"', providers)

    def test_tavily_is_basic_single_credit_only(self) -> None:
        providers = (ROOT / "curator-app/src/scholarly-providers.js").read_text(encoding="utf-8")
        self.assertIn('search_depth: "basic"', providers)
        self.assertIn('auto_parameters: false', providers)
        self.assertIn('include_answer: false', providers)
        self.assertIn('if (credits > 1) throw new Error("tavily_credit_guard")', providers)
        self.assertNotIn('search_depth: "advanced"', providers)

    def test_free_web_search_requires_runtime_guard_and_opened_candidate(self) -> None:
        handler = (ROOT / "curator-app/src/free-web-search.js").read_text(encoding="utf-8")
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        queue = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        reading = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        self.assertIn('env.TAVILY_FREE_ONLY', handler)
        self.assertIn('authenticatedRetrieval(request, env)', worker)
        self.assertIn('url.pathname === "/api/free-web-search"', worker)
        self.assertNotIn('/api/free-web-search', queue)
        self.assertIn('/api/free-web-search', reading)

    def test_openalex_curator_runtime_does_not_use_api_key(self) -> None:
        enrichment = (ROOT / "curator-app/src/enrichment.js").read_text(encoding="utf-8")
        self.assertNotIn('OPENALEX_API_KEY', enrichment)
        self.assertNotIn('api_key', enrichment)

    def test_free_provider_fallbacks_are_present(self) -> None:
        providers = (ROOT / "curator-app/src/scholarly-providers.js").read_text(encoding="utf-8")
        for provider in (
            "Semantic Scholar",
            "DataCite",
            "Unpaywall",
            "CORE",
            "Europe PMC",
            "Tavily Basic",
        ):
            self.assertIn(provider, providers)


if __name__ == "__main__":
    unittest.main()
