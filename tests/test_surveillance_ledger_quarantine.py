from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/metrics"))

import fetch_surveillance_ledger_quarantine as quarantine  # noqa: E402


class SurveillanceLedgerQuarantineTests(unittest.TestCase):
    def test_exact_invalid_terminal_is_filtered(self) -> None:
        rows = [
            {"id": 1, "body": "ordinary"},
            {
                "id": 5631393628,
                "body": "Daily surveillance batch ACADEMIC-2026-09-11-EXTRA-2520dfa54e12: completed.",
            },
        ]
        with patch.object(quarantine, "_RAW_API_GET", return_value=(rows, None)):
            payload, links = quarantine._quarantine_api_get(
                "https://api.github.com/repos/x/y/issues/30/comments?per_page=100", "token"
            )
        self.assertEqual(payload, [{"id": 1, "body": "ordinary"}])
        self.assertIsNone(links)

    def test_same_comment_id_with_wrong_batch_fails_closed(self) -> None:
        rows = [{"id": 5631393628, "body": "different batch"}]
        with patch.object(quarantine, "_RAW_API_GET", return_value=(rows, None)):
            with self.assertRaises(Exception):
                quarantine._quarantine_api_get(
                    "https://api.github.com/repos/x/y/issues/30/comments?per_page=100", "token"
                )

    def test_non_ledger_calls_are_unchanged(self) -> None:
        rows = [{"id": 5631393628, "body": "different batch"}]
        with patch.object(quarantine, "_RAW_API_GET", return_value=(rows, None)):
            payload, _ = quarantine._quarantine_api_get(
                "https://api.github.com/repos/x/y/issues/317", "token"
            )
        self.assertEqual(payload, rows)


if __name__ == "__main__":
    unittest.main()
