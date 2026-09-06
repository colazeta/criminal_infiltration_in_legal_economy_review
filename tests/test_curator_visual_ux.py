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

    def test_reading_surface_prioritises_identity_abstract_and_guidance(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr)", css)
        self.assertIn("#candidate-abstract-panel {\n  grid-column: 1 / -1;", css)
        self.assertIn("#candidate-reading-aid-panel {\n  grid-column: 1;", css)
        self.assertIn("#candidate-review-guidance-panel {\n  grid-column: 2;", css)
        self.assertIn("font-family: ui-monospace", css)
        self.assertIn("scroll-margin-top: 42vh", css)
        self.assertIn("scroll-margin-top: 62vh", css)

    def test_authenticated_workspace_removes_repeated_intro_chrome(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        selector = '.curator-page:has(#curator-session-panel:not([hidden])) .workspace-heading'
        self.assertIn(selector, css)
        self.assertIn("display: none", css)


if __name__ == "__main__":
    unittest.main()
