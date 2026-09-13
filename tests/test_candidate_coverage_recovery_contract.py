from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CandidateCoverageRecoveryContractTests(unittest.TestCase):
    def test_recovery_scaffolds_before_reporting_success(self) -> None:
        source = (ROOT / "scripts/curation/recover_intake_backlog.py").read_text(
            encoding="utf-8"
        )
        scaffold = source.index("scaffold_all(root, args.date)")
        output = source.index("args.output.write_text")
        self.assertLess(scaffold, output)
        self.assertIn("_stage_coverage_for_preservation(root)", source)

    def test_actions_stages_all_three_coverage_projections(self) -> None:
        source = (ROOT / "scripts/curation/recover_intake_backlog.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('os.environ.get("GITHUB_ACTIONS") != "true"', source)
        self.assertIn("COVERAGE_PATHS", source)
        self.assertIn('"git", "-C", str(root), "add"', source)

    def test_scaffolding_is_network_free(self) -> None:
        source = (ROOT / "scripts/curation/scaffold_candidate_coverage.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("urlopen", "requests", "httpx", "subprocess", "GH_TOKEN"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
