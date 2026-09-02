from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AbstractCoverageTests(unittest.TestCase):
    def test_backfill_covers_queue_without_persisting_abstract_text(self) -> None:
        script = (ROOT / "scripts/abstracts/backfill_coverage.mjs").read_text(encoding="utf-8")
        self.assertIn('"review_queue.csv"', script)
        self.assertIn('"abstract_coverage.csv"', script)
        self.assertIn('coverage_status', script)
        self.assertIn('abstract_source', script)
        self.assertIn('providers_tried', script)
        self.assertIn('needs_web_search', script)
        self.assertIn('resolveAbstractFromRetrieval', script)
        self.assertIn('enrichCandidate', script)
        self.assertNotIn('"abstract_text",', script)

    def test_bulk_backfill_does_not_use_tavily_or_exa(self) -> None:
        script = (ROOT / "scripts/abstracts/backfill_coverage.mjs").read_text(encoding="utf-8")
        self.assertNotIn('TAVILY_API_KEY', script)
        self.assertNotIn('EXA_API_KEY', script)
        workflow = (ROOT / ".github/workflows/abstract-coverage.yml").read_text(encoding="utf-8")
        self.assertNotIn('TAVILY_API_KEY', workflow)
        self.assertNotIn('EXA_API_KEY', workflow)

    def test_coverage_is_synced_into_candidate_issues(self) -> None:
        sync = (ROOT / "scripts/abstracts/sync_issue_coverage.py").read_text(encoding="utf-8")
        self.assertIn('## Abstract coverage — mechanical', sync)
        self.assertIn('Abstract text persisted: `no`', sync)
        self.assertIn('coverage_status', sync)
        workflow = (ROOT / ".github/workflows/abstract-coverage.yml").read_text(encoding="utf-8")
        self.assertIn('sync_issue_coverage.py', workflow)
        self.assertIn('git status --porcelain -- data/curation/abstract_coverage.csv', workflow)

    def test_workflow_is_triggered_by_inputs_not_its_own_output(self) -> None:
        workflow = (ROOT / ".github/workflows/abstract-coverage.yml").read_text(encoding="utf-8")
        trigger_block = workflow.split('schedule:', 1)[0]
        self.assertIn('review_queue.csv', trigger_block)
        self.assertIn('retrieval_coverage.csv', trigger_block)
        self.assertNotIn('abstract_coverage.csv', trigger_block)


if __name__ == "__main__":
    unittest.main()
