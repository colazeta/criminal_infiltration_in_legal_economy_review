from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class BibliometricArchiveUiTests(unittest.TestCase):
    def test_bibliometrics_default_to_reviewed_corpus_with_explicit_pending_toggle(self) -> None:
        source = (SITE / "stats.html").read_text(encoding="utf-8")
        self.assertIn('id="include-pending-toggle" type="checkbox"', source)
        self.assertNotIn('id="include-pending-toggle" type="checkbox" checked', source)
        self.assertIn('id="bibliometric-content"', source)
        self.assertIn('id="journal-evolution"', source)
        self.assertIn('id="author-evolution"', source)
        self.assertIn('src="./bibliometrics.js?v=001"', source)

    def test_pending_bibliometrics_do_not_include_terminal_review_states(self) -> None:
        source = (SITE / "bibliometrics.js").read_text(encoding="utf-8")
        self.assertIn('new Set(["pending", "needs_full_text"])', source)
        self.assertIn('state.includePending ? state.archive.concat(pending()) : state.archive', source)
        self.assertIn('record.year === null || record.year === undefined || record.year === ""', source)
        self.assertIn('year > 0 ? year : null', source)

    def test_archive_register_exposes_structured_filters(self) -> None:
        source = (SITE / "index.html").read_text(encoding="utf-8")
        for element_id in (
            "register-year-filter",
            "register-author-filter",
            "register-venue-filter",
            "register-review-filter",
            "register-access-filter",
            "register-sort-order",
            "author-filter",
            "venue-filter",
        ):
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', source)

    def test_bibliometric_skin_remains_flat(self) -> None:
        source = (SITE / "bibliometrics.css").read_text(encoding="utf-8")
        self.assertNotIn("linear-gradient", source)
        self.assertNotIn("radial-gradient", source)
        self.assertNotIn("border-radius", source)
        self.assertNotIn("box-shadow", source)
        self.assertIn("bibliometric-matrix", source)


if __name__ == "__main__":
    unittest.main()
