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

    def test_credit_web_providers_require_persistent_project_caps(self) -> None:
        registry = json.loads(
            (ROOT / "ontology/providers/web-capabilities.json").read_text(encoding="utf-8")
        )
        providers = {row["id"]: row for row in registry["providers"]}
        for provider_id in ("jina_reader", "serper", "exa", "tavily_basic"):
            self.assertTrue(providers[provider_id]["automatic_allowed"])
        self.assertEqual(providers["serper"]["project_lifetime_request_cap"], 1000)
        self.assertLess(providers["serper"]["project_lifetime_request_cap"], 2500)
        self.assertEqual(providers["exa"]["project_lifetime_request_cap"], 500)
        self.assertLess(providers["exa"]["max_theoretical_project_cost_usd_at_verified_price"], 20)
        self.assertIn("DEDICATED", providers["serper"]["dedicated_account_guard"])
        self.assertIn("DEDICATED", providers["exa"]["dedicated_account_guard"])
        for provider_id in ("firecrawl", "cloudflare_browser_run"):
            self.assertFalse(providers[provider_id]["automatic_allowed"])

    def test_tavily_is_basic_single_credit_only(self) -> None:
        providers = (ROOT / "curator-app/src/scholarly-providers.js").read_text(encoding="utf-8")
        self.assertIn('search_depth: "basic"', providers)
        self.assertIn("auto_parameters: false", providers)
        self.assertIn("include_answer: false", providers)
        self.assertIn('if (credits > 1) throw new Error("tavily_credit_guard")', providers)
        self.assertNotIn('search_depth: "advanced"', providers)

    def test_serper_and_exa_are_bounded_discovery_only(self) -> None:
        resolver = (ROOT / "curator-app/src/web-capability-resolver.js").read_text(encoding="utf-8")
        self.assertIn('SERPER_SEARCH_API = "https://google.serper.dev/search"', resolver)
        self.assertIn('EXA_SEARCH_API = "https://api.exa.ai/search"', resolver)
        self.assertIn('SERPER_DEDICATED_FREE_ACCOUNT', resolver)
        self.assertIn('EXA_DEDICATED_STARTER_ACCOUNT', resolver)
        self.assertIn('type: "fast"', resolver)
        self.assertIn('category: "research paper"', resolver)
        self.assertIn('numResults: 5', resolver)
        self.assertNotIn('type: "deep"', resolver)
        self.assertNotIn('type: "deep-lite"', resolver)
        self.assertNotIn('x402', resolver.lower())
        self.assertIn("reserveProjectProviderBudget", resolver)
        self.assertIn("provider-discovered manifestation", resolver)

    def test_provider_budget_is_persisted_before_external_credit_calls(self) -> None:
        budget = (ROOT / "curator-app/src/provider-budget.js").read_text(encoding="utf-8")
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        self.assertIn('maxRequests: 1000', budget)
        self.assertIn('maxRequests: 500', budget)
        self.assertIn('web-provider-budget-v1', budget)
        self.assertIn('/provider-budget', worker)
        self.assertIn('providerBudgetUsage', worker)
        self.assertIn('provider_project_budget_exhausted', worker)
        self.assertIn('this.ctx.storage.put("providerBudgetUsage"', worker)

    def test_provider_readiness_is_authenticated_and_read_only(self) -> None:
        readiness = (ROOT / "curator-app/src/provider-readiness.js").read_text(encoding="utf-8")
        budget = (ROOT / "curator-app/src/provider-budget.js").read_text(encoding="utf-8")
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        onboarding = (ROOT / "docs/operations/web-provider-onboarding.md").read_text(encoding="utf-8")
        self.assertIn('url.pathname === "/api/web-provider-status"', worker)
        self.assertIn('requireCuratorSession(request, env)', worker)
        self.assertIn('/provider-budget-status', worker)
        self.assertIn('/provider-budget-status', budget)
        self.assertNotIn('reserveProjectProviderBudget', readiness)
        self.assertIn('blockingReasons', readiness)
        self.assertIn('remaining', readiness)
        self.assertIn('GET /api/web-provider-status', onboarding)

    def test_free_web_search_requires_runtime_guards_and_opened_candidate(self) -> None:
        resolver = (ROOT / "curator-app/src/web-capability-resolver.js").read_text(encoding="utf-8")
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        queue = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        reading = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        for guard in (
            "JINA_READER_FREE_ONLY",
            "SERPER_FREE_ONLY",
            "EXA_FREE_ONLY",
            "TAVILY_FREE_ONLY",
        ):
            self.assertIn(guard, resolver)
        self.assertIn("authenticatedRetrieval(request, env)", worker)
        self.assertIn('url.pathname === "/api/free-web-search"', worker)
        self.assertNotIn("/api/free-web-search", queue)
        self.assertIn("/api/free-web-search", reading)

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
        for provider in ("Jina Reader", "Serper", "Exa Search"):
            self.assertIn(provider, web)


if __name__ == "__main__":
    unittest.main()
