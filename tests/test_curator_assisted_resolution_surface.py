from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CuratorAssistedResolutionSurfaceTests(unittest.TestCase):
    def test_surface_exposes_all_controlled_resolution_states(self) -> None:
        source = (ROOT / "site/curator-assisted-resolution.js").read_text(encoding="utf-8")
        self.assertIn("candidate-assisted-resolution-panel", source)
        self.assertIn("full_text_or_intro_ready", source)
        self.assertIn("publisher_summary_ready", source)
        self.assertIn("metadata_only", source)
        self.assertIn("known_noise", source)
        self.assertIn("not_verified_after_targeted_search", source)
        self.assertIn("not_applicable_noise", source)
        self.assertNotIn("innerHTML", source)

    def test_surface_reuses_existing_issue_fetch_instead_of_duplicate_request(self) -> None:
        source = (ROOT / "site/curator-assisted-resolution.js").read_text(encoding="utf-8")
        self.assertIn("const originalFetch = window.fetch.bind(window)", source)
        self.assertIn("window.fetch = async function curatorAssistedResolutionFetch", source)
        self.assertIn("response.clone().json()", source)
        self.assertIn("issueCache", source)
        self.assertNotIn("await fetch(`https://api.github.com", source)

    def test_missing_abstract_promotes_governed_synopsis_into_primary_reading_cell(self) -> None:
        source = (ROOT / "site/curator-assisted-resolution.js").read_text(encoding="utf-8")
        self.assertIn("Reading aid — preparatory", source)
        self.assertIn('aid["Review synopsis"]', source)
        self.assertIn("candidate-abstract-text", source)
        self.assertIn("candidate-abstract-source", source)
        self.assertIn("Sintesi per lo screening", source)
        self.assertIn("Sintesi generata da fonti verificate", source)
        self.assertIn("Sintesi dai metadati verificati", source)
        self.assertIn("non abstract dell’autore", source)
        self.assertIn('panel.dataset.evidenceMode = "synthesis"', source)
        self.assertIn('panel.dataset.evidenceMode = "abstract"', source)

    def test_actual_abstract_has_priority_over_generated_synthesis(self) -> None:
        source = (ROOT / "site/curator-assisted-resolution.js").read_text(encoding="utf-8")
        self.assertIn("function actualAbstractVisible()", source)
        self.assertIn("if (actualAbstractVisible())", source)
        self.assertIn('title.textContent = "Abstract"', source)
        self.assertIn("abstract recuperato", source)
        self.assertIn("abstract mostrato solo nella console autenticata", source)

    def test_interceptor_loads_before_reading_surface_in_public_and_secure_configs(self) -> None:
        public = (ROOT / "site/curator-config.js").read_text(encoding="utf-8")
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        self.assertLess(public.index("curator-assisted-resolution.js"), public.index("curator-reading.js"))
        self.assertLess(
            worker.index('load(\\"./curator-assisted-resolution.js'),
            worker.index('load(\\"./curator-reading.js'),
        )
        self.assertIn('"/curator-assisted-resolution.js"', worker)

    def test_deploy_smoke_checks_new_component(self) -> None:
        workflow = (ROOT / ".github/workflows/deploy-curator-worker.yml").read_text(encoding="utf-8")
        self.assertIn('"site/curator-assisted-resolution.js"', workflow)
        self.assertIn('"curator-assisted-resolution.js"', workflow)
        self.assertIn("Curator assisted abstract-resolution surface", workflow)


if __name__ == "__main__":
    unittest.main()
