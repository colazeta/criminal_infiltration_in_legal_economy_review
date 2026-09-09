from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class PlainMethodLayoutTests(unittest.TestCase):
    def test_method_is_linear_document_not_card_layout(self) -> None:
        html = (SITE / "method.html").read_text(encoding="utf-8")
        self.assertIn('class="classic-site classic-method"', html)
        self.assertIn('href="./method.css"', html)
        self.assertGreaterEqual(html.count("<hr"), 7)
        self.assertGreaterEqual(html.count("<ol>"), 3)
        self.assertGreaterEqual(html.count("<ul>"), 3)
        for token in (
            'class="method-grid"',
            'class="intro"',
            'class="scope-note"',
            'class="section-heading"',
            'class="pipeline-panel"',
        ):
            self.assertNotIn(token, html)

    def test_method_specific_css_stays_plain(self) -> None:
        css = (SITE / "method.css").read_text(encoding="utf-8")
        self.assertIn("PLAIN_90S_METHOD_V1", css)
        for token in ("display: grid", "box-shadow", "linear-gradient", "radial-gradient"):
            self.assertNotIn(token, css)
        self.assertNotIn("border-radius", css.replace("border-radius: 0", ""))


if __name__ == "__main__":
    unittest.main()
