"""A migration receipt must prove complete, private and idempotent persistence."""
import copy
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.architecture import normalize_extractions as migration


class ExtractionMigrationGateTest(unittest.TestCase):
    def receipt(self, migrated=2, verified=0):
        return dict(contract='CILE-EXTRACTION-RELATIONS-1', commit='c' * 40,
                    proposals=migrated + verified, migrated=migrated, verified=verified,
                    complete=True, scientific_decisions_changed=False,
                    private_content_exported=False, cutover_ready=False)

    def execute(self, receipts):
        with patch.dict(os.environ, {'GITHUB_SHA': 'c' * 40}), patch.object(migration, 'check') as check, patch.object(
                migration, 'call', side_effect=receipts) as call:
            result = migration.migrate()
            check.assert_called_once_with('c' * 40, activate=False)
            self.assertEqual(call.call_count, 2)
            for args in call.call_args_list:
                self.assertEqual(args.args, ('architecture-normalize',))
                self.assertEqual(args.kwargs, {'expected_commit': 'c' * 40})
            return result

    def test_all_proposals_then_zero_write_replay(self):
        result = self.execute([self.receipt(), self.receipt(0, 2)])
        self.assertTrue(result['idempotency_verified'])
        self.assertFalse(result['migration']['cutover_ready'])

    def test_incomplete_mixed_deployment_or_private_receipts_cannot_pass(self):
        variants = [dict(complete=False), dict(commit='d' * 40), dict(proposals=3),
                    dict(migrated=True), dict(private_content_exported=True),
                    dict(scientific_decisions_changed=True), dict(cutover_ready=True),
                    dict(unexpected_private_field='must never print')]
        for change in variants:
            with self.subTest(change=change):
                receipt = {**self.receipt(), **change}
                with self.assertRaisesRegex(RuntimeError, 'normalization_receipt_invalid'):
                    self.execute([receipt, self.receipt(0, 2)])

    def test_second_write_is_not_certified_as_idempotent(self):
        with self.assertRaisesRegex(RuntimeError, 'normalization_receipt_invalid'):
            self.execute([self.receipt(), copy.deepcopy(self.receipt())])

    def test_unready_private_version_cannot_start_normalization(self):
        with patch.dict(os.environ, {'GITHUB_SHA': 'c' * 40}), patch.object(
                migration, 'check', side_effect=RuntimeError('enrichment_service_http_409:stale_deployment')) as check, patch.object(migration, 'call') as call:
            with self.assertRaisesRegex(RuntimeError, 'stale_deployment'):
                migration.migrate()
            check.assert_called_once_with('c' * 40, activate=False)
            call.assert_not_called()

    def test_readiness_precedes_writes_and_normalization_failure_is_not_retried(self):
        events = []
        def ready(expected, **kwargs):
            events.append(('verified', expected))
        def normalize(operation, **kwargs):
            events.append((operation, kwargs['expected_commit']))
            raise RuntimeError('enrichment_service_http_500:architecture_normalization_failed')
        with patch.dict(os.environ, {'GITHUB_SHA': 'c' * 40}), patch.object(
                migration, 'check', side_effect=ready), patch.object(migration, 'call', side_effect=normalize):
            with self.assertRaisesRegex(RuntimeError, 'architecture_normalization_failed'):
                migration.migrate()
        self.assertEqual(events, [('verified', 'c' * 40), ('architecture-normalize', 'c' * 40)])

    def test_failure_diagnostics_retain_safe_cause_without_exception_payload(self):
        for code in ['enrichment_service_http_409:stale_deployment',
                     'enrichment_service_http_401:service_authentication_required',
                     'enrichment_service_http_500:architecture_normalization_failed',
                     'normalization_receipt_invalid']:
            self.assertEqual(migration.failure_code(RuntimeError(code)), code)
        for text in ['private source body and secret',
                     'enrichment_service_http_500:secret=private',
                     'enrichment_service_http_500:private_credential']:
            safe = migration.failure_code(RuntimeError(text))
            self.assertNotIn('private', safe)
            self.assertNotIn('secret', safe)
            self.assertNotIn('credential', safe)

    def test_deployment_backs_up_before_schema_and_migrates_before_activation(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / '.github/workflows/deploy-curator-worker.yml').read_text()
        self.assertLess(workflow.index('scripts.architecture.predeploy_backup'),
                        workflow.index('scripts/review_v2/prepare_cloudflare.py'))
        self.assertLess(workflow.index('scripts.architecture.normalize_extractions'),
                        workflow.index('scripts.enrichment.deployment_check --activate'))
        self.assertIn('if-no-files-found: error', workflow)
        self.assertIn('node-version: 24', workflow)


if __name__ == '__main__':
    unittest.main()
