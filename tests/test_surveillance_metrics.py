from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/metrics"))

from fetch_surveillance_ledger import (  # noqa: E402
    MARKER,
    extract_run,
    verify_intake_issue,
)
from surveillance import (  # noqa: E402
    MetricsError,
    build_public_payload,
    validate_public_payload,
    validate_run,
)


REPOSITORY = "colazeta/criminal_infiltration_in_legal_economy_review"


def candidate_issue(run: dict, number: int = 31) -> dict:
    batch_id = run["batch_id"]
    return {
        "number": number,
        "html_url": f"https://github.com/{REPOSITORY}/issues/{number}",
        "title": f"[INTAKE][ACADEMIC] {batch_id}",
        "body": (
            f"### Batch ID\n\n{batch_id}\n\n"
            "### Search and provenance log\n\nConsensus and Exa completed.\n\n"
            "### Candidate records\n\nThree structured candidate records.\n\n"
            "### Safeguards\n\n- [x] No candidate was marked eligible or published."
        ),
        "user": {"login": "colazeta"},
    }


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

    def test_source_set_must_match_governance(self) -> None:
        run = completed_run()
        run["expected_sources"][1] = "Google Scholar"
        run["sources"][1]["source"] = "Google Scholar"
        with self.assertRaisesRegex(MetricsError, "governed active source set"):
            validate_run(run)

    def test_unique_result_disposition_must_reconcile(self) -> None:
        run = completed_run()
        run["totals"]["known_matches"] += 1
        with self.assertRaisesRegex(MetricsError, "disposition"):
            validate_run(run)

    def test_cross_source_union_cannot_be_smaller_than_a_source(self) -> None:
        run = completed_run()
        run["totals"].update(
            {
                "unique_results": 7,
                "known_matches": 3,
                "intake_candidates": 3,
                "not_forwarded": 1,
                "unresolved_identity": 0,
            }
        )
        with self.assertRaisesRegex(MetricsError, "fall below a source total"):
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

    def test_intake_issue_url_must_match_number_and_repository(self) -> None:
        run = completed_run()
        run["intake_issue"]["url"] = "https://github.com/other/repo/issues/999"
        with self.assertRaisesRegex(MetricsError, "canonical repository"):
            validate_run(run)

    def test_referenced_intake_issue_must_match_batch_and_template(self) -> None:
        run = validate_run(completed_run())
        verify_intake_issue(run, candidate_issue(run), {"colazeta"}, 30)

        wrong_batch = candidate_issue(run)
        wrong_batch["body"] = wrong_batch["body"].replace(
            run["batch_id"], "ACADEMIC-2026-08-30", 1
        )
        with self.assertRaisesRegex(MetricsError, "batch ID"):
            verify_intake_issue(run, wrong_batch, {"colazeta"}, 30)

    def test_metrics_ledger_cannot_pose_as_intake_issue(self) -> None:
        run = validate_run(completed_run())
        run["intake_issue"] = {
            "created": True,
            "number": 30,
            "url": f"https://github.com/{REPOSITORY}/issues/30",
        }
        issue = candidate_issue(run, number=30)
        with self.assertRaisesRegex(MetricsError, "metrics ledger"):
            verify_intake_issue(run, issue, {"colazeta"}, 30)

    def test_referenced_intake_issue_requires_authorised_issue_author(self) -> None:
        run = validate_run(completed_run())
        issue = candidate_issue(run)
        issue["user"]["login"] = "someone-else"
        with self.assertRaisesRegex(MetricsError, "author is not authorised"):
            verify_intake_issue(run, issue, {"colazeta"}, 30)

    def test_exclusive_candidate_attribution_must_be_exact(self) -> None:
        run = completed_run()
        run["sources"][0]["candidate_hits"] = 3
        run["sources"][0]["exclusive_candidates"] = 3
        run["sources"][1]["candidate_hits"] = 3
        run["sources"][1]["exclusive_candidates"] = 0
        with self.assertRaisesRegex(MetricsError, "exclusive candidate attribution"):
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
        self.assertEqual(payload["summary"]["last7Days"]["newCandidates"], 0)
        self.assertEqual(payload["summary"]["allTime"]["newCandidates"], 0)

    def test_windows_without_completed_runs_remain_null(self) -> None:
        payload = build_public_payload([partial_run()], 30, REPOSITORY)
        self.assertIsNone(payload["summary"]["last7Days"]["uniqueResults"])
        self.assertIsNone(payload["summary"]["last30Days"]["newCandidates"])
        self.assertIsNone(payload["summary"]["allTime"]["newCandidates"])
        consensus = next(
            row for row in payload["sources"] if row["source"] == "Consensus"
        )
        exa = next(row for row in payload["sources"] if row["source"] == "Exa")
        self.assertEqual(consensus["completedRuns"], 1)
        self.assertEqual(consensus["queriesCompleted"], 7)
        self.assertEqual(exa["queriesCompleted"], 1)
        self.assertIsNone(consensus["occurrencesReturned"])
        self.assertIsNone(exa["occurrencesReturned"])

    def test_old_completed_run_does_not_fill_current_window(self) -> None:
        payload = build_public_payload(
            [completed_run("2026-07-01"), partial_run("2026-08-31")],
            30,
            REPOSITORY,
        )
        self.assertIsNone(payload["summary"]["last30Days"]["uniqueResults"])
        self.assertEqual(payload["summary"]["allTime"]["newCandidates"], 3)
        self.assertTrue(
            all(row["occurrencesReturned"] is None for row in payload["sources"])
        )

    def test_empty_series_has_no_measured_volume(self) -> None:
        payload = build_public_payload([], 30, REPOSITORY)
        self.assertIsNone(payload["summary"]["last7Days"]["uniqueResults"])
        self.assertIsNone(payload["summary"]["last30Days"]["newCandidates"])
        self.assertIsNone(payload["summary"]["allTime"]["newCandidates"])

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

    def test_public_source_label_is_governed(self) -> None:
        payload = build_public_payload([completed_run()], 30, REPOSITORY)
        payload["sources"][0]["source"] = "Mafia Firms"
        with self.assertRaisesRegex(MetricsError, "governed active set"):
            validate_public_payload(payload)

    def test_public_exclusive_candidate_totals_are_exact(self) -> None:
        payload = build_public_payload([completed_run()], 30, REPOSITORY)
        payload["sources"][0]["exclusiveCandidates"] = 2
        payload["sources"][1]["exclusiveCandidates"] = 0
        with self.assertRaisesRegex(MetricsError, "exclusive candidate totals"):
            validate_public_payload(payload)


if __name__ == "__main__":
    unittest.main()
