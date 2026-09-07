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
            'class="candidate-grid-header"',
            'id="candidate-list"',
            'id="candidate-detail"',
            'id="decision-form"',
        ):
            self.assertIn(required, html)

    def test_queue_is_a_full_width_master_table_not_a_sidebar(self) -> None:
        css = (ROOT / "site/curator-queue.css").read_text(encoding="utf-8")
        self.assertIn("Classic master table: queue above, selected record below", css)
        self.assertIn("grid-template-columns: minmax(0, 1fr)", css)
        self.assertIn("grid-template-rows: clamp(220px, 29vh, 285px) minmax(0, 1fr)", css)
        self.assertNotIn("grid-template-columns: 280px minmax(0, 1fr)", css)
        self.assertNotIn("position: sticky", css)
        self.assertIn(".candidate-grid-header", css)
        self.assertIn("display: contents", css)
        self.assertIn("white-space: nowrap", css)
        self.assertIn("background: #000080", css)

    def test_master_table_has_fixed_columns_for_scannability(self) -> None:
        css = (ROOT / "site/curator-queue.css").read_text(encoding="utf-8")
        for selector in (
            ".queue-card-title",
            ".queue-card-authors",
            ".queue-card-citation",
            ".queue-stage-badge",
        ):
            self.assertIn(selector, css)
        self.assertIn("86px", css)
        self.assertIn("minmax(260px, 2.4fr)", css)
        self.assertIn("text-overflow: ellipsis", css)

    def test_shell_is_viewport_bound_like_a_desktop_application(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        self.assertIn("Full-viewport master table above a scrollable record form", css)
        self.assertIn("height: 100dvh", css)
        self.assertIn("overflow: hidden", css)
        self.assertIn("display: flex", css)
        self.assertIn("flex-direction: column", css)
        self.assertIn("background: var(--classic-blue)", css)
        self.assertNotIn("linear-gradient", css)
        self.assertNotIn("border-radius: 999", css)

    def test_paper_record_is_literal_tabular_structure(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns: 1.25fr .35fr 1fr 1fr .7fr .75fr", css)
        self.assertIn("border-right: 1px solid var(--classic-grid)", css)
        self.assertIn('font-family: "Courier New", Courier, monospace', css)
        self.assertIn("Literal six-cell bibliographic row", css)

    def test_abstract_or_synthesis_is_bounded_not_a_blank_half_screen(self) -> None:
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        self.assertIn("never large enough to waste the viewport", css)
        self.assertIn("#candidate-abstract-text", css)
        self.assertIn("min-height: 86px", css)
        self.assertIn("max-height: 28vh", css)
        self.assertIn("overflow: auto", css)
        self.assertIn("white-space: pre-wrap", css)

    def test_native_confirmation_checkbox_is_not_stretched_by_global_form_css(self) -> None:
        html = (ROOT / "site/curate.html").read_text(encoding="utf-8")
        css = (ROOT / "site/curator-reading.css").read_text(encoding="utf-8")
        self.assertIn('class="classic-confirmation"', html)
        self.assertIn('.classic-confirmation input[type="checkbox"]', css)
        self.assertIn("width: 13px !important", css)
        self.assertIn("height: 13px !important", css)
        self.assertIn("appearance: auto", css)

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
        self.assertIn("Guided choices still drive the governed native select", css)
        self.assertIn(".guided-decision-choice", css)
        self.assertIn("grid-template-columns: repeat(4, minmax(0, 1fr))", css)
        self.assertIn(".guided-decision-copy", css)
        self.assertIn(".decision-progress", css)
        self.assertIn('background: var(--classic-blue) !important', css)


if __name__ == "__main__":
    unittest.main()
