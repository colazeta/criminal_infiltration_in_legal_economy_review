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

    def test_surface_consumes_same_origin_candidate_context_without_fetch_wrapper(self) -> None:
        source = (ROOT / "site/curator-assisted-resolution.js").read_text(encoding="utf-8")
        self.assertIn('document.addEventListener("curator:candidate-context"', source)
        self.assertIn("event?.detail?.context?.assistedResolution", source)
        self.assertNotIn("window.fetch =", source)
        self.assertNotIn("originalFetch", source)
        self.assertNotIn("api.github.com", source)
        self.assertNotIn("issueCache", source)

    def test_primary_synthesis_is_owned_by_reading_surface(self) -> None:
        assisted = (ROOT / "site/curator-assisted-resolution.js").read_text(encoding="utf-8")
        reading = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        self.assertNotIn("promoteAidToMainSurface", assisted)
        self.assertNotIn("candidate-abstract-text", assisted)
        self.assertIn("promoteSynthesis", reading)
        self.assertIn('panel.dataset.evidenceMode = "synthesis"', reading)
        self.assertIn('panel.dataset.evidenceMode = "abstract"', reading)
        self.assertIn("Sintesi da fonti verificate", reading)
        self.assertIn("Sintesi dai metadati verificati", reading)

    def test_actual_abstract_has_priority_over_synthesis(self) -> None:
        reading = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        self.assertIn("function renderAbstract(payload)", reading)
        self.assertIn('panel.dataset.evidenceMode = "abstract"', reading)
        self.assertIn('title.textContent = "Abstract"', reading)
        self.assertIn("abstractCache", reading)

    def test_component_still_loads_before_reading_surface_but_no_longer_intercepts_it(self) -> None:
        public = (ROOT / "site/curator-config.js").read_text(encoding="utf-8")
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        self.assertLess(public.index("curator-assisted-resolution.js"), public.index("curator-reading.js"))
        self.assertLess(
            worker.index('load(\\"./curator-assisted-resolution.js'),
            worker.index('load(\\"./curator-reading.js'),
        )
        self.assertIn('"/curator-assisted-resolution.js"', worker)

    def test_deploy_smoke_checks_component(self) -> None:
        workflow = (ROOT / ".github/workflows/deploy-curator-worker.yml").read_text(encoding="utf-8")
        self.assertIn('"site/curator-assisted-resolution.js"', workflow)
        self.assertIn('"curator-assisted-resolution.js"', workflow)
        self.assertIn("Curator assisted abstract-resolution surface", workflow)


if __name__ == "__main__":
    unittest.main()
