import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.retrieval.selected_paper_delivery import (
    MANDATORY, PREPARE, audit, index_rows, refresh_mode, run_commands,
)


class SelectedPaperDeliveryTests(unittest.TestCase):
    def test_override_only_push_is_local_but_queue_change_is_not(self):
        before = "a" * 40
        self.assertEqual(refresh_mode("push", before, ["data/curation/reading_aid_overrides.json", "tests/test_aid.py", "site/data/paper-register.json"]), "local")
        for files in (["data/curation/review_queue.csv"], ["scripts/retrieval/resolve_queue.py"], [], [".github/workflows/abstract-coverage.yml"]):
            self.assertEqual(refresh_mode("push", before, files), "full")

    def test_unknown_history_never_suppresses_backfill(self):
        for event, before in (("schedule", "a" * 40), ("push", "0" * 40), ("push", "invalid")):
            self.assertEqual(refresh_mode(event, before, ["data/curation/reading_aid_overrides.json"]), "full")

    def test_preparation_has_no_external_backfill_or_scheduler(self):
        commands = "\n".join(" ".join(command) for command in PREPARE)
        self.assertIn("apply_verified_reading_locators.py", commands)
        self.assertIn("promote_verified_sources.mjs", commands)
        self.assertIn("build_archive.py", commands)
        for forbidden in ("backfill_coverage.mjs", "resolve_queue.py", "paper-enrichment", "git push", "gh pr"):
            self.assertNotIn(forbidden, commands)

    def test_mandatory_validation_preserves_scientific_and_ontology_gates(self):
        commands = [" ".join(command) for command in MANDATORY]
        for command in ("python3 scripts/ontology/validate_ontology.py", "python3 scripts/validation/validate_repository.py", "node --check site/model.js", "node --check site/review-v2.js", "node --check site/curator-guided.js", "node --test curator-app/test/*.test.js"):
            self.assertIn(command, commands)

    def test_duplicate_identity_cannot_disappear_in_dict(self):
        with self.assertRaises(ValueError):
            index_rows([{"id": "x"}, {"id": "x"}], "id", "fixture")

    def fixture(self, root):
        curation = root / "data/curation"
        public = root / "site/data"
        curation.mkdir(parents=True)
        public.mkdir(parents=True)
        for name, rows in {
            "review_queue.csv": [{"candidate_id": "x"}],
            "retrieval_coverage.csv": [{"candidate_id": "x", "resolution_status": "full_text", "source_urls": "https://example.org/paper.pdf"}],
            "abstract_coverage.csv": [{"candidate_id": "x", "coverage_status": "needs_web_search"}],
        }.items():
            with (curation / name).open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        (public / "paper-register.json").write_text(json.dumps({"records": [{"id": "x"}]}))
        (public / "curator-stats.json").write_text(json.dumps({"totalMaterialised": 1}))
        (curation / "reading_aid_overrides.json").write_text(json.dumps({"records": [{"candidateId": "x", "kind": "full_text_intro", "note": "Evidence basis: full_text", "sourceUrl": "https://example.org/paper.pdf"}]}))

    def test_full_text_support_does_not_approve_science_or_abstract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            result = audit(root)
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["materialised_verified_locators"], 1)
            self.assertEqual(result["abstract_status_counts"], {"needs_web_search": 1})
            self.assertFalse(result["scientific_approval_inferred"])
            self.assertFalse(result["private_sources_inspected"])

    def test_stale_publication_and_unmaterialised_locator_fail_check(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            (root / "site/data/paper-register.json").write_text('{"records": []}')
            (root / "site/data/curator-stats.json").write_text('{"totalMaterialised": 0}')
            path = root / "data/curation/retrieval_coverage.csv"
            path.write_text(path.read_text().replace("https://example.org/paper.pdf", "https://example.org/other.pdf"))
            result = audit(root)
            self.assertIn("public_register_identity_drift", result["errors"])
            self.assertIn("curator_stats_count_drift", result["errors"])
            self.assertIn("verified_locator_not_materialised:x", result["errors"])

    def test_first_command_failure_stops_without_discarding_branch_state(self):
        import subprocess
        with patch("scripts.retrieval.selected_paper_delivery.subprocess.run", side_effect=subprocess.CalledProcessError(1, ["first"])) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                run_commands([["first"], ["second"]])
            self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
