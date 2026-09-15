import json
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ontology.validate_ontology import check_delivery_contract
from scripts.enrichment.retain_document import validate_manifest

ROOT = Path(__file__).resolve().parents[1]


class DeliveryContractTests(unittest.TestCase):
    def test_every_field_and_table_is_mapped_and_policy_is_exhaustive(self):
        check_delivery_contract(json.loads((ROOT / 'ontology/cile-review-profile.yaml').read_text()))

    def test_seed_uses_existing_public_identity_exact_hashes_and_private_rights(self):
        data = json.loads((ROOT / 'config/verified-document-seed.json').read_text())
        validate_manifest(data)
        self.assertEqual(data['visibility'], 'private')
        self.assertFalse(data['rights_verified'])
        self.assertIsNone(data['licence_url'])

    def test_public_seed_without_independently_verified_rights_is_rejected(self):
        data = json.loads((ROOT / 'config/verified-document-seed.json').read_text())
        data['visibility'] = 'public'
        with self.assertRaisesRegex(RuntimeError, 'redistribution_not_authorised'):
            validate_manifest(data)

    def test_hourly_hybrid_lanes_reuse_existing_scheduler_and_persistence_first_contract(self):
        runbook = (ROOT / 'docs/operations/two-lane-delivery.md').read_text()
        current = (ROOT / 'docs/operations/hourly-hybrid-v4.md').read_text()
        self.assertIn('Lane A runs at :10 and Lane B at :40', runbook)
        self.assertIn('exactly two project-wide scouting windows per day', runbook)
        self.assertIn('Parallel Search is the default discovery provider', runbook)
        self.assertIn('CILE-HOUR40-1', runbook)
        self.assertIn('durable paper-stage transition', runbook)
        self.assertIn('CILE-IDENTITY-RESOLUTION-2', runbook)
        self.assertIn('forwarded_to_intake', runbook)
        self.assertIn('soft-close', runbook)
        self.assertIn('cile-validated-branch-recovery:1', runbook)
        self.assertIn('PERSIST', current)
        self.assertIn('ENRICH', current)
        self.assertIn('RESOLVE', current)
        self.assertIn('oldest pending observation is at least 24 hours old', current)
        self.assertNotIn('Complete up to three existing candidates', runbook)
        self.assertNotIn('schedule:', (ROOT / '.github/workflows/deploy-curator-worker.yml').read_text())

    def test_surveillance_docs_use_current_provider_order(self):
        automation = (ROOT / 'docs/operations/automation.md').read_text()
        novelty = (ROOT / 'docs/operations/novelty-depth.md').read_text()
        self.assertIn('Parallel Search is the default scheduled discovery provider', automation)
        self.assertIn('Parallel Search by default', novelty)
        self.assertNotIn('Exa is always primary', automation)
        self.assertNotIn('Parallel Search is **not** a co-equal daily source', novelty)

    def test_identity_and_calibration_v4_contracts_are_executable(self):
        identity = (ROOT / 'docs/operations/identity-resolution.md').read_text()
        calibration = (ROOT / 'docs/operations/calibration-trace-audit.md').read_text()
        self.assertIn('scripts.identity_resolution_v2', identity)
        self.assertIn('observation_key', identity)
        self.assertIn('fulltext-calibration-trace-audit.yml', calibration)
        self.assertIn('checkpoint-reuse', calibration)

    def test_seed_only_corrections_trigger_existing_deployment(self):
        workflow = (ROOT / '.github/workflows/deploy-curator-worker.yml').read_text()
        self.assertIn('      - "config/verified-document-seed.json"', workflow.split('permissions:')[0])
