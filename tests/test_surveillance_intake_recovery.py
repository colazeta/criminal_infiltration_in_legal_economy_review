from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/metrics"))

from fetch_surveillance_ledger import intake_issue_time_is_valid  # noqa: E402


class IntakeTimestampRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.run = {
            "batch_id": "ACADEMIC-2026-09-11-EXTRA-2520dfa54e12",
            "window_start": "2026-09-11T09:58:29+02:00",
            "window_end": "2026-09-11T10:06:20+02:00",
        }

    def test_normal_in_window_intake_remains_valid(self) -> None:
        created = datetime(2026, 9, 11, 8, 6, 19, tzinfo=timezone.utc)
        self.assertTrue(intake_issue_time_is_valid(self.run, created, 317))

    def test_exact_audited_twelve_second_lateness_is_valid(self) -> None:
        created = datetime(2026, 9, 11, 8, 6, 32, tzinfo=timezone.utc)
        self.assertTrue(intake_issue_time_is_valid(self.run, created, 317))

    def test_later_timestamp_is_not_recovered(self) -> None:
        created = datetime(2026, 9, 11, 8, 6, 33, tzinfo=timezone.utc)
        self.assertFalse(intake_issue_time_is_valid(self.run, created, 317))

    def test_wrong_issue_is_not_recovered(self) -> None:
        created = datetime(2026, 9, 11, 8, 6, 32, tzinfo=timezone.utc)
        self.assertFalse(intake_issue_time_is_valid(self.run, created, 318))

    def test_wrong_batch_is_not_recovered(self) -> None:
        run = dict(self.run)
        run["batch_id"] = "ACADEMIC-2026-09-11-EXTRA-000000000000"
        created = datetime(2026, 9, 11, 8, 6, 32, tzinfo=timezone.utc)
        self.assertFalse(intake_issue_time_is_valid(run, created, 317))


if __name__ == "__main__":
    unittest.main()
