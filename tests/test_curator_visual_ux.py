from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CuratorVisualUXTests(unittest.TestCase):
    def test_queue_is_a_flat_classic_row_list(self) -> None:
        css = (ROOT / "site/curator-queue.css").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns: 320px minmax(0, 1fr)", css)
        self.assertIn("position: sticky", css)
        self.assertIn("border-radius: 0", css)
        self.assertIn("box-shadow: none", css)
        self.assertIn("border-bottom: 1px solid #aaa", css)
        self.assertIn('background: #000080', css)
        self.assertIn(".queue-card-chips {\n  display: none;", css)

    def test_paper_record_is_literal_tabular_structure(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        auth = '.curator-page:has(#curator-session-panel:not([hidden]))'
        self.assertIn(f"{auth} .site-header", css)
        self.assertIn("closer to a 1990s database form", css)
        self.assertIn("grid-template-columns: 1.25fr 0.35fr 1fr 1fr 0.7fr 0.75fr", css)
        self.assertIn("border-right: 1px solid var(--curator-classic-grid)", css)
        self.assertIn("font-family: \"Courier New\", Courier, monospace", css)
        self.assertIn("border-radius: 0 !important", css)
        self.assertIn("box-shadow: none !important", css)

    def test_textual_abstract_is_the_main_record_cell(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        self.assertIn("The actual textual abstract is the main cell", css)
        self.assertIn("#candidate-abstract-text", css)
        self.assertIn("min-height: 130px", css)
        self.assertIn("font: 14px/1.55 Arial, Helvetica, sans-serif", css)
        self.assertIn("white-space: pre-wrap", css)

    def test_secondary_diagnostics_are_removed_from_normal_reading_path(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        for selector in (
            "#candidate-reading-aid-panel",
            "#candidate-review-guidance-panel",
            "#candidate-consensus-panel",
            ".candidate-provenance-details",
        ):
            self.assertIn(selector, css)
        self.assertIn("display: none !important", css)
        self.assertIn("data-identity-blocked=\"false\"", css)
        self.assertIn("#candidate-assisted-resolution-panel", css)

    def test_guided_decision_function_is_flattened_not_removed(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        self.assertIn("Guided decision controls are flattened, not removed", css)
        self.assertIn(".guided-decision-composer", css)
        self.assertIn(".guided-decision-choice", css)
        self.assertIn("grid-template-columns: repeat(4, minmax(0, 1fr))", css)
        self.assertIn('background: var(--curator-classic-blue) !important', css)

    def test_authenticated_workspace_removes_repeated_intro_chrome(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        selector = '.curator-page:has(#curator-session-panel:not([hidden])) .site-header'
        self.assertIn(selector, css)
        self.assertIn("display: none !important", css)


if __name__ == "__main__":
    unittest.main()
