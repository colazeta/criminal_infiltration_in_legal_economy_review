from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WebCapabilityOntologyTests(unittest.TestCase):
    def test_web_module_extends_current_cile_profile(self) -> None:
        base = json.loads((ROOT / "ontology/cile-review-profile.yaml").read_text(encoding="utf-8"))
        module = json.loads((ROOT / "ontology/modules/web-retrieval.json").read_text(encoding="utf-8"))
        self.assertEqual(module["extends_profile"], base["version"])
        for class_name in (
            "WebRetrievalProvider",
            "ProviderCapability",
            "ProviderQuota",
            "ProviderProjectBudget",
            "WebSearchInvocation",
            "PageRetrievalInvocation",
            "BrowserInvocation",
            "AgenticResearchInvocation",
        ):
            self.assertIn(class_name, module["classes"])

    def test_provider_registry_is_governed_and_zero_spend_by_default(self) -> None:
        registry = json.loads((ROOT / "ontology/providers/web-capabilities.json").read_text(encoding="utf-8"))
        base = json.loads((ROOT / "ontology/cile-review-profile.yaml").read_text(encoding="utf-8"))
        self.assertEqual(registry["extends_ontology_profile"], base["version"])
        providers = {row["id"]: row for row in registry["providers"]}
        self.assertEqual(set(providers), {
            "jina_reader",
            "serper",
            "exa",
            "tavily_basic",
            "firecrawl",
            "cloudflare_browser_run",
        })
        for provider_id in ("jina_reader", "serper", "exa", "tavily_basic"):
            self.assertTrue(providers[provider_id]["implemented"])
            self.assertTrue(providers[provider_id]["automatic_allowed"])
            self.assertIn("FREE_ONLY", providers[provider_id]["runtime_guard"])
        for provider_id in ("serper", "exa"):
            self.assertTrue(providers[provider_id]["paid_balance_possible"])
            self.assertIn("project_lifetime_request_cap", providers[provider_id])
            self.assertIn("dedicated_account_guard", providers[provider_id])
        for provider_id in ("firecrawl", "cloudflare_browser_run"):
            self.assertFalse(providers[provider_id]["automatic_allowed"])

    def test_runtime_registry_matches_governed_provider_ids_and_layers(self) -> None:
        registry = json.loads((ROOT / "ontology/providers/web-capabilities.json").read_text(encoding="utf-8"))
        source = (ROOT / "curator-app/src/web-capability-resolver.js").read_text(encoding="utf-8")
        for provider in registry["providers"]:
            self.assertIn(f'id: "{provider["id"]}"', source)
            self.assertIn(f'layer: {provider["layer"]}', source)

    def test_credit_providers_have_persistent_budget_semantics(self) -> None:
        module = json.loads((ROOT / "ontology/modules/web-retrieval.json").read_text(encoding="utf-8"))
        self.assertIn("projectBudgetUsed", module["properties"])
        self.assertIn("projectBudgetLimit", module["properties"])
        self.assertIn("dedicatedFreeAccountGuard", module["properties"])
        self.assertTrue(any("persistent project budget" in rule for rule in module["invariants"]))

    def test_queue_cannot_consume_web_capabilities(self) -> None:
        queue = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")
        self.assertNotIn("/api/free-web-search", queue)
        self.assertNotIn("web-capability-resolver", queue)


if __name__ == "__main__":
    unittest.main()
