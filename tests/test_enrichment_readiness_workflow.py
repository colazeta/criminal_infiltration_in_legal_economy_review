"""Regression for the manual readiness workflow's YAML colon parsing failure."""
from pathlib import Path
import re
import unittest

class EnrichmentReadinessWorkflowTests(unittest.TestCase):
    def test_manual_readiness_does_not_gain_a_push_or_schedule_trigger(self):
        text=Path('.github/workflows/enrichment-readiness.yml').read_text()
        trigger=text.split('on:\n',1)[1].split('permissions:',1)[0]
        self.assertEqual(trigger.strip(),'workflow_dispatch:')
        self.assertNotIn('service_client.py activate',text)
        self.assertNotIn('service_client.py run',text)

    def test_colon_bearing_summary_uses_a_block_scalar(self):
        text=Path('.github/workflows/enrichment-readiness.yml').read_text()
        step=text.split('- name: Record activation boundary',1)[1]
        self.assertRegex(step,r'\n\s+run: \|\n\s+echo ')
        self.assertIsNone(re.search(r'^\s+run: echo .*: ',text,re.MULTILINE))
