from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VerifiedAbstractSourceBridgeTests(unittest.TestCase):
    def test_bridge_promotes_only_verified_abstract_sources_without_persisting_text(self) -> None:
        source = (ROOT / "scripts/abstracts/promote_verified_sources.mjs").read_text(encoding="utf-8")
        self.assertIn("verifiedAbstractSourceMap", source)
        self.assertIn('record.kind === "verified_abstract_source"', source)
        self.assertIn('coverage_status: "available"', source)
        self.assertIn('match_type: "verified_abstract_source"', source)
        self.assertIn("abstract text does not persist", source)
        self.assertNotIn("abstract_text:", source)

    def test_bridge_reads_base_and_override_reading_aids(self) -> None:
        source = (ROOT / "scripts/abstracts/promote_verified_sources.mjs").read_text(encoding="utf-8")
        self.assertIn("data/curation/reading_aids.json", source)
        self.assertIn("data/curation/reading_aid_overrides.json", source)
        self.assertIn("merged.set(record.candidateId, record)", source)

    def test_backfill_workflow_runs_bridge_after_bulk_check(self) -> None:
        workflow = (ROOT / ".github/workflows/abstract-coverage.yml").read_text(encoding="utf-8")
        check = workflow.index("node scripts/abstracts/backfill_coverage.mjs --check")
        promote = workflow.index("node scripts/abstracts/promote_verified_sources.mjs")
        self.assertLess(check, promote)
        self.assertIn("data/curation/reading_aids.json", workflow)
        self.assertIn("data/curation/reading_aid_overrides.json", workflow)

    def test_documentation_preserves_retrieval_boundary(self) -> None:
        docs = (ROOT / "docs/operations/verified-abstract-source-bridge.md").read_text(encoding="utf-8")
        self.assertIn("does not persist abstract text", docs)
        self.assertIn("non-decisional", docs)
        self.assertIn("publisher_summary", docs)


if __name__ == "__main__":
    unittest.main()
