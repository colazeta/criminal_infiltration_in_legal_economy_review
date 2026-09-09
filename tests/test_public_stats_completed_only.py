"""Public statistics must never expose incomplete surveillance executions."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/metrics"))

from build_research_stats import active_runs  # noqa: E402
from daily_calendar import CYCLE  # noqa: E402
from extra_runs import project_extra_runs  # noqa: E402
from surveillance import build_public_payload  # noqa: E402
from test_surveillance_metrics import REPOSITORY, exa_run  # noqa: E402


def partial(run: dict) -> dict:
    run = copy.deepcopy(run)
    run["status"] = "partial"
    source = run["sources"][0]
    source.update(
        status="failed",
        queries_completed=max(1, source["queries_planned"] - 1),
        failure_code="connector_unavailable",
        limitations=["Synthetic incomplete run."],
    )
    for field in (
        "occurrences_returned",
        "unique_results",
        "candidate_hits",
        "exclusive_candidates",
    ):
        source[field] = None
    run["totals"] = {field: None for field in run["totals"]}
    run["assessments"] = {field: 0 for field in run["assessments"]}
    run["intake_issue"] = {"created": False, "number": None, "url": None}
    return run


def as_extra(run: dict, suffix: str) -> dict:
    run = copy.deepcopy(run)
    day = run["run_date"]
    run["batch_id"] = f"ACADEMIC-{day}-EXTRA-{suffix}"
    run["window_start"] = f"{day}T18:00:00+02:00"
    run["window_end"] = f"{day}T18:20:00+02:00"
    return run


class CompletedOnlyPublicStatisticsTests(unittest.TestCase):
    def test_incomplete_scheduled_run_is_absent_from_public_projection(self) -> None:
        completed = exa_run("2026-09-09")
        incomplete = partial(exa_run("2026-09-10"))

        projected = active_runs([completed, incomplete])
        self.assertEqual([row["batch_id"] for row in projected], [completed["batch_id"]])

        payload = build_public_payload(projected, 30, REPOSITORY)
        self.assertEqual([row["batchId"] for row in payload["daily"]], [completed["batch_id"]])
        self.assertEqual(payload["summary"]["runDays"], 1)
        self.assertEqual(payload["summary"]["completedRuns"], 1)
        self.assertEqual(payload["summary"]["partialRuns"], 0)
        self.assertEqual(payload["summary"]["failedRuns"], 0)

    def test_incomplete_extra_run_is_absent_from_public_projection(self) -> None:
        completed = as_extra(exa_run("2026-09-09"), "012345abcdef")
        incomplete = as_extra(partial(exa_run("2026-09-09")), "abcdef012345")

        rows = project_extra_runs([completed, incomplete], CYCLE)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["batchId"], completed["batch_id"])
        self.assertEqual(rows[0]["status"], "completed")
        self.assertIsNone(rows[0]["failureCode"])


if __name__ == "__main__":
    unittest.main()
