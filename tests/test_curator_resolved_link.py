from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CuratorResolvedLinkTests(unittest.TestCase):
    def test_curator_prefers_persisted_best_url(self) -> None:
        javascript = (ROOT / "site/curator-resolved-link.js").read_text(encoding="utf-8")
        self.assertIn('/api/retrieval', javascript)
        self.assertIn('dataset.resolvedUrl', javascript)
        self.assertIn('Apri full text', javascript)
        self.assertIn('Apri copia OA', javascript)
        self.assertIn('sessionStorage.getItem(SESSION_KEY)', javascript)
        self.assertIn('bestUrl', javascript)
        self.assertNotIn('.innerHTML', javascript)
        self.assertNotIn('localStorage', javascript)

    def test_worker_retrieval_endpoint_is_authenticated_and_candidate_bound(self) -> None:
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        self.assertIn('url.pathname === "/api/retrieval"', worker)
        self.assertIn('requireCuratorSession(request, env)', worker)
        self.assertIn('<!-- curator-candidate:${candidateId} -->', worker)
        self.assertIn('## Retrieval coverage — mechanical', worker)
        self.assertIn('bestUrl: safeHttpsUrl', worker)
        self.assertIn('"/curator-resolved-link.js"', worker)
        self.assertIn('load(\"./curator-resolved-link.js\"', worker)

    def test_public_config_loads_component_without_exposing_api_origin(self) -> None:
        config = (ROOT / "site/curator-config.js").read_text(encoding="utf-8")
        self.assertIn('apiBaseUrl: ""', config)
        self.assertIn('loadCuratorComponent("./curator-resolved-link.js", "curator-resolved-link")', config)

    def test_ci_and_deployment_cover_resolved_link_surface(self) -> None:
        archive = (ROOT / ".github/workflows/archive.yml").read_text(encoding="utf-8")
        deploy = (ROOT / ".github/workflows/deploy-curator-worker.yml").read_text(encoding="utf-8")
        resolver = (ROOT / ".github/workflows/retrieval-resolution.yml").read_text(encoding="utf-8")
        self.assertGreaterEqual(archive.count('node --check site/curator-resolved-link.js'), 2)
        self.assertIn('site/curator-resolved-link.js', deploy)
        self.assertIn('curator-resolved-link.js', deploy)
        self.assertIn('/api/retrieval', deploy)
        self.assertIn('node --check site/curator-resolved-link.js', resolver)

    def test_retrieval_writeback_prefers_pr_but_does_not_force_main(self) -> None:
        workflow = (ROOT / ".github/workflows/retrieval-resolution.yml").read_text(encoding="utf-8")
        self.assertIn('gh pr create', workflow)
        self.assertIn('git push origin HEAD:main', workflow)
        self.assertIn('current_main', workflow)
        self.assertIn('base_sha', workflow)
        self.assertNotIn('--force', workflow)
        self.assertIn('Validated fallback branch retained', workflow)


if __name__ == "__main__":
    unittest.main()
