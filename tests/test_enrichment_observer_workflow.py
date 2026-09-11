"""Observer workflow contracts; no private service calls in these tests."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class EnrichmentObserverWorkflowTests(unittest.TestCase):
    def test_separate_observer_is_read_only_and_never_runs_a_model(self):
        source = (ROOT / '.github/workflows/enrichment-observer.yml').read_text()
        self.assertIn('check(current_commit(), activate=False)', source)
        self.assertIn('contents: read', source)
        self.assertIn('persist-credentials: false', source)
        self.assertNotIn('activate=True', source)
        self.assertNotIn('service_client.py run', source)
        self.assertNotIn('scripts.enrichment.pilot', source)
        self.assertNotIn('cloudflare_api_token', source.lower())
        self.assertNotIn('upload-artifact', source)

    def test_observer_follows_minute40_without_becoming_the_work_queue(self):
        source = (ROOT / '.github/workflows/enrichment-observer.yml').read_text()
        self.assertIn("cron: '45 * * * *'", source)
        self.assertIn('cancel-in-progress: false', source)
        self.assertIn("github.ref == 'refs/heads/main'", source)
        self.assertIn('head_repository.full_name == github.repository', source)
        self.assertIn('enrichment_schedule_watermark_stalled', source)
        readiness = (ROOT / '.github/workflows/enrichment-readiness.yml').read_text()
        self.assertNotIn('  schedule:', readiness)
