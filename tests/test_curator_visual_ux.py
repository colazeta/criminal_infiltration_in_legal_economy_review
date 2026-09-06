from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CuratorVisualUXTests(unittest.TestCase):
    def test_queue_is_persistent_dense_and_separate_from_reading_surface(self) -> None:
        css = (ROOT / "site/curator-queue.css").read_text(encoding="utf-8")
        self.assertIn("position: sticky", css)
        self.assertIn("height: min(820px, calc(100vh - 24px))", css)
        self.assertIn("grid-template-columns: minmax(390px, 0.92fr) minmax(0, 1.62fr)", css)
        self.assertIn(".queue-card-doi {\n  display: none;", css)
        self.assertIn('.queue-card-chip[data-state="source"] {\n  display: none;', css)
        self.assertIn("max-height: 240px", css)

    def test_authenticated_reader_is_queue_paper_abstract_decision(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        auth = '.curator-page:has(#curator-session-panel:not([hidden]))'
        self.assertIn(f"{auth} .site-header", css)
        self.assertIn(f"{auth} .curator-workspace > :not(.editorial-app)", css)
        self.assertIn("grid-template-columns: 286px minmax(0, 1fr) !important", css)
        self.assertIn("The paper's abstract is the visual centre of the workspace", css)
        self.assertIn("#candidate-abstract-text", css)
        self.assertIn("font-size: 1.04rem", css)
        self.assertIn("line-height: 1.72", css)
        self.assertIn("Decision immediately follows reading", css)

    def test_secondary_diagnostics_do_not_compete_with_abstract(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        self.assertIn("#candidate-reading-aid-panel", css)
        self.assertIn("#candidate-review-guidance-panel", css)
        self.assertIn("#candidate-consensus-panel", css)
        self.assertIn(".candidate-provenance-details", css)
        self.assertIn("display: none !important", css)
        self.assertIn("#candidate-identity-panel", css)
        self.assertIn("#candidate-assisted-resolution-panel", css)

    def test_metadata_collapses_to_doi_and_stage_because_byline_carries_citation(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        self.assertIn("Authors/year/venue are already in the byline", css)
        self.assertIn(".candidate-metadata > div:nth-child(4)", css)
        self.assertIn(".candidate-metadata > div:nth-child(6)", css)
        self.assertIn(".candidate-metadata > div {\n  display: none;", css)

    def test_authenticated_workspace_removes_repeated_intro_chrome(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        selector = '.curator-page:has(#curator-session-panel:not([hidden])) .workspace-heading'
        self.assertIn(selector, css)
        self.assertIn("display: none", css)


if __name__ == "__main__":
    unittest.main()
