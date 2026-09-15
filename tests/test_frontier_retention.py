import unittest
from pathlib import Path

from scripts.enrichment.retain_frontier_documents import frontier, owns_b, title_matches

ROOT = Path(__file__).resolve().parents[1]


class FrontierRetentionTests(unittest.TestCase):
    def test_known_b_owned_public_full_text_candidates_are_selectable(self):
        selected = {record['id'] for record, _ in frontier(6)}
        self.assertIn('CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-002', selected)
        self.assertTrue(all(owns_b(candidate_id) for candidate_id in selected))

    def test_title_identity_tolerates_layout_and_punctuation_only(self):
        title = 'Tough on criminal wealth? Exploring the link between organized crime’s asset confiscation and regional entrepreneurship'
        text = 'TOUGH ON CRIMINAL WEALTH?\nExploring the link between organized crime\'s asset confiscation and regional entrepreneurship\nElisa Operti'
        self.assertTrue(title_matches(title, text))
        self.assertFalse(title_matches(title, 'A completely different paper about unrelated institutions and markets.'))

    def test_private_service_claim_wraps_source_and_document_writes(self):
        store = (ROOT / 'curator-app/src/enrichment-store.js').read_text(encoding='utf-8')
        claim = (ROOT / 'curator-app/src/frontier-retention-claim.js').read_text(encoding='utf-8')
        for operation in ('document-retention-claim', 'source-claimed', 'document-claimed', 'document-retention-release', 'document-retention-abort'):
            self.assertIn(operation, store)
        self.assertIn("kind='extraction'", claim)
        self.assertIn("status='blocked'", claim)
        self.assertIn('lease_token', claim)
        self.assertIn('lease_until', claim)
        self.assertIn('model_calibration_required', claim)

    def test_frontier_runner_is_private_and_does_not_infer_rights(self):
        source = (ROOT / 'scripts/enrichment/retain_frontier_documents.py').read_text(encoding='utf-8')
        self.assertIn("'visibility': 'private'", source)
        self.assertIn("'rights_verified': False", source)
        self.assertIn("'licence_status': 'not_verified'", source)
        self.assertIn("row.get('evidence_source') != 'Governed PDF fetch'", source)


if __name__ == '__main__':
    unittest.main()
