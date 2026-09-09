"""Regression tests for the governed surveillance schema transition."""
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/metrics"))

from daily_calendar import CYCLE, calendar_projection


class DailyCalendarSchemaTransitionTests(unittest.TestCase):
    def _run(self, schema_version):
        return {
            "schema_version": schema_version,
            "run_date": "2026-09-09",
            "expected_sources": ["Exa"],
            "status": "completed",
            "window_start": "2026-09-09T07:00:00+02:00",
            "window_end": "2026-09-09T07:10:00+02:00",
            "sources": [
                {
                    "status": "completed",
                    "failure_code": None,
                    "queries_planned": 7,
                    "queries_completed": 7,
                }
            ],
        }

    def test_current_calendar_accepts_v2_and_v3_runs(self):
        start = date.fromisoformat(CYCLE["daily_start_date"])
        for schema_version in (2, 3):
            with self.subTest(schema_version=schema_version):
                calendar = calendar_projection(
                    [self._run(schema_version)],
                    "2026-09-09T12:00:00Z",
                    start,
                    CYCLE["review_id"],
                )
                self.assertEqual(calendar["completedDays"], 1)
                self.assertEqual(calendar["lastLedgerDate"], "2026-09-09")

    def test_current_calendar_rejects_legacy_schema(self):
        start = date.fromisoformat(CYCLE["daily_start_date"])
        with self.assertRaisesRegex(ValueError, "source policy"):
            calendar_projection(
                [self._run(1)],
                "2026-09-09T12:00:00Z",
                start,
                CYCLE["review_id"],
            )


if __name__ == "__main__":
    unittest.main()
