"""Synthetic deployment/operational separation tests; no external requests."""
import copy
import unittest
from unittest.mock import patch
from scripts.enrichment import deployment_check as module

SHA = 'a' * 40
VERIFY = {'verified': True, 'commit': SHA}
STATE = {'commit': SHA, 'enabled': True, 'storage_backend': 'durable_object_sqlite',
         'scientific_extraction': 'blocked_pending_calibration',
         'scheduling': {'protocol': 'CILE-HOUR40-1', 'cron': '40 * * * *',
                        'schedule': {'first_slot': 2400000, 'next_slot': 6000000},
                        'iterations': [{'status': 'failed', 'error_code': 'identifier_resolution_required'}]}}


class DeploymentCheckTests(unittest.TestCase):
    def test_only_safe_verify_retries_same_commit_before_activation(self):
        with patch.object(module, 'call', side_effect=[RuntimeError(module.STALE), VERIFY, STATE]) as call, patch.object(module.time, 'sleep') as sleep:
            result = module.check(SHA, activate=True)
        self.assertEqual([c.args[0] for c in call.call_args_list], ['verify', 'verify', 'activate'])
        self.assertTrue(all(c.kwargs['expected_commit'] == SHA for c in call.call_args_list))
        self.assertTrue(result['deployment_ready'])
        sleep.assert_called_once_with(10)

    def test_authentication_or_storage_errors_are_not_retried(self):
        for message in ['enrichment_service_http_401:service_authentication_required', 'enrichment_service_http_500:service_operation_failed']:
            with patch.object(module, 'call', side_effect=RuntimeError(message)) as call:
                with self.assertRaisesRegex(RuntimeError, message): module.check(SHA, activate=True)
                self.assertEqual(call.call_count, 1)

    def test_stale_retry_budget_is_finite_and_never_activates(self):
        with patch.object(module, 'call', side_effect=RuntimeError(module.STALE)) as call, patch.object(module.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, module.STALE): module.check(SHA, activate=True, attempts=3)
            self.assertEqual(call.call_count, 3)
            self.assertTrue(all(c.args[0] == 'verify' for c in call.call_args_list))

    def test_paper_failure_is_retained_but_not_called_a_deployment_failure(self):
        with patch.object(module, 'call', side_effect=[VERIFY, STATE]) as call:
            result = module.check(SHA)
        self.assertEqual([c.args[0] for c in call.call_args_list], ['verify', 'status'])
        self.assertEqual(result['scheduling']['iterations'][0]['status'], 'failed')
        self.assertFalse(result['paper_work_executed_by_check'])
        self.assertEqual(result['scientific_extraction'], 'blocked_pending_calibration')

    def test_wrong_readback_or_schedule_does_not_pass(self):
        for field, value in [('commit', 'b' * 40), ('enabled', False), ('scheduling', {})]:
            state = copy.deepcopy(STATE); state[field] = value
            with patch.object(module, 'call', side_effect=[VERIFY, state]):
                with self.assertRaises(RuntimeError): module.check(SHA, activate=True)
        bad = copy.deepcopy(STATE); bad['scheduling']['schedule']['first_slot'] = 0
        with patch.object(module, 'call', side_effect=[VERIFY, bad]):
            with self.assertRaisesRegex(RuntimeError, 'slot_invalid'): module.check(SHA)

    def test_invalid_expected_version_never_reads_private_state(self):
        with patch.object(module, 'call') as call:
            with self.assertRaisesRegex(RuntimeError, 'invalid_expected'): module.check('main', activate=True)
            call.assert_not_called()
