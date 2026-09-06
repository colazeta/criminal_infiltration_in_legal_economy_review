from __future__ import annotations

import unittest

from scripts.curation.sync_issue_abstract_resolution import (
    HEADING,
    remove_section,
    resolution_section,
)


class SyncIssueAbstractResolutionTests(unittest.TestCase):
    def test_resolution_section_is_explicitly_non_decisional(self) -> None:
        record = {
            "resolutionClass": "publisher_summary_ready",
            "standaloneAbstractStatus": "not_verified_after_targeted_search",
            "sourceLabel": "Publisher",
            "sourceUrl": "https://example.org/source",
            "checkedAt": "2026-09-06",
            "nextAction": "Screen the exact source.",
            "note": "No standalone abstract verified.",
        }
        section = resolution_section(record)
        self.assertIn(HEADING, section)
        self.assertIn("not_verified_after_targeted_search", section)
        self.assertIn("does **not** assert", section)
        self.assertIn("not a scientific screening decision", section)

    def test_remove_section_preserves_other_curator_sections(self) -> None:
        body = (
            "## Reading aid — preparatory\n\nAid\n\n"
            f"{HEADING}\n\n- Resolution class: `metadata_only`\n\n"
            "## Review guidance — preparatory\n\nGuide\n"
        )
        result = remove_section(body, HEADING)
        self.assertNotIn(HEADING, result)
        self.assertIn("## Reading aid — preparatory", result)
        self.assertIn("## Review guidance — preparatory", result)


if __name__ == "__main__":
    unittest.main()
