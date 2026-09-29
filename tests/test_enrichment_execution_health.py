"""Receipt-based observer regressions; no provider or private-service calls."""
import copy
from datetime import datetime
import json
from pathlib import Path
import unittest

from scripts.metrics.enrichment_execution_health import execution_health, HOUR

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / 'tests/fixtures/enrichment-observer-20260929.json').read_text())
NOW = int(datetime.fromisoformat(FIXTURE['observed_at'].replace('Z', '+00:00')).timestamp() * 1000)


class ExecutionHealthTests(unittest.TestCase):
    def setUp(self):
        self.scheduling = copy.deepcopy(FIXTURE['scheduling'])

    def test_live_green_observer_receipt_exposes_eighteen_terminal_failures(self):
        before = copy.deepcopy(self.scheduling)
        result = execution_health(self.scheduling, NOW)
        self.assertGreater(self.scheduling['schedule']['next_slot'], NOW)
        self.assertEqual(result['status'], 'degraded')
        self.assertEqual(result['error_code'], 'enrichment_recent_iterations_failed')
        self.assertEqual(result['consecutive_failed_in_sample'], 18)
        self.assertEqual(result['failure_codes_in_streak'], {'rate_limited': 18})
        self.assertEqual(self.scheduling, before)

    def test_terminal_completion_breaks_streak_without_claiming_progress(self):
        self.scheduling['iterations'][0].update(status='completed', error_code=None)
        result = execution_health(self.scheduling, NOW)
        self.assertEqual(result['status'], 'no_failure_cluster')
        self.assertIsNone(result['error_code'])
        self.assertEqual(result['consecutive_failed_in_sample'], 0)
        self.assertNotIn('assessment_completed', result)

    def test_provider_identity_survives_the_closed_error_projection(self):
        for receipt in self.scheduling['iterations']:
            if receipt['status'] == 'failed':
                receipt['error_code'] = 'openalex_rate_limited'
        result = execution_health(self.scheduling, NOW)
        self.assertEqual(result['failure_codes_in_streak'], {'openalex_rate_limited': 18})

    def test_one_or_two_failures_do_not_raise_cluster_alarm(self):
        for count in [1, 2]:
            with self.subTest(count=count):
                self.scheduling['iterations'][count]['status'] = 'completed'
                result = execution_health(self.scheduling, NOW)
                self.assertIsNone(result['error_code'])
                self.scheduling = copy.deepcopy(FIXTURE['scheduling'])

    def test_pending_or_running_ticket_cannot_hide_failed_terminal_receipts(self):
        for status in ['pending', 'running']:
            with self.subTest(status=status):
                self.scheduling['iterations'][0]['status'] = status
                result = execution_health(self.scheduling, NOW)
                self.assertEqual(result['status'], 'degraded')
                self.assertEqual(result['consecutive_failed_in_sample'], 17)

    def test_sample_order_does_not_change_result(self):
        expected = execution_health(self.scheduling, NOW)
        self.scheduling['iterations'].reverse()
        self.assertEqual(execution_health(self.scheduling, NOW), expected)

    def test_missing_history_never_becomes_zero_failures(self):
        for value in [None, {}, {'schedule': self.scheduling['schedule']},
                      {**self.scheduling, 'iterations': None}]:
            with self.subTest(value=value):
                result = execution_health(value, NOW)
                self.assertEqual(result['status'], 'unavailable')
                self.assertIsNone(result['consecutive_failed_in_sample'])
                self.assertIsNone(result['observed_iterations'])

    def test_empty_history_is_unknown_and_only_gets_initial_grace(self):
        self.scheduling['iterations'] = []
        first = self.scheduling['schedule']['first_slot']
        initial = execution_health(self.scheduling, first + HOUR)
        self.assertEqual(initial['status'], 'awaiting_execution')
        self.assertIsNone(initial['consecutive_failed_in_sample'])
        stale = execution_health(self.scheduling, NOW)
        self.assertEqual(stale['error_code'], 'enrichment_terminal_receipt_stalled')
        self.assertIsNone(stale['consecutive_failed_in_sample'])

    def test_stale_completed_receipt_does_not_hide_execution_stall(self):
        self.scheduling['iterations'] = self.scheduling['iterations'][4:]
        self.scheduling['iterations'][0]['status'] = 'completed'
        result = execution_health(self.scheduling, NOW)
        self.assertEqual(result['error_code'], 'enrichment_terminal_receipt_stalled')

    def test_malformed_or_wrong_schedule_receipts_fail_closed(self):
        cases = [('scheduled_at', True), ('scheduled_at', NOW + HOUR),
                 ('scheduled_at', 0), ('status', 'unknown'), ('status', []),
                 ('schedule_id', 'another-schedule')]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                scheduling = copy.deepcopy(self.scheduling)
                scheduling['iterations'][0][field] = value
                result = execution_health(scheduling, NOW)
                self.assertEqual(result['status'], 'unavailable')
                self.assertIsNone(result['consecutive_failed_in_sample'])

    def test_duplicate_or_oversize_sample_is_unavailable(self):
        self.scheduling['iterations'][-1] = self.scheduling['iterations'][0]
        self.assertEqual(execution_health(self.scheduling, NOW)['status'], 'unavailable')
        self.scheduling['iterations'] *= 2
        self.assertEqual(execution_health(self.scheduling, NOW)['status'], 'unavailable')

    def test_arbitrary_error_text_is_not_projected(self):
        for value in ['private retained text: Bearer abc', 'ghp_credentialshapedtext', None, []]:
            with self.subTest(value=value):
                self.scheduling['iterations'][0]['error_code'] = value
                result = execution_health(self.scheduling, NOW)
                self.assertEqual(result['failure_codes_in_streak']['unclassified_failure'], 1)
                self.assertNotIn('Bearer', json.dumps(result))
                self.assertNotIn('ghp_', json.dumps(result))

    def test_deployment_readiness_stays_independent(self):
        source = (ROOT / 'scripts/enrichment/deployment_check.py').read_text()
        self.assertNotIn('execution_health', source)
