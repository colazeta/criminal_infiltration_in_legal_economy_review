from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CuratorFullscreenLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.page = (ROOT / "site/curate.html").read_text(encoding="utf-8")
        self.reading = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        self.queue = (ROOT / "site/curator-queue.js").read_text(encoding="utf-8")

    def test_component_geometry_is_loaded_statically_before_javascript(self) -> None:
        styles = self.page.index('href="./styles.css"')
        reading = self.page.index('href="./curator-reading.css"')
        queue = self.page.index('href="./curator-queue.css"')
        shell = self.page.index('id="curator-fullscreen-shell"')
        scripts = self.page.index('src="./curator-config.js"')
        self.assertLess(styles, reading)
        self.assertLess(reading, queue)
        self.assertLess(queue, shell)
        self.assertLess(shell, scripts)
        self.assertIn('data-curator-reading="true"', self.page)
        self.assertIn('data-curator-queue="true"', self.page)

    def test_dynamic_style_loaders_do_not_duplicate_static_links(self) -> None:
        self.assertIn('link[data-curator-reading="true"]', self.reading)
        self.assertIn('link[data-curator-queue="true"]', self.queue)

    def test_fullscreen_shell_owns_viewport_and_remaining_height(self) -> None:
        match = re.search(
            r'<style id="curator-fullscreen-shell">(?P<css>.*?)</style>',
            self.page,
            flags=re.S,
        )
        self.assertIsNotNone(match)
        css = match.group("css")
        for marker in (
            "CURATOR_FULLSCREEN_SHELL_V1",
            "body.curator-page > main#main-content",
            "position: fixed",
            "inset: 0",
            ".curator-page #editorial-console",
            "flex: 1 1 0%",
            "height: 0",
            "grid-template-columns: minmax(0, 1fr)",
            "minmax(0, 1fr)",
            "overflow: hidden",
            ".candidate-decision-panel",
            "overflow: auto",
        ):
            self.assertIn(marker, css)
        self.assertNotIn("1180px", css)
        self.assertNotIn("max-width: 1180", css)

    def test_page_scroll_is_suppressed_and_internal_panes_own_scrolling(self) -> None:
        match = re.search(
            r'<style id="curator-fullscreen-shell">(?P<css>.*?)</style>',
            self.page,
            flags=re.S,
        )
        css = match.group("css")
        self.assertRegex(css, r'html,\s*body\.curator-page\s*\{[^}]*overflow:\s*hidden')
        self.assertRegex(
            css,
            r'#editorial-console\s*>\s*\.candidate-decision-panel\s*\{[^}]*overflow:\s*auto',
        )
        self.assertIn("#candidate-list", css)
        self.assertIn("overscroll-behavior: contain", css)

    def test_fullscreen_contract_has_small_viewport_overrides(self) -> None:
        match = re.search(
            r'<style id="curator-fullscreen-shell">(?P<css>.*?)</style>',
            self.page,
            flags=re.S,
        )
        css = match.group("css")
        self.assertIn("@media (max-height: 640px)", css)
        self.assertIn("@media (max-width: 820px)", css)


if __name__ == "__main__":
    unittest.main()
