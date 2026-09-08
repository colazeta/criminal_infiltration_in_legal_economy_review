"""Source cutover must unblock Exa while preserving historical truth and gates."""
import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/metrics"))
from build_research_stats import active_runs
from daily_calendar import CYCLE, calendar_projection
from fetch_surveillance_ledger import MARKERS, extract_run, fetch_validated_runs, verify_intake_issue
from surveillance import MetricsError, build_public_payload, validate_public_payload, validate_run
from scripts.curation.import_intake_issue import IntakeImportError, parse_intake_issue
from scripts.metrics.monitor_surveillance_heartbeat import comment_has_batch
from scripts.metrics import monitor_surveillance_heartbeat as heartbeat
from test_surveillance_metrics import REPOSITORY, candidate_issue, completed_run, exa_run, partial_run


def envelope(run):
    return f"Daily surveillance batch {run['batch_id']}: {run['status']}.\n\n{MARKERS[run['schema_version']]}\n```json\n{json.dumps(run)}\n```"


class ExaPolicyTests(unittest.TestCase):
    def test_watchdog_uses_current_scope_and_ignores_legacy_gaps(self):
        with patch("fetch_surveillance_ledger.fetch_validated_runs", return_value=[exa_run()]) as fetch, patch.object(heartbeat, "find_open_incident", return_value=None):
            self.assertEqual(heartbeat.reconcile(REPOSITORY, 30, "synthetic", date(2026, 9, 9), dry_run=True), "ok:ACADEMIC-2026-09-09")
            self.assertEqual(fetch.call_args.args[-1], CYCLE)
        with patch("fetch_surveillance_ledger.fetch_validated_runs") as fetch, patch.object(heartbeat, "api_request") as writes:
            self.assertEqual(heartbeat.reconcile(REPOSITORY, 30, "synthetic", date(2026, 9, 8)), "not_due:ACADEMIC-2026-09-08")
            fetch.assert_not_called(); writes.assert_not_called()

    def test_one_complete_source_is_complete_and_intake_parses_without_consensus(self):
        run = validate_run(exa_run())
        issue = candidate_issue(run)
        verify_intake_issue(run, issue, {"colazeta"}, 30)
        manifest = parse_intake_issue(issue["body"], issue["title"])
        self.assertEqual(len(manifest["candidates"]), 3)
        payload = build_public_payload([run], 30, REPOSITORY)
        validate_public_payload(payload)
        self.assertEqual(payload["daily"][0]["sourceCompleteness"], 1)
        self.assertEqual(payload["summary"]["last30Days"]["sourceCompletionRate"], 1)
        self.assertEqual([s["source"] for s in payload["sources"]], ["Exa"])

    def test_real_zero_remains_measured_zero(self):
        run = exa_run()
        for field in run["totals"]: run["totals"][field] = 0
        for field in run["assessments"]: run["assessments"][field] = 0
        for field in ("occurrences_returned", "unique_results", "candidate_hits", "exclusive_candidates"):
            run["sources"][0][field] = 0
        run["intake_issue"] = {"created": False, "number": None, "url": None}
        validate_run(run)
        payload = build_public_payload([run], 30, REPOSITORY)
        validate_public_payload(payload)
        self.assertEqual(payload["summary"]["allTime"]["newCandidates"], 0)

    def test_partial_queries_and_failed_source_are_not_zero_or_intake(self):
        for n, status in ((0, "failed"), (6, "partial")):
            run = exa_run()
            run["status"] = status
            source = run["sources"][0]
            source.update(status="failed", queries_completed=n, failure_code="timeout")
            for field in ("occurrences_returned", "unique_results", "candidate_hits", "exclusive_candidates"): source[field] = None
            for field in run["totals"]: run["totals"][field] = None
            for field in run["assessments"]: run["assessments"][field] = 0
            run["intake_issue"] = {"created": False, "number": None, "url": None}
            validate_run(run)
            payload = build_public_payload([run], 30, REPOSITORY)
            validate_public_payload(payload)
            self.assertEqual(payload["daily"][0]["status"], status)
            self.assertIsNone(payload["summary"]["allTime"]["newCandidates"])
            self.assertEqual(payload["sources"][0]["queriesCompleted"], n)
            run["intake_issue"] = exa_run()["intake_issue"]
            with self.assertRaises(MetricsError): validate_run(run)

    def test_current_calendar_denominator_counts_one_source_per_expected_day(self):
        run = exa_run()
        payload = build_public_payload([run], 30, REPOSITORY)
        calendar = calendar_projection([run], "2026-09-10T12:00:00Z", date(2026, 9, 9), CYCLE["review_id"])
        payload.update(schemaVersion=2, calendar=calendar)
        validate_public_payload(payload)
        self.assertEqual(calendar["sourceCompletionRate30"], 0.5)
        self.assertEqual(calendar["rows"][1]["queriesPlanned"], 7)
        self.assertIsNone(calendar["rows"][1]["queriesCompleted"])
        calendar["rows"][0]["expectedSources"] = 2
        with self.assertRaises(MetricsError): validate_public_payload(payload)

    def test_historical_sources_and_partial_outcomes_are_not_reinterpreted(self):
        old = partial_run("2026-09-08")
        before = copy.deepcopy(old)
        parsed = extract_run(envelope(old))
        self.assertEqual(parsed["schema_version"], 1)
        self.assertEqual(parsed["status"], "partial")
        self.assertEqual(old, before)
        self.assertEqual(active_runs([old, exa_run()]), [exa_run()])
        payload = build_public_payload([old], 30, REPOSITORY)
        validate_public_payload(payload)
        self.assertEqual(payload["daily"][0]["sourceCompleteness"], 0.5)

    def test_legacy_and_current_policies_cannot_be_combined_in_one_series(self):
        with self.assertRaises(MetricsError): build_public_payload([completed_run(), exa_run()], 30, REPOSITORY)
        with self.assertRaises(MetricsError): active_runs([completed_run("2026-09-09")])
        with self.assertRaises(ValueError): calendar_projection([completed_run("2026-09-09")], "2026-09-10T12:00:00Z", date(2026, 9, 9), CYCLE["review_id"])

    def test_new_ledger_rejects_source_downgrade_before_inventory_or_writes(self):
        run = completed_run("2026-09-09")
        comment = {"body": envelope(run), "user": {"login": "colazeta"}, "created_at": "2026-09-09T05:21:00Z", "updated_at": "2026-09-09T05:21:00Z"}
        with patch("fetch_surveillance_ledger.api_get", return_value=([comment], None)) as request:
            with self.assertRaisesRegex(MetricsError, "Exa-only"):
                fetch_validated_runs(REPOSITORY, 30, ["colazeta"], "synthetic-token", CYCLE)
            self.assertEqual(request.call_count, 1)

    def test_marker_version_and_payload_must_agree_and_heartbeat_reads_v2(self):
        run = exa_run()
        body = envelope(run)
        self.assertEqual(extract_run(body)["schema_version"], 2)
        self.assertTrue(comment_has_batch(body, run["batch_id"]))
        for broken in (body.replace(MARKERS[2], MARKERS[1]), body.replace("surveillance-run:v2", "surveillance-run:v3"), body + MARKERS[1]):
            with self.assertRaises(MetricsError): extract_run(broken)

    def test_consensus_cannot_reenter_current_search_or_intake_manifests(self):
        run = exa_run()
        broken = copy.deepcopy(run); broken["expected_sources"] = ["Consensus", "Exa"]
        with self.assertRaises(MetricsError): validate_run(broken)
        issue = candidate_issue(run)
        issue["body"] = issue["body"].replace('"Exa"', '"Consensus"')
        with self.assertRaises(MetricsError): verify_intake_issue(run, issue, {"colazeta"}, 30)
        with self.assertRaises(IntakeImportError): parse_intake_issue(issue["body"], issue["title"])

    def test_intake_requires_all_seven_windows_and_matching_versions(self):
        run = exa_run()
        issue = candidate_issue(run)
        for body in (issue["body"].replace("EXA-W7-Q1", "EXA-W6-Q2"), issue["body"].replace('"schema_version": 2', '"schema_version": 1')):
            broken = {**issue, "body": body}
            with self.assertRaises(MetricsError): verify_intake_issue(run, broken, {"colazeta"}, 30)
            with self.assertRaises(IntakeImportError): parse_intake_issue(body, issue["title"])

    def test_single_source_attribution_must_equal_persisted_total(self):
        run = exa_run(); run["sources"][0]["exclusive_candidates"] = 2
        with self.assertRaises(MetricsError): validate_run(run)
        payload = build_public_payload([exa_run()], 30, REPOSITORY)
        payload["sources"][0]["exclusiveCandidates"] = 2
        with self.assertRaises(MetricsError): validate_public_payload(payload)
