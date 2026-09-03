from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ZeroCostProviderPolicyTests(unittest.TestCase):
    def test_scholarly_automatic_registry_contains_no_exa_or_pay_as_you_go_provider(self) -> None:
        providers = (ROOT / "curator-app/src/scholarly-providers.js").read_text(encoding="utf-8")
        self.assertIn("FREE_PROVIDER_REGISTRY", providers)
        self.assertIn('billing: "none"', providers)
        self.assertIn('billing: "free_hard_cap"', providers)
        self.assertNotIn("api.exa.ai", providers)
        self.assertNotIn('provider: "Exa"', providers)

    def test_web_capability_registry_separates_discoverable_from_automatic(self) -> None:
        registry = json.loads(
            (ROOT / "ontology/providers/web-capabilities.json").read_text(encoding="utf-8")
        )
        providers = {row["id"]: row for row in registry["providers"]}
        self.assertTrue(providers["jina_reader"]["automatic_allowed"])
        self.assertTrue(providers["tavily_basic"]["automatic_allowed"])
        for provider_id in ("serper", "exa", "firecrawl", "cloudflare_browser_run"):
            self.assertFalse(providers[provider_id]["automatic_allowed"])
            self.assertTrue(providers[provider_id]["paid_balance_possible"])
        self.assertIn("paid balance", registry["policy"]["paid_balance_policy"].lower())

    def test_tavily_is_basic_single_credit_only(self) -> None:
        providers = (ROOT / "curator-app/src/scholarly-providers.js").read_text(encoding="utf-8")
        self.assertIn('search_depth: "basic"', providers)
        self.assertIn("auto_parameters: false", providers)
        self.assertIn("include_answer: false", providers)
        self.assertIn('if (credits > 1) throw new Error("tavily_credit_guard")', providers)
        self.assertNotIn('search_depth: "advanced"', providers)

    def test_free_web_search_requires_runtime_guards_and_opened_candidate(self) -> None:
        resolver = (ROOT / "curator-app/src/web-capability-resolver.js").read_text(encoding="utf-8")
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        queue = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        reading = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        self.assertIn("JINA_READER_FREE_ONLY", resolver)
        self.assertIn("TAVILY_FREE_ONLY", resolver)
        self.assertIn("automaticEligible", resolver)
        self.assertIn("authenticatedRetrieval(request, env)", worker)
        self.assertIn('url.pathname === "/api/free-web-search"', worker)
        self.assertNotIn("/api/free-web-search", queue)
        self.assertIn("/api/free-web-search", reading)

    def test_registered_paid_capable_providers_have_no_runtime_adapter(self) -> None:
        resolver = (ROOT / "curator-app/src/web-capability-resolver.js").read_text(encoding="utf-8")
        for provider_id in ("serper", "exa", "firecrawl", "cloudflare_browser_run"):
            marker = f'id: "{provider_id}"'
            self.assertIn(marker, resolver)
        self.assertNotIn("api.exa.ai", resolver)
        self.assertNotIn("google.serper.dev", resolver)
        self.assertNotIn("api.firecrawl.dev", resolver)

    def test_openalex_curator_runtime_does_not_use_api_key(self) -> None:
        enrichment = (ROOT / "curator-app/src/enrichment.js").read_text(encoding="utf-8")
        self.assertNotIn("OPENALEX_API_KEY", enrichment)
        self.assertNotIn("api_key", enrichment)

    def test_free_provider_fallbacks_are_present(self) -> None:
        scholarly = (ROOT / "curator-app/src/scholarly-providers.js").read_text(encoding="utf-8")
        web = (ROOT / "curator-app/src/web-capability-resolver.js").read_text(encoding="utf-8")
        for provider in (
            "Semantic Scholar",
            "DataCite",
            "Unpaywall",
            "CORE",
            "Europe PMC",
            "Tavily Basic",
        ):
            self.assertIn(provider, scholarly)
        self.assertIn("Jina Reader", web)


if __name__ == "__main__":
    unittest.main()
