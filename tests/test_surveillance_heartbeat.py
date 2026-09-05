from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.metrics.monitor_surveillance_heartbeat import (
    INCIDENT_MARKER,
    SURVEILLANCE_MARKER,
    batch_id_for,
    comment_has_batch,
    incident_body,
    rome_today,
)


ROOT = Path(__file__).resolve().parents[1]


class SurveillanceHeartbeatTests(unittest.TestCase):
    def test_batch_id_is_date_stable(self) -> None:
        self.assertEqual(batch_id_for(rome_today(datetime(2026, 9, 5, 10, tzinfo=timezone.utc))), "ACADEMIC-2026-09-05")

    def test_comment_requires_governed_marker_and_exact_batch(self) -> None:
        body = f'''Daily surveillance batch ACADEMIC-2026-09-05: completed.\n\n{SURVEILLANCE_MARKER}\n```json\n{{"batch_id":"ACADEMIC-2026-09-05"}}\n```'''
        self.assertTrue(comment_has_batch(body, "ACADEMIC-2026-09-05"))
        self.assertFalse(comment_has_batch(body, "ACADEMIC-2026-09-04"))
        self.assertFalse(comment_has_batch('{"batch_id":"ACADEMIC-2026-09-05"}', "ACADEMIC-2026-09-05"))

    def test_incident_explicitly_refuses_scientific_interpretation(self) -> None:
        body = incident_body("ACADEMIC-2026-09-05", datetime(2026, 9, 5, 12, tzinfo=timezone.utc))
        self.assertIn(INCIDENT_MARKER, body)
        self.assertIn("not** a zero-result", body)
        self.assertIn("not** a failed source", body)
        self.assertIn("not** evidence for scientific saturation", body)
        self.assertIn("Do not invent or backfill", body)

    def test_workflow_is_issue_only_and_scheduled_after_external_task(self) -> None:
        workflow = (ROOT / ".github/workflows/surveillance-heartbeat.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "15 12 * * *"', workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("issues: write", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertIn("monitor_surveillance_heartbeat.py", workflow)


if __name__ == "__main__":
    unittest.main()
