import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/metrics"))
from validate_terminal import validate
from surveillance import MetricsError


class TerminalPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {row["id"]: row for row in json.loads(
            (ROOT / "tests/fixtures/github-ledger-audit-20260927.json").read_text())}

    def test_valid_body_before_write_does_not_claim_persistence(self):
        result = validate(self.rows[5790164542]["body"], "ACADEMIC-2026-09-23",
                          datetime(2026, 9, 23, 6, 29, tzinfo=timezone.utc))
        self.assertTrue(result["schema_valid"])
        self.assertFalse(result["persisted"])
        self.assertTrue(result["remote_validation_required"])

    def test_observed_overlong_notes_and_limitations_are_rejected_before_write(self):
        for cid, batch in [(5739910343, "ACADEMIC-2026-09-19"),
                           (5784336676, "ACADEMIC-2026-09-22-EXTRA-ce155a5f6d3d")]:
            with self.assertRaisesRegex(MetricsError, "invalid text value"):
                validate(self.rows[cid]["body"], batch)

    def test_late_premature_wrong_batch_and_missing_envelopes_are_rejected(self):
        body = self.rows[5790164542]["body"]
        for when in [datetime(2026, 9, 24, tzinfo=timezone.utc),
                     datetime(2026, 9, 23, 6, 27, tzinfo=timezone.utc)]:
            with self.assertRaisesRegex(MetricsError, "unedited daily run"):
                validate(body, "ACADEMIC-2026-09-23", when)
        with self.assertRaisesRegex(MetricsError, "differs"):
            validate(body, "ACADEMIC-2026-09-24")
        with self.assertRaisesRegex(MetricsError, "missing"):
            validate("not a terminal", "ACADEMIC-2026-09-23")
