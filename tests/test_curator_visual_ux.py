from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CuratorVisualUXTests(unittest.TestCase):
    def test_page_contains_only_operational_curator_shell(self) -> None:
        html = (ROOT / "site/curate.html").read_text(encoding="utf-8")
        for removed in (
            'class="site-header"',
            'class="workspace-heading"',
            'class="run-health"',
            'class="curator-toolbar"',
            'class="queue-overview"',
            'class="queue-lanes"',
            'class="decision-workspace"',
            'class="curator-boundary"',
            "<footer",
        ):
            self.assertNotIn(removed, html)
        for required in (
            'class="curator-titlebar"',
            'id="editorial-console"',
            'id="candidate-list"',
            'id="candidate-detail"',
            'id="decision-form"',
        ):
            self.assertIn(required, html)

    def test_queue_is_a_narrow_flat_record_list(self) -> None:
        css = (ROOT / "site/curator-queue.css").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns: 280px minmax(0, 1fr)", css)
        self.assertIn("position: sticky", css)
        self.assertIn("border-radius: 0", css)
        self.assertIn("box-shadow: none", css)
        self.assertIn("border-bottom: 1px solid #aaa", css)
        self.assertIn("background: #000080", css)
        self.assertIn(".queue-card-chips {\n  display: none;", css)

    def test_shell_is_one_classic_database_window(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        self.assertIn("One window, one queue, one record, one decision form", css)
        self.assertIn(".curator-titlebar", css)
        self.assertIn("background: var(--classic-blue)", css)
        self.assertIn("border-radius: 0", css)
        self.assertIn("box-shadow: none", css)
        self.assertNotIn("linear-gradient", css)
        self.assertNotIn("border-radius: 999", css)

    def test_paper_record_is_literal_tabular_structure(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns: 1.25fr 0.35fr 1fr 1fr 0.7fr 0.75fr", css)
        self.assertIn("border-right: 1px solid var(--classic-grid)", css)
        self.assertIn('font-family: "Courier New", Courier, monospace', css)
        self.assertIn("Literal six-cell bibliographic row", css)

    def test_abstract_or_synthesis_is_the_single_large_reading_cell(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        self.assertIn("abstract when available, otherwise governed synthesis", css)
        self.assertIn("#candidate-abstract-text", css)
        self.assertIn("min-height: 120px", css)
        self.assertIn("font: 13px/1.5 Arial, Helvetica, sans-serif", css)
        self.assertIn("white-space: pre-wrap", css)

    def test_secondary_diagnostics_are_not_visible(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        for selector in (
            "#candidate-reading-aid-panel",
            "#candidate-review-guidance-panel",
            "#candidate-consensus-panel",
            "#candidate-assisted-resolution-panel",
            ".candidate-provenance-details",
            ".candidate-retrieval-status",
        ):
            self.assertIn(selector, css)
        self.assertIn("display: none !important", css)
        self.assertIn('data-identity-blocked="false"', css)

    def test_guided_decision_keeps_function_but_drops_explanatory_chrome(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        self.assertIn("Guided decisions still drive the governed native select", css)
        self.assertIn(".guided-decision-choice", css)
        self.assertIn("grid-template-columns: repeat(4, minmax(0, 1fr))", css)
        self.assertIn(".guided-decision-copy", css)
        self.assertIn(".decision-progress", css)
        self.assertIn('background: var(--classic-blue) !important', css)


if __name__ == "__main__":
    unittest.main()
