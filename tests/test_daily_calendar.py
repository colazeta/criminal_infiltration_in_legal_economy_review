import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/metrics"))
sys.path.insert(0, str(ROOT / "tests"))
from daily_calendar import calendar_projection, validate_calendar
from test_surveillance_metrics import completed_run
from surveillance import build_public_payload, validate_public_payload, MetricsError


class DailyCalendarTests(unittest.TestCase):
    def test_all_days_exist_and_unknown_execution_is_never_zero(self):
        runs = [completed_run(day) for day in ["2026-08-31", "2026-09-01", "2026-09-07"]]
        payload = build_public_payload(runs, 30, "colazeta/criminal_infiltration_in_legal_economy_review")
        calendar = calendar_projection(runs, "2026-09-07T20:00:00Z")
        validate_calendar(calendar, payload["daily"])
        self.assertEqual(len(calendar["rows"]), 8)
        self.assertEqual(calendar["missingDays"], 5)
        self.assertEqual(calendar["expectedDays"], 8)
        self.assertEqual(calendar["completionRate"], 3 / 8)
        self.assertEqual(calendar["sourceCompletionRate30"], 6 / 16)
        missing = calendar["rows"][2]
        self.assertEqual(missing["status"], "missing")
        self.assertIsNone(missing["queriesCompleted"])
        self.assertIsNone(missing["attemptCount"])
        payload.update(schemaVersion=2, calendar=calendar)
        validate_public_payload(payload)
        broken = copy.deepcopy(payload); broken["calendar"]["rows"].pop(2)
        with self.assertRaises(MetricsError): validate_public_payload(broken)

    def test_today_is_planned_before_deadline_and_missing_after(self):
        early = calendar_projection([], "2026-09-08T04:30:00Z")
        late = calendar_projection([], "2026-09-08T06:00:00Z")
        self.assertEqual(early["rows"][-1]["status"], "planned")
        self.assertEqual(late["rows"][-1]["status"], "missing")

    def test_failure_details_do_not_leak_through_public_codes(self):
        run = completed_run()
        run["sources"][0]["failure_code"] = "private candidate title in provider error"
        result = calendar_projection([run], "2026-09-01T12:00:00Z")
        self.assertNotIn("private candidate", json.dumps(result))
        self.assertIn("other_provider_failure", result["rows"][0]["failureCodes"])
