from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class ClassicSiteUiTests(unittest.TestCase):
    def test_public_pages_load_classic_styles_after_base_styles(self) -> None:
        for filename in ("index.html", "aml.html", "stats.html", "404.html"):
            source = (SITE / filename).read_text(encoding="utf-8")
            with self.subTest(filename=filename):
                self.assertIn('class="classic-site', source)
                self.assertIn('href="./classic-site.css"', source)
                self.assertLess(source.index('href="./styles.css"'), source.index('href="./classic-site.css"'))

    def test_classic_design_system_is_flat_and_full_width(self) -> None:
        source = (SITE / "classic-site.css").read_text(encoding="utf-8")
        self.assertIn("CLASSIC_SITE_V1", source)
        self.assertIn("body.classic-site main", source)
        self.assertIn("width: 100%;", source)
        self.assertIn("max-width: none;", source)
        self.assertIn("--classic-blue: #000080", source)
        self.assertNotIn("linear-gradient", source)
        self.assertNotIn("radial-gradient", source)
        self.assertNotIn("translateY", source)
        self.assertNotIn("border-radius: 999", source)
        self.assertNotIn("box-shadow: var(", source)

    def test_public_archive_records_are_rendered_as_database_rows(self) -> None:
        source = (SITE / "classic-site.css").read_text(encoding="utf-8")
        self.assertIn("Publication records become database rows", source)
        self.assertIn("body.classic-site .paper-list", source)
        self.assertIn("body.classic-site .paper-card", source)
        self.assertIn("border-radius: 0", source)
        self.assertIn("body.classic-site .record-details summary", source)

    def test_method_and_statistics_surfaces_are_flat_reference_panels(self) -> None:
        source = (SITE / "classic-site.css").read_text(encoding="utf-8")
        self.assertIn("body.classic-site .method-grid", source)
        self.assertIn("body.classic-site .pipeline-panel", source)
        self.assertIn("body.classic-site .chart-card", source)
        self.assertIn("body.classic-site .table-scroll", source)
        self.assertIn("border-collapse: collapse", source)

    def test_curator_uses_same_classic_navigation_language_without_global_skin(self) -> None:
        source = (SITE / "curate.html").read_text(encoding="utf-8") + (SITE / "curator-shell.css").read_text()
        self.assertIn('class="curator-menubar"', source)
        self.assertIn('aria-current="page">CURATOR</a>', source)
        self.assertIn("background: #000080", source)
        self.assertNotIn('href="./classic-site.css"', source)
        self.assertIn("CURATOR_FULLSCREEN_SHELL_V1", source)

    def test_404_is_classic_error_window(self) -> None:
        source = (SITE / "404.html").read_text(encoding="utf-8")
        self.assertIn('class="classic-site classic-404"', source)
        self.assertIn('class="error-window"', source)
        self.assertIn('class="error-titlebar"', source)


if __name__ == "__main__":
    unittest.main()
