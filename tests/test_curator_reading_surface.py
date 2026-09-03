from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CuratorReadingSurfaceTests(unittest.TestCase):
    def test_reading_surface_keeps_abstract_ephemeral_authenticated_and_zero_cost(self) -> None:
        javascript = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        self.assertIn('/api/enrichment', javascript)
        self.assertIn('/api/resolved-abstract', javascript)
        self.assertIn('/api/free-web-search', javascript)
        self.assertIn('candidate-abstract-panel', javascript)
        self.assertIn('selected-candidate-article', javascript)
        self.assertIn(
            'OpenAlex · Crossref · Semantic Scholar · DataCite · Unpaywall · CORE · Europe PMC · paper risolto · Jina Reader · Tavily Basic',
            javascript,
        )
        self.assertIn('free_page_reader', javascript)
        self.assertIn('Jina Reader', javascript)
        self.assertIn('needs_web_search', javascript)
        self.assertIn('web_search_exhausted', javascript)
        self.assertIn('providersTried', javascript)
        self.assertIn('sessionStorage.getItem(SESSION_KEY)', javascript)
        self.assertNotIn('.innerHTML', javascript)
        self.assertNotIn('localStorage', javascript)
        self.assertNotIn('abstract_cache', javascript.lower())
        self.assertNotIn('Exa', javascript)

    def test_worker_requires_curator_session_before_all_enrichment_layers(self) -> None:
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        self.assertIn('url.pathname === "/api/enrichment"', worker)
        self.assertIn('url.pathname === "/api/free-web-search"', worker)
        self.assertIn('new URL("/api/session", request.url)', worker)
        self.assertIn('if (!validation.ok) return validation', worker)
        self.assertIn('handleEnrichmentRequest(request, env)', worker)
        self.assertIn('handleFreeWebSearchRequest(request, env)', worker)
        self.assertIn('authenticatedRetrieval(request, env)', worker)
        self.assertIn('"/curator-reading.js"', worker)
        self.assertIn('"/curator-reading.css"', worker)

    def test_public_config_loads_reading_component_without_provider_secrets(self) -> None:
        config = (ROOT / "site/curator-config.js").read_text(encoding="utf-8")
        self.assertIn('apiBaseUrl: ""', config)
        self.assertIn('loadCuratorComponent("./curator-reading.js", "curator-reading")', config)
        self.assertNotIn('OPENALEX_API_KEY', config)
        self.assertNotIn('TAVILY_API_KEY', config)
        self.assertNotIn('CORE_API_KEY', config)
        self.assertNotIn('JINA_API_KEY', config)

    def test_worker_deploy_tracks_zero_cost_provider_policy(self) -> None:
        workflow = (ROOT / ".github/workflows/deploy-curator-worker.yml").read_text(
            encoding="utf-8"
        )
        wrangler = (ROOT / "curator-app/wrangler.example.jsonc").read_text(encoding="utf-8")
        self.assertIn('site/curator-reading.js', workflow)
        self.assertIn('candidate-abstract-panel', workflow)
        self.assertIn('/api/free-web-search', workflow)
        self.assertIn('TAVILY_API_KEY', workflow)
        self.assertIn('CORE_API_KEY', workflow)
        self.assertIn('UNPAYWALL_EMAIL', workflow)
        self.assertNotIn('EXA_API_KEY', workflow)
        self.assertIn('"JINA_READER_FREE_ONLY": "true"', wrangler)
        self.assertIn('"TAVILY_FREE_ONLY": "true"', wrangler)

    def test_archive_ci_syntax_checks_zero_cost_modules(self) -> None:
        workflow = (ROOT / ".github/workflows/archive.yml").read_text(
            encoding="utf-8"
        )
        self.assertGreaterEqual(workflow.count('node --check site/curator-reading.js'), 2)
        self.assertGreaterEqual(workflow.count('node --check curator-app/src/enrichment.js'), 2)
        self.assertGreaterEqual(workflow.count('node --check curator-app/src/scholarly-providers.js'), 2)
        self.assertGreaterEqual(workflow.count('node --check curator-app/src/free-web-search.js'), 2)

    def test_reading_surface_exposes_bibliographic_review_cues(self) -> None:
        javascript = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        self.assertIn('selected-candidate-venue', javascript)
        self.assertIn('candidate-reading-byline', javascript)
        self.assertIn('Apri articolo', javascript)
        self.assertNotIn('Abstract assente', javascript)

    def test_abstract_never_enters_static_public_payloads(self) -> None:
        for relative in (
            "site/data/archive.json",
            "site/data/secondary-collections.json",
            "site/data/curator-stats.json",
            "site/data/curator-options.json",
        ):
            content = (ROOT / relative).read_text(encoding="utf-8").lower()
            self.assertNotIn('"abstract"', content, relative)


if __name__ == "__main__":
    unittest.main()
