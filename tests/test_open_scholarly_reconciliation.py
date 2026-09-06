from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OpenScholarlyReconciliationTests(unittest.TestCase):
    def test_new_zero_cost_providers_are_authorised(self) -> None:
        sources = (ROOT / "docs/governance/sources.md").read_text(encoding="utf-8")
        for domain in [
            "api.opencitations.net",
            "export.arxiv.org",
            "zenodo.org",
            "api.archives-ouvertes.fr",
            "doaj.org",
        ]:
            self.assertIn(domain, sources)

    def test_runtime_has_field_reconciliation_and_two_provider_citation_frontier(self) -> None:
        reconciliation = (ROOT / "curator-app/src/metadata-reconciliation.js").read_text(encoding="utf-8")
        citations = (ROOT / "curator-app/src/citation-chasing.js").read_text(encoding="utf-8")
        enrichment = (ROOT / "curator-app/src/enrichment.js").read_text(encoding="utf-8")
        self.assertIn("reconcileMetadata", reconciliation)
        self.assertIn("manifestation_ambiguity", reconciliation)
        self.assertIn("OpenCitations", citations)
        self.assertIn("Semantic Scholar", citations)
        self.assertIn("metadataResolution", enrichment)
        self.assertIn("metadataObservations", enrichment)
        self.assertIn("citationFrontier", enrichment)

    def test_provider_registry_has_no_required_credentials_or_paid_fallback(self) -> None:
        providers = (ROOT / "curator-app/src/open-scholarly-providers.js").read_text(encoding="utf-8")
        self.assertIn('billing: "none"', providers)
        self.assertNotIn('billing: "pay', providers)
        self.assertNotIn("API_KEY", providers)

    def test_cli_is_non_mutating_and_doi_bound(self) -> None:
        cli = (ROOT / "scripts/expansion/citation_frontier.mjs").read_text(encoding="utf-8")
        self.assertIn("--doi", cli)
        self.assertIn("Mechanical E2/E3 retrieval only", cli)
        self.assertNotIn("data/registry", cli)
        self.assertNotIn("review_queue.csv", cli)

    def test_curator_package_checks_new_modules(self) -> None:
        package = json.loads((ROOT / "curator-app/package.json").read_text(encoding="utf-8"))
        check = package["scripts"]["check"]
        for module in [
            "src/open-scholarly-providers.js",
            "src/metadata-reconciliation.js",
            "src/citation-chasing.js",
        ]:
            self.assertIn(module, check)


if __name__ == "__main__":
    unittest.main()
