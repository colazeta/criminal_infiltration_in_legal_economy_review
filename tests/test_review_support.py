import csv
import json
import unittest
from pathlib import Path

from scripts.curation.sync_issue_review_support import (
    GUIDANCE_HEADING,
    READING_HEADING,
    guidance_section,
    reading_section,
    replace_section,
)


ROOT = Path(__file__).resolve().parents[1]


class ReviewSupportTests(unittest.TestCase):
    def test_every_unresolved_abstract_has_a_non_decisional_reading_aid(self) -> None:
        with (ROOT / "data/curation/abstract_coverage.csv").open(
            newline="", encoding="utf-8-sig"
        ) as handle:
            unresolved = {
                row["candidate_id"]
                for row in csv.DictReader(handle)
                if row["coverage_status"] == "needs_web_search"
            }
        payload = json.loads(
            (ROOT / "data/curation/reading_aids.json").read_text(encoding="utf-8")
        )
        aids = {record["candidateId"]: record for record in payload["records"]}
        self.assertEqual(unresolved, set(aids))
        self.assertTrue(unresolved)
        for candidate_id, record in aids.items():
            self.assertTrue(record["sourceUrl"].startswith("https://"), candidate_id)
            self.assertTrue(record["synopsis"].strip(), candidate_id)
            self.assertNotIn("abstract", {key.lower() for key in record})
            self.assertLessEqual(len(record["synopsis"]), 1500)

    def test_guidance_is_candidate_specific_but_never_a_decision(self) -> None:
        with (ROOT / "data/curation/review_queue.csv").open(
            newline="", encoding="utf-8-sig"
        ) as handle:
            row = next(
                item
                for item in csv.DictReader(handle)
                if item["candidate_id"] == "CAND-ACADEMIC-2026-09-01-001"
            )
        section = guidance_section(row)
        self.assertIn(GUIDANCE_HEADING, section)
        self.assertIn("Four-part core test", section)
        self.assertIn("eligible_core", section)
        self.assertIn("maybe_full_text_needed", section)
        self.assertIn("broader_aml", section)
        self.assertIn(row["required_human_action"], section)
        self.assertIn("not decisions", section)

    def test_reading_aid_is_explicitly_not_an_author_abstract(self) -> None:
        payload = json.loads(
            (ROOT / "data/curation/reading_aids.json").read_text(encoding="utf-8")
        )
        section = reading_section(payload["records"][0])
        self.assertIn(READING_HEADING, section)
        self.assertIn("non-decisional reading aid", section)
        self.assertIn("must never be represented as the\nauthor's abstract", section)

    def test_section_replacement_is_idempotent_and_preserves_curator_action(self) -> None:
        body = "## Retrieval coverage — mechanical\n\n- Best URL: x\n\n## Curator action\n\nGo"
        replacement = f"{READING_HEADING}\n\n- Aid kind: `publisher_summary`"
        once = replace_section(body, READING_HEADING, replacement)
        twice = replace_section(once, READING_HEADING, replacement)
        self.assertEqual(once, twice)
        self.assertIn("## Retrieval coverage — mechanical", once)
        self.assertIn("## Curator action", once)
        self.assertLess(once.index(READING_HEADING), once.index("## Curator action"))


if __name__ == "__main__":
    unittest.main()
