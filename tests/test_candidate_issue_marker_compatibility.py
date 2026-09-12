from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ID = "CAND-ACADEMIC-2026-09-09-EXTRA-85e203d4eb5a-002"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CandidateIssueMarkerCompatibilityTests(unittest.TestCase):
    def test_all_issue_sync_inventories_accept_lowercase_batch_hex(self) -> None:
        modules = [
            load_module(
                "sync_issue_review_support_marker_test",
                ROOT / "scripts" / "curation" / "sync_issue_review_support.py",
            ),
            load_module(
                "sync_issue_access_marker_test",
                ROOT / "scripts" / "access" / "sync_issue_access.py",
            ),
            load_module(
                "sync_issue_coverage_marker_test",
                ROOT / "scripts" / "abstracts" / "sync_issue_coverage.py",
            ),
        ]
        for module in modules:
            with self.subTest(module=module.__name__):
                original = module.paginated
                try:
                    module.paginated = lambda repository, token, path: [
                        {
                            "number": 464,
                            "body": f"<!-- curator-candidate:{CANDIDATE_ID} -->\n",
                        }
                    ]
                    inventory = module.issue_inventory("owner/repo", "token")
                finally:
                    module.paginated = original
                self.assertEqual(inventory[CANDIDATE_ID]["number"], 464)


if __name__ == "__main__":
    unittest.main()
