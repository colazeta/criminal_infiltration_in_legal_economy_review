from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from test_surveillance_metrics import candidate_issue, exa_run
from scripts.curation.recover_intake_backlog import reconcile_represented_issue
from scripts.curation.stage_intake import IntakeImportError, stage_candidates


ROOT = Path(__file__).resolve().parents[1]


def extra(day: str = "2026-09-09", suffix: str = "012345abcdef") -> dict:
    run = exa_run(day)
    run.update(
        batch_id=f"ACADEMIC-{day}-EXTRA-{suffix}",
        window_start=f"{day}T18:00:00+02:00",
        window_end=f"{day}T18:20:00+02:00",
    )
    return run


def issue_for(run: dict) -> dict:
    issue = candidate_issue(run)
    issue["created_at"] = f"{run['run_date']}T16:10:00Z"
    return issue


def empty_root(folder: str) -> Path:
    root = Path(folder)
    queue = root / "data/curation/review_queue.csv"
    queue.parent.mkdir(parents=True)
    queue.write_text(
        (ROOT / "data/curation/review_queue.csv").read_text().splitlines()[0] + "\n",
        encoding="utf-8",
    )
    cycle = root / "config/archive-cycle.json"
    cycle.parent.mkdir(parents=True)
    cycle.write_text((ROOT / "config/archive-cycle.json").read_text(), encoding="utf-8")
    registry = root / "data/registry"
    registry.mkdir(parents=True)
    for name in ("papers.csv", "work_identifiers.csv"):
        (registry / name).write_text((ROOT / "data/registry" / name).read_text(), encoding="utf-8")
    return root


class RepresentedIntakeReconciliationTests(unittest.TestCase):
    def test_fully_materialised_batch_is_reconciled_candidate_by_candidate(self) -> None:
        run = extra()
        issue = issue_for(run)
        with tempfile.TemporaryDirectory() as folder:
            root = empty_root(folder)
            staged = stage_candidates(
                root,
                issue["body"],
                issue["title"],
                str(issue["number"]),
                "2026-09-09",
                issue_created_at=issue["created_at"],
                run=run,
            )
            result = reconcile_represented_issue(root, issue, run, "2026-09-09")
            self.assertEqual(result["added"], [])
            self.assertTrue(result["reconciliation_only"])
            self.assertEqual(result["source_candidate_count"], len(staged["added"]))
            self.assertEqual(
                {row["candidate_id"] for row in result["skipped_existing"]},
                set(staged["added"]),
            )

    def test_partially_materialised_batch_fails_instead_of_being_silently_ignored(self) -> None:
        run = extra(suffix="abcdef012345")
        issue = issue_for(run)
        with tempfile.TemporaryDirectory() as folder:
            root = empty_root(folder)
            staged = stage_candidates(
                root,
                issue["body"],
                issue["title"],
                str(issue["number"]),
                "2026-09-09",
                issue_created_at=issue["created_at"],
                run=run,
            )
            queue_path = root / "data/curation/review_queue.csv"
            with queue_path.open(newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                fields = list(reader.fieldnames or [])
                rows = list(reader)
            missing_id = staged["added"][-1]
            rows = [row for row in rows if row["candidate_id"] != missing_id]
            with queue_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)

            with self.assertRaisesRegex(
                IntakeImportError,
                "represented batch still has unreconciled candidate",
            ):
                reconcile_represented_issue(root, issue, run, "2026-09-09")

    def test_exact_candidate_id_with_incompatible_title_fails_closed(self) -> None:
        run = extra(suffix="fedcba654321")
        issue = issue_for(run)
        with tempfile.TemporaryDirectory() as folder:
            root = empty_root(folder)
            staged = stage_candidates(
                root,
                issue["body"],
                issue["title"],
                str(issue["number"]),
                "2026-09-09",
                issue_created_at=issue["created_at"],
                run=run,
            )
            queue_path = root / "data/curation/review_queue.csv"
            with queue_path.open(newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                fields = list(reader.fieldnames or [])
                rows = list(reader)
            rows[0]["title"] = "A conflicting title under the same candidate ID"
            with queue_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)

            with self.assertRaisesRegex(IntakeImportError, "incompatible title"):
                reconcile_represented_issue(root, issue, run, "2026-09-09")
            self.assertTrue(staged["added"])


if __name__ == "__main__":
    unittest.main()
