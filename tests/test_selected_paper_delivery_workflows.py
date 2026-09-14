import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SelectedPaperDeliveryWorkflowTests(unittest.TestCase):
    def test_support_writers_serialize_main_persistence_without_blocking_pr_validation(self):
        retrieval = (ROOT / ".github/workflows/retrieval-resolution.yml").read_text()
        abstract = (ROOT / ".github/workflows/abstract-coverage.yml").read_text()
        materialize = (ROOT / ".github/workflows/materialize-curation.yml").read_text()

        # Main/scheduled persistence and all curator-issue mutation share one lane.
        self.assertIn("'curator-support-persistence'", retrieval)
        for name, text in (
            ("abstract-coverage.yml", abstract),
            ("materialize-curation.yml", materialize),
        ):
            with self.subTest(workflow=name):
                self.assertIn("group: curator-support-persistence", text)
                self.assertIn("cancel-in-progress: false", text)
                self.assertIn("queue: max", text)
                self.assertNotIn("cancel-in-progress: true", text)

        # Branch-local PR preparation must not wait behind an independent main backfill.
        self.assertIn("github.event_name == 'pull_request'", retrieval)
        self.assertIn("selected-support-pr-{0}", retrieval)
        self.assertIn("github.event.pull_request.number", retrieval)
        self.assertIn("cancel-in-progress: false", retrieval)
        self.assertIn("queue: max", retrieval)
        self.assertNotIn("cancel-in-progress: true", retrieval)

        for name, text in (
            ("retrieval-resolution.yml", retrieval),
            ("abstract-coverage.yml", abstract),
        ):
            with self.subTest(workflow=name):
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
        self.assertIn("latest_quality_state()", text)
        self.assertIn('[ "$quality_state" = "missing" ] || [ "$quality_state" = "blocked" ]', text)
        self.assertIn("Dispatched replacement exact-head quality validation", text)
        self.assertIn("Reusing retained selected-support checkpoint", text)
        self.assertNotIn('selected-support-${GITHUB_RUN_ID}', text)
        self.assertNotIn("HEAD:main", text)
        self.assertNotIn("--force", text)
        self.assertLess(text.index('pending "quality_not_successful"'), text.index("--method PUT"))
        subprocess.run(["bash", "-n", "scripts/retrieval/persist_selected_support.sh"], cwd=ROOT, check=True)

    def test_reused_checkpoint_is_exactly_the_validated_tree_and_missing_pr_is_recovered(self):
        text = (ROOT / "scripts/retrieval/persist_selected_support.sh").read_text()
        self.assertIn('checkpoint_index="$RUNNER_TEMP/selected-support-index"', text)
        self.assertIn('GIT_INDEX_FILE="$checkpoint_index" git read-tree "$base_sha"', text)
        self.assertIn('GIT_INDEX_FILE="$checkpoint_index" git add -A -- "${paths[@]}"', text)
        self.assertIn('expected_tree="$(GIT_INDEX_FILE="$checkpoint_index" git write-tree)"', text)
        self.assertIn('git fetch --no-tags origin "$branch"', text)
        self.assertIn('merge_base="$(git merge-base "$base_sha" "$head_sha")"', text)
        self.assertIn('[ "$merge_base" = "$base_sha" ] || pending "checkpoint_base_mismatch"', text)
        self.assertIn('remote_tree="$(git rev-parse "$head_sha^{tree}")"', text)
        self.assertIn('[ "$remote_tree" = "$expected_tree" ] || pending "checkpoint_head_mismatch"', text)
        self.assertIn('\n  verify_remote_checkpoint\n  checkpoint="$(gh pr list', text)
        self.assertIn("create_checkpoint_pr()", text)
        self.assertIn("Recovered selected-support PR for retained validated branch", text)
        self.assertIn('select(.headRefOid == "', text)
        self.assertNotIn('pending "checkpoint_branch_without_open_pr"', text)
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
        self.assertIn("Selected-paper projections are not committed on this head", text)
        self.assertIn('prepared="$(git diff --name-only)"', text)
        self.assertLess(
            text.index("selected_paper_delivery.py --prepare"),
            text.index("Selected-paper projections are not committed on this head"),
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
