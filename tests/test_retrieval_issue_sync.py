from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "retrieval" / "sync_issue_retrieval.py"
SPEC = importlib.util.spec_from_file_location("sync_issue_retrieval", MODULE_PATH)
assert SPEC and SPEC.loader
syncer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(syncer)


class RetrievalIssueSyncTests(unittest.TestCase):
    def test_section_exposes_best_and_alternative_urls_without_editorial_claim(self) -> None:
        row = {
            "resolution_status": "full_text",
            "best_url": "https://example.org/paper.pdf",
            "best_url_kind": "full_text",
            "full_text_url": "https://example.org/paper.pdf",
            "open_access_url": "https://repository.example/item/1",
            "landing_url": "https://publisher.example/article/1",
            "doi_url": "https://doi.org/10.1234/test",
            "resolution_sources": "OpenAlex; Crossref",
            "match_method": "OpenAlex:doi; Crossref:doi",
            "match_confidence": "high",
            "checked_at": "2026-09-02",
        }
        section = syncer.section(row)
        self.assertIn("Retrieval coverage — mechanical", section)
        self.assertIn("https://example.org/paper.pdf", section)
        self.assertIn("https://repository.example/item/1", section)
        self.assertIn("https://publisher.example/article/1", section)
        self.assertIn("does not establish eligibility", section)

    def test_retrieval_section_is_inserted_before_curator_action_and_is_idempotent(self) -> None:
        body = """<!-- curator-candidate:CAND-X -->

## Candidate record

metadata

## Curator action

action
"""
        replacement = syncer.SECTION_HEADING + "\n\n- Best URL: <https://example.org>"
        first = syncer.replace_section(body, replacement)
        second = syncer.replace_section(first, replacement)
        self.assertEqual(first, second)
        self.assertLess(first.index(syncer.SECTION_HEADING), first.index("## Curator action"))

    def test_issue_inventory_accepts_lowercase_batch_hex_in_candidate_id(self) -> None:
        candidate_id = "CAND-ACADEMIC-2026-09-09-EXTRA-85e203d4eb5a-002"
        original = syncer.paginated
        try:
            syncer.paginated = lambda repository, token, path: [
                {
                    "number": 464,
                    "body": f"<!-- curator-candidate:{candidate_id} -->\n",
                }
            ]
            inventory = syncer.issue_inventory("owner/repo", "token")
        finally:
            syncer.paginated = original
        self.assertEqual(inventory[candidate_id]["number"], 464)

    def test_issue_inventory_tolerates_same_issue_repeated_across_pages(self) -> None:
        candidate_id = "CAND-ACADEMIC-2026-09-13-EXTRA-a6766e6649ed-006"
        issue = {
            "id": 5439991102,
            "number": 563,
            "body": f"<!-- curator-candidate:{candidate_id} -->\n",
        }
        original = syncer.paginated
        seen_path = []
        try:
            def repeated(repository, token, path):
                seen_path.append(path)
                return [dict(issue), dict(issue)]

            syncer.paginated = repeated
            inventory = syncer.issue_inventory("owner/repo", "token")
        finally:
            syncer.paginated = original
        self.assertEqual(inventory[candidate_id]["number"], 563)
        self.assertEqual(
            seen_path,
            ["/issues?state=all&sort=created&direction=asc"],
        )

    def test_issue_inventory_rejects_distinct_issues_for_same_candidate(self) -> None:
        candidate_id = "CAND-ACADEMIC-2026-09-13-EXTRA-a6766e6649ed-006"
        original = syncer.paginated
        try:
            syncer.paginated = lambda repository, token, path: [
                {
                    "id": 1,
                    "number": 563,
                    "body": f"<!-- curator-candidate:{candidate_id} -->\n",
                },
                {
                    "id": 2,
                    "number": 999,
                    "body": f"<!-- curator-candidate:{candidate_id} -->\n",
                },
            ]
            with self.assertRaises(syncer.SyncError):
                syncer.issue_inventory("owner/repo", "token")
        finally:
            syncer.paginated = original


if __name__ == "__main__":
    unittest.main()
