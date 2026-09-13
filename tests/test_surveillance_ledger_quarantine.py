from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/metrics"))

import fetch_surveillance_ledger_quarantine as quarantine  # noqa: E402


class SurveillanceLedgerQuarantineTests(unittest.TestCase):
    def test_exact_invalid_terminals_are_filtered(self) -> None:
        rows = [{"id": 1, "body": "ordinary"}]
        for comment_id, batch_id in quarantine.QUARANTINED_LEDGER_COMMENTS.items():
            rows.append(
                {
                    "id": comment_id,
                    "body": f"Daily surveillance batch {batch_id}: completed.",
                }
            )
        with patch.object(quarantine, "_RAW_API_GET", return_value=(rows, None)):
            payload, links = quarantine._quarantine_api_get(
                "https://api.github.com/repos/x/y/issues/30/comments?per_page=100", "token"
            )
        self.assertEqual(payload, [{"id": 1, "body": "ordinary"}])
        self.assertIsNone(links)

    def test_same_comment_id_with_wrong_batch_fails_closed(self) -> None:
        for comment_id in quarantine.QUARANTINED_LEDGER_COMMENTS:
            rows = [{"id": comment_id, "body": "different batch"}]
            with patch.object(quarantine, "_RAW_API_GET", return_value=(rows, None)):
                with self.assertRaises(Exception):
                    quarantine._quarantine_api_get(
                        "https://api.github.com/repos/x/y/issues/30/comments?per_page=100", "token"
                    )

    def test_non_ledger_calls_are_unchanged(self) -> None:
        rows = [{"id": 5644330070, "body": "different batch"}]
        with patch.object(quarantine, "_RAW_API_GET", return_value=(rows, None)):
            payload, _ = quarantine._quarantine_api_get(
                "https://api.github.com/repos/x/y/issues/345", "token"
            )
        self.assertEqual(payload, rows)

    def test_extra_batch_does_not_claim_same_day_ordinary_batch(self) -> None:
        ordinary = "ACADEMIC-2026-09-13"
        extra = "ACADEMIC-2026-09-13-EXTRA-123456789abc"
        malformed_extra = (
            f"Daily surveillance batch {extra}: completed.\n\n"
            "<!-- surveillance-run:v3 -->\n"
            "```json\n"
            f'{{"schema_version":3,"batch_id":"{extra}","sources":[]}}\n'
            "```"
        )
        self.assertFalse(quarantine._comment_claims_batch(malformed_extra, ordinary))
        self.assertTrue(quarantine._comment_claims_batch(malformed_extra, extra))

    def test_exact_target_batch_still_fails_closed_when_malformed(self) -> None:
        target = "ACADEMIC-2026-09-13"
        malformed_target = (
            f"Daily surveillance batch {target}: completed.\n\n"
            "<!-- surveillance-run:v3 -->\n```json\n{}\n```"
        )
        self.assertTrue(quarantine._comment_claims_batch(malformed_target, target))

    def test_exact_json_batch_id_is_fail_closed_fallback(self) -> None:
        target = "ACADEMIC-2026-09-13"
        malformed_summary = (
            "broken surveillance summary\n"
            "<!-- surveillance-run:v3 -->\n"
            f'```json\n{{"batch_id":"{target}"}}\n```'
        )
        self.assertTrue(quarantine._comment_claims_batch(malformed_summary, target))

    def test_exact_late_recovery_terminal_accepts_audited_next_day_creation(self) -> None:
        run = {
            "batch_id": "ACADEMIC-2026-09-11-EXTRA-61e4d03af5c4",
            "run_date": "2026-09-11",
            "window_end": "2026-09-11T13:06:48+02:00",
        }
        comment = {
            "id": 5647832949,
            "created_at": "2026-09-12T18:30:00Z",
            "updated_at": "2026-09-12T18:30:00Z",
        }
        quarantine._verify_ledger_comment_time_with_recovery(run, comment)

    def test_late_recovery_terminal_fails_if_edited(self) -> None:
        run = {
            "batch_id": "ACADEMIC-2026-09-11-EXTRA-61e4d03af5c4",
            "run_date": "2026-09-11",
            "window_end": "2026-09-11T13:06:48+02:00",
        }
        comment = {
            "id": 5647832949,
            "created_at": "2026-09-12T18:30:00Z",
            "updated_at": "2026-09-12T18:31:00Z",
        }
        with self.assertRaises(Exception):
            quarantine._verify_ledger_comment_time_with_recovery(run, comment)

    def test_late_recovery_terminal_fails_for_wrong_batch(self) -> None:
        run = {
            "batch_id": "ACADEMIC-2026-09-11-EXTRA-wrong",
            "run_date": "2026-09-11",
            "window_end": "2026-09-11T13:06:48+02:00",
        }
        comment = {
            "id": 5647832949,
            "created_at": "2026-09-12T18:30:00Z",
            "updated_at": "2026-09-12T18:30:00Z",
        }
        with self.assertRaises(Exception):
            quarantine._verify_ledger_comment_time_with_recovery(run, comment)

    def test_late_recovery_terminal_fails_for_unexpected_creation_day(self) -> None:
        run = {
            "batch_id": "ACADEMIC-2026-09-11-EXTRA-61e4d03af5c4",
            "run_date": "2026-09-11",
            "window_end": "2026-09-11T13:06:48+02:00",
        }
        comment = {
            "id": 5647832949,
            "created_at": "2026-09-13T18:30:00Z",
            "updated_at": "2026-09-13T18:30:00Z",
        }
        with self.assertRaises(Exception):
            quarantine._verify_ledger_comment_time_with_recovery(run, comment)


if __name__ == "__main__":
    unittest.main()
