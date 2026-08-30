from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/metrics"))

from fetch_surveillance_ledger import MARKER, extract_run  # noqa: E402
from surveillance import (  # noqa: E402
    MetricsError,
    build_public_payload,
    validate_public_payload,
    validate_run,
)


REPOSITORY = "colazeta/criminal_infiltration_in_legal_economy_review"


def completed_run(day: str = "2026-08-31") -> dict:
    return {
        "schema_version": 1,
        "batch_id": f"ACADEMIC-{day}",
        "run_date": day,
        "window_start": f"{day}T00:00:00+02:00",
        "window_end": f"{day}T07:20:00+02:00",
        "timezone": "Europe/Rome",
        "status": "completed",
        "repository_commit": "a" * 40,
        "expected_sources": ["Consensus", "Exa"],
        "sources": [
            {
                "source": "Consensus",
                "status": "completed",
                "queries_planned": 7,
                "queries_completed": 7,
                "occurrences_returned": 12,
                "unique_results": 8,
                "candidate_hits": 2,
                "exclusive_candidates": 1,
                "failure_code": None,
                "limitations": [],
            },
            {
                "source": "Exa",
                "status": "completed",
                "queries_planned": 4,
                "queries_completed": 4,
                "occurrences_returned": 10,
                "unique_results": 7,
                "candidate_hits": 2,
                "exclusive_candidates": 1,
                "failure_code": None,
                "limitations": ["Provider ranking capped the inspected tail."],
            },
        ],
        "totals": {
            "occurrences_returned": 22,
            "unique_results": 12,
            "known_matches": 5,
            "intake_candidates": 3,
            "not_forwarded": 3,
            "unresolved_identity": 1,
            "possible_duplicate_flags": 1,
            "metadata_conflicts": 1,
        },
        "assessments": {
            "plausible_core": 2,
            "plausible_contextual": 1,
            "uncertain": 0,
        },
        "intake_issue": {
            "created": True,
            "number": 31,
            "url": f"https://github.com/{REPOSITORY}/issues/31",
        },
        "notes": ["Counts describe intake triage, not eligibility."],
    }


def zero_run(day: str = "2026-09-01") -> dict:
    run = completed_run(day)
    for source in run["sources"]:
        for field in (
            "occurrences_returned",
            "unique_results",
            "candidate_hits",
            "exclusive_candidates",
        ):
            source[field] = 0
        source["limitations"] = []
    for field in run["totals"]:
        run["totals"][field] = 0
    for field in run["assessments"]:
        run["assessments"][field] = 0
    run["intake_issue"] = {"created": False, "number": None, "url": None}
    run["notes"] = ["Successful zero-candidate run."]
    return run


def partial_run(day: str = "2026-09-02") -> dict:
    run = completed_run(day)
    run["status"] = "partial"
    failed = run["sources"][1]
    failed["status"] = "failed"
    failed["queries_completed"] = 1
    for field in (
        "occurrences_returned",
        "unique_results",
        "candidate_hits",
        "exclusive_candidates",
    ):
        failed[field] = None
    failed["failure_code"] = "connector_unavailable"
    failed["limitations"] = ["Exa did not complete the required search."]
    for field in run["totals"]:
        run["totals"][field] = None
    for field in run["assessments"]:
        run["assessments"][field] = 0
    run["intake_issue"] = {"created": False, "number": None, "url": None}
    return run


class SurveillanceRunTests(unittest.TestCase):
    def test_completed_run_is_valid(self) -> None:
        result = validate_run(completed_run())
        self.assertEqual(result["totals"]["intake_candidates"], 3)

    def test_successful_zero_is_distinct_from_missing(self) -> None:
        result = validate_run(zero_run())
        self.assertEqual(result["totals"]["unique_results"], 0)
        self.assertFalse(result["intake_issue"]["created"])

    def test_partial_run_requires_null_aggregate_totals(self) -> None:
        result = validate_run(partial_run())
        self.assertEqual(result["status"], "partial")
        self.assertIsNone(result["totals"]["unique_results"])

    def test_batch_date_must_match(self) -> None:
        run = completed_run()
        run["batch_id"] = "ACADEMIC-2026-09-01"
        with self.assertRaisesRegex(MetricsError, "batch_id date"):
            validate_run(run)

    def test_window_offset_must_match_rome(self) -> None:
        run = completed_run()
        run["window_end"] = "2026-08-31T07:20:00+01:00"
        with self.assertRaisesRegex(MetricsError, "offset incompatible"):
            validate_run(run)

    def test_expected_source_requires_a_query(self) -> None:
        run = zero_run()
        run["sources"][0]["queries_planned"] = 0
        run["sources"][0]["queries_completed"] = 0
        with self.assertRaisesRegex(MetricsError, "requires a planned query"):
            validate_run(run)

    def test_unique_result_disposition_must_reconcile(self) -> None:
        run = completed_run()
        run["totals"]["known_matches"] += 1
        with self.assertRaisesRegex(MetricsError, "disposition"):
            validate_run(run)

    def test_incomplete_run_cannot_report_aggregate_zeroes(self) -> None:
        run = partial_run()
        run["totals"]["unique_results"] = 0
        with self.assertRaisesRegex(MetricsError, "must be null"):
            validate_run(run)

    def test_issue_creation_must_match_candidate_count(self) -> None:
        run = completed_run()
        run["intake_issue"] = {"created": False, "number": None, "url": None}
        with self.assertRaisesRegex(MetricsError, "issue creation"):
            validate_run(run)

    def test_comment_parser_accepts_one_marked_json_block(self) -> None:
        run = completed_run()
        body = f"Run summary\n\n{MARKER}\n```json\n{json.dumps(run)}\n```"
        self.assertEqual(extract_run(body)["batch_id"], run["batch_id"])

    def test_comment_parser_rejects_ambiguous_marked_body(self) -> None:
        run = completed_run()
        block = f"{MARKER}\n```json\n{json.dumps(run)}\n```"
        with self.assertRaisesRegex(MetricsError, "exactly one"):
            extract_run(block + "\n" + block)


class PublicStatisticsTests(unittest.TestCase):
    def test_payload_separates_run_health_and_candidate_yield(self) -> None:
        payload = build_public_payload(
            [completed_run(), zero_run(), partial_run()], 30, REPOSITORY
        )
        self.assertEqual(payload["summary"]["runDays"], 3)
        self.assertEqual(payload["summary"]["completedRuns"], 2)
        self.assertEqual(payload["summary"]["partialRuns"], 1)
        self.assertEqual(payload["summary"]["last7Days"]["newCandidates"], 3)
        self.assertEqual(payload["summary"]["last30Days"]["uniqueResults"], 12)
        self.assertEqual(payload["daily"][0]["candidateRate"], 0.25)
        self.assertEqual(payload["daily"][0]["knownOverlapRate"], 0.416667)
        self.assertIsNone(payload["daily"][1]["candidateRate"])
        self.assertIsNone(payload["daily"][2]["uniqueResults"])

    def test_zero_denominator_rates_are_null_not_zero(self) -> None:
        payload = build_public_payload([zero_run()], 30, REPOSITORY)
        row = payload["daily"][0]
        self.assertIsNone(row["candidateRate"])
        self.assertIsNone(row["knownOverlapRate"])
        self.assertIsNone(row["deduplicationShare"])

    def test_duplicate_day_fails_closed(self) -> None:
        first = completed_run()
        second = copy.deepcopy(first)
        second["repository_commit"] = "b" * 40
        with self.assertRaisesRegex(MetricsError, "duplicate"):
            build_public_payload([first, second], 30, REPOSITORY)

    def test_public_rows_contain_no_candidate_metadata(self) -> None:
        payload = build_public_payload([completed_run()], 30, REPOSITORY)
        validate_public_payload(payload)
        serialized = json.dumps(payload).lower()
        for forbidden in ("title", "authors", "abstract", "doi", "evidence_quote"):
            self.assertNotIn(f'"{forbidden}"', serialized)
        self.assertNotIn("intakeIssueUrl", payload["daily"][0])
        self.assertTrue(payload["daily"][0]["intakeIssueCreated"])

    def test_public_summary_tampering_is_rejected(self) -> None:
        payload = build_public_payload([completed_run()], 30, REPOSITORY)
        payload["summary"]["last7Days"]["newCandidates"] = 99
        with self.assertRaisesRegex(MetricsError, "summary disagrees"):
            validate_public_payload(payload)


if __name__ == "__main__":
    unittest.main()
