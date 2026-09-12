from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_surveillance_metrics import candidate_issue, exa_run
from scripts.curation.import_intake_issue import (
    IntakeImportError,
    issue_form_value,
    parse_intake_issue,
)
from scripts.curation.stage_intake import stage_candidates
from scripts.intake_open_access import validate_snapshots

ROOT = Path(__file__).resolve().parents[1]


def extra(day="2026-09-09", suffix="012345abcdef"):
    run = exa_run(day)
    run.update(
        batch_id=f"ACADEMIC-{day}-EXTRA-{suffix}",
        window_start=f"{day}T18:00:00+02:00",
        window_end=f"{day}T18:20:00+02:00",
    )
    return run


def issue_for(run):
    issue = candidate_issue(run)
    issue["created_at"] = f"{run['run_date']}T16:10:00Z"
    return issue


def replace_candidates(issue: dict, mutate) -> dict:
    issue = copy.deepcopy(issue)
    manifest = parse_intake_issue(issue["body"], issue["title"])
    mutate(manifest["candidates"])
    old = issue_form_value(issue["body"], "Candidate records")
    replacement = "```json\n" + json.dumps(manifest, ensure_ascii=False, indent=2) + "\n```"
    issue["body"] = issue["body"].replace(old, replacement, 1)
    return issue


def empty_root(folder: str) -> Path:
    root = Path(folder)
    queue = root / "data/curation/review_queue.csv"
    queue.parent.mkdir(parents=True)
    queue.write_text(
        (ROOT / "data/curation/review_queue.csv").read_text().splitlines()[0] + "\n",
        encoding="utf-8",
    )
    return root


class IntakeRediscoveryTests(unittest.TestCase):
    def test_exact_rediscovery_does_not_poison_later_batch(self) -> None:
        first = issue_for(extra())
        second = issue_for(extra(suffix="abcdef012345"))
        with tempfile.TemporaryDirectory() as folder:
            root = empty_root(folder)
            one = stage_candidates(root, first["body"], first["title"], "201", "2026-09-09")
            two = stage_candidates(root, second["body"], second["title"], "202", "2026-09-09")
            self.assertEqual(len(one["added"]), 3)
            self.assertEqual(two["added"], [])
            self.assertEqual(len(two["skipped_existing"]), 3)
            self.assertEqual(validate_snapshots(root), 3)
            snapshots = sorted((root / "data/curation/intake_access").glob("*.json"))
            self.assertEqual(len(snapshots), 1)

    def test_mixed_batch_materialises_novel_candidate_and_reconciles_rediscovery(self) -> None:
        first = issue_for(extra())
        second_run = extra(suffix="abcdef012345")
        second = issue_for(second_run)

        def add_novel(candidates):
            novel = copy.deepcopy(candidates[0])
            novel["candidate_id"] = f"CAND-{second_run['batch_id']}-004"
            novel["title"] = "A genuinely novel recovery candidate"
            novel["year"] = 2024
            novel["identifiers"] = {"doi": None, "other": ["RECOVERY-NOVEL-001"]}
            novel["open_access"]["candidate_id"] = novel["candidate_id"]
            candidates.append(novel)

        second = replace_candidates(second, add_novel)
        with tempfile.TemporaryDirectory() as folder:
            root = empty_root(folder)
            stage_candidates(root, first["body"], first["title"], "201", "2026-09-09")
            result = stage_candidates(root, second["body"], second["title"], "202", "2026-09-09")
            self.assertEqual(result["added"], [f"CAND-{second_run['batch_id']}-004"])
            self.assertEqual(len(result["skipped_existing"]), 3)
            self.assertEqual(validate_snapshots(root), 4)
            snapshot = json.loads(
                (root / "data/curation/intake_access" / f"{second_run['batch_id']}.json").read_text()
            )
            self.assertEqual(
                [receipt["candidate_id"] for receipt in snapshot["receipts"]],
                [f"CAND-{second_run['batch_id']}-004"],
            )

    def test_exact_identifier_with_incompatible_title_fails_closed(self) -> None:
        first = issue_for(extra())
        second = issue_for(extra(suffix="abcdef012345"))

        def set_first_doi(candidates):
            candidates[0]["identifiers"]["doi"] = "10.1234/recovery-test"

        def conflicting(candidates):
            candidates[0]["identifiers"]["doi"] = "10.1234/recovery-test"
            candidates[0]["title"] = "A conflicting title for the same DOI"

        first = replace_candidates(first, set_first_doi)
        second = replace_candidates(second, conflicting)
        with tempfile.TemporaryDirectory() as folder:
            root = empty_root(folder)
            stage_candidates(root, first["body"], first["title"], "201", "2026-09-09")
            before = (root / "data/curation/review_queue.csv").read_bytes()
            with self.assertRaisesRegex(IntakeImportError, "incompatible title"):
                stage_candidates(root, second["body"], second["title"], "202", "2026-09-09")
            self.assertEqual((root / "data/curation/review_queue.csv").read_bytes(), before)
            self.assertFalse(
                (root / "data/curation/intake_access" / f"{extra(suffix='abcdef012345')['batch_id']}.json").exists()
            )


class RecoveryWorkflowTests(unittest.TestCase):
    def test_normal_intake_is_serial_target_validated_and_rediscovery_safe(self) -> None:
        workflow = (ROOT / ".github/workflows/intake-to-curation.yml").read_text(encoding="utf-8")
        fetcher = (ROOT / "scripts/curation/fetch_intake_run.py").read_text(encoding="utf-8")
        self.assertIn("group: intake-to-curation-main", workflow)
        self.assertIn("scripts/curation/stage_intake.py", workflow)
        self.assertIn("Close rediscovery-only intake", workflow)
        self.assertIn("gh issue close", workflow)
        self.assertIn("fetch_validated_run_for_intake", fetcher)
        self.assertNotIn("fetch_validated_runs(", fetcher)

    def test_backlog_recovery_uses_same_global_lock_and_one_sequential_reconciler(self) -> None:
        workflow = (ROOT / ".github/workflows/recover-intake-backlog.yml").read_text(encoding="utf-8")
        script = (ROOT / "scripts/curation/recover_intake_backlog.py").read_text(encoding="utf-8")
        self.assertIn("group: intake-to-curation-main", workflow)
        self.assertIn("'[MAINTENANCE][INTAKE-RECOVERY]'", workflow)
        self.assertIn("scripts/curation/recover_intake_backlog.py", workflow)
        self.assertIn("sorted(paginated_issues", script)
        self.assertIn("stage_candidates(", script)
        self.assertIn("fetch_validated_run_for_intake", script)
        self.assertIn("PERMANENTLY_QUARANTINED_BATCHES", script)

    def test_quarantine_wrapper_treats_cross_run_identity_as_occurrence_only(self) -> None:
        import sys
        sys.path.insert(0, str(ROOT / "scripts/metrics"))
        import fetch_surveillance_ledger_quarantine as quarantine

        original = quarantine._base.candidate_keys

        def fake_fetch(*_args, **_kwargs):
            self.assertEqual(quarantine._base.candidate_keys({"title": "x"}), set())
            return []

        with patch.object(quarantine._base, "fetch_validated_runs", side_effect=fake_fetch):
            self.assertEqual(quarantine.fetch_validated_runs("x/y", 30, ["x"], "token"), [])
        self.assertIs(quarantine._base.candidate_keys, original)


if __name__ == "__main__":
    unittest.main()
