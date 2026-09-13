import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SelectedPaperDeliveryWorkflowTests(unittest.TestCase):
    def test_both_support_writers_serialize_and_validate_before_persisting(self):
        for name in ("retrieval-resolution.yml", "abstract-coverage.yml"):
            text = (ROOT / ".github/workflows" / name).read_text()
            with self.subTest(workflow=name):
                self.assertIn("group: curator-support-persistence", text)
                self.assertIn("cancel-in-progress: false", text)
                self.assertIn("queue: max", text)
                self.assertNotIn("cancel-in-progress: true", text)
                self.assertIn("fetch-depth: 0", text)
                self.assertIn("actions: write", text)
                self.assertIn("selected_paper_delivery.py --refresh-mode", text)
                self.assertIn("if: steps.refresh.outputs.mode == 'full'", text)
                self.assertLess(text.index("--prepare --validate"), text.index("run: bash scripts/retrieval/persist_selected_support.sh"))
                self.assertNotIn("HEAD:main", text)
                self.assertNotIn("gh pr merge", text)

    def test_persistence_requires_dispatched_quality_expected_head_and_reuses_identical_checkpoint(self):
        text = (ROOT / "scripts/retrieval/persist_selected_support.sh").read_text()
        self.assertIn("persistence_pending", text)
        self.assertIn('echo "::error::', text)
        self.assertIn('pending "quality_not_successful"', text)
        self.assertIn('pending "quality_dispatch_failed"', text)
        self.assertIn('pending "main_moved_reconciliation_required"', text)
        self.assertIn('-f sha="$head_sha"', text)
        self.assertIn('diff_digest="$( { printf', text)
        self.assertIn('branch="automation/selected-support-${diff_digest}"', text)
        self.assertIn('gh pr list --state open --base main --head "$branch"', text)
        self.assertIn('gh workflow run archive.yml --ref "$branch"', text)
        self.assertIn("Reusing retained selected-support checkpoint", text)
        self.assertNotIn('selected-support-${GITHUB_RUN_ID}', text)
        self.assertNotIn("HEAD:main", text)
        self.assertNotIn("--force", text)
        self.assertLess(text.index('pending "quality_not_successful"'), text.index("--method PUT"))
        subprocess.run(["bash", "-n", "scripts/retrieval/persist_selected_support.sh"], cwd=ROOT, check=True)

    def test_owned_pr_preparation_dispatches_final_head_quality(self):
        text = (ROOT / ".github/workflows/retrieval-resolution.yml").read_text()
        self.assertIn('gh workflow run archive.yml --ref "$GITHUB_HEAD_REF"', text)
        self.assertIn("dispatched final-head CI", text)
        self.assertNotIn("final_head_validation_pending", text)

    def test_archive_observes_delivery_after_support_workflows(self):
        text = (ROOT / ".github/workflows/archive.yml").read_text()
        self.assertNotIn("cancel-in-progress: true", text)
        self.assertIn('"Resolve curator paper access"', text)
        self.assertIn('"Backfill curator abstract coverage"', text)
        self.assertEqual(text.count("selected_paper_delivery.py --check"), 2)
        self.assertIn("selected_paper_delivery.py --prepare", text)
        self.assertIn('if [ "$EVENT_NAME" = "pull_request" ]', text)
        self.assertIn('selected-support-pr-audit.json', text)
        self.assertIn("Selected-paper preparation changed unexpected paths", text)
        self.assertLess(
            text.index("selected_paper_delivery.py --prepare"),
            text.index("Selected-paper preparation changed unexpected paths"),
        )
        for path in ("site/curator-guided.js", "site/model.js", "site/review-v2.js"):
            self.assertEqual(text.count("node --check " + path), 2)

    def test_completion_document_preserves_the_canonical_scheduler(self):
        text = (ROOT / "docs/operations/targeted-reading-retrieval.md").read_text()
        self.assertIn("CILE-HOUR40-1", text)
        self.assertIn("up to 100 runs", text)
        self.assertIn("not the canonical at-least-once record", text)
        self.assertIn("A merged PR is not yet a Pages deployment", text)


if __name__ == "__main__":
    unittest.main()
