import json
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.ontology.validate_ontology import check_delivery_contract
from scripts.enrichment.retain_document import validate_manifest
ROOT=Path(__file__).resolve().parents[1]
class DeliveryContractTests(unittest.TestCase):
    def test_every_field_and_table_is_mapped_and_policy_is_exhaustive(self):
        check_delivery_contract(json.loads((ROOT/'ontology/cile-review-profile.yaml').read_text()))
    def test_seed_uses_existing_public_identity_exact_hashes_and_private_rights(self):
        data=json.loads((ROOT/'config/verified-document-seed.json').read_text());validate_manifest(data)
        self.assertEqual(data['visibility'],'private');self.assertFalse(data['rights_verified']);self.assertIsNone(data['licence_url'])
    def test_public_seed_without_independently_verified_rights_is_rejected(self):
        data=json.loads((ROOT/'config/verified-document-seed.json').read_text());data['visibility']='public'
        with self.assertRaisesRegex(RuntimeError,'redistribution_not_authorised'):validate_manifest(data)
    def test_the_only_remaining_daily_task_and_hourly_enrichment_are_not_new_schedulers(self):
        runbook=(ROOT/'docs/operations/two-lane-delivery.md').read_text()
        self.assertIn('once daily',runbook);self.assertIn('CILE-HOUR40-1',runbook)
        self.assertNotIn('schedule:',(ROOT/'.github/workflows/deploy-curator-worker.yml').read_text())

    def test_seed_only_corrections_trigger_existing_deployment(self):
        workflow=(ROOT/'.github/workflows/deploy-curator-worker.yml').read_text()
        self.assertIn('      - "config/verified-document-seed.json"',workflow.split('permissions:')[0])
