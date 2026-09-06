from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IntakePersistenceTests(unittest.TestCase):
    def test_validated_intake_prefers_pr_and_automerge(self) -> None:
        workflow = (ROOT / ".github/workflows/intake-to-curation.yml").read_text(encoding="utf-8")
        self.assertIn('gh pr create --base main --head "$BRANCH"', workflow)
        self.assertIn('gh pr merge "$pr_url" --squash --delete-branch', workflow)
        self.assertIn("Validated intake merged automatically", workflow)

    def test_direct_persistence_is_guarded_by_exact_validated_base(self) -> None:
        workflow = (ROOT / ".github/workflows/intake-to-curation.yml").read_text(encoding="utf-8")
        self.assertIn('base_sha="$(git rev-parse HEAD)"', workflow)
        self.assertIn('git fetch origin main', workflow)
        self.assertIn('current_main="$(git rev-parse origin/main)"', workflow)
        self.assertIn('if [ "$current_main" = "$BASE_SHA" ]; then', workflow)
        self.assertIn('git push origin HEAD:main', workflow)
        self.assertNotIn('git push --force', workflow)
        self.assertNotIn('git push -f', workflow)

    def test_concurrent_main_change_fails_loudly_and_retains_audit_branch(self) -> None:
        workflow = (ROOT / ".github/workflows/intake-to-curation.yml").read_text(encoding="utf-8")
        self.assertIn("Validated intake could not be persisted automatically", workflow)
        self.assertIn("Validated branch retained", workflow)
        self.assertIn("Expected main SHA", workflow)
        self.assertIn("Current main SHA", workflow)
        self.assertIn("exit 1", workflow)


if __name__ == "__main__":
    unittest.main()
