"""A successful register readback also proves delivery of its reader controls."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.curation.verify_published_register import verify_sheet_support, RENDERER_ASSETS
from scripts.curation.build_paper_support import build_payload

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://example.test/project/data/paper-register.json'


class PublicReaderDeliveryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.site = Path(directory.name)
        register = json.loads((ROOT / 'site/data/paper-register.json').read_text())
        (self.site / 'paper-support.json').write_text(json.dumps(build_payload(ROOT, register)))
        for name in RENDERER_ASSETS:
            (self.site / name).write_bytes((ROOT / 'site' / name).read_bytes())

    def served(self, url):
        return (self.site / url.rsplit('/', 1)[-1]).read_bytes()

    def test_receipt_attests_navigation_and_layout_bytes(self):
        with patch('scripts.curation.verify_published_register.public_bytes', self.served):
            receipt = verify_sheet_support(URL, self.site / 'data/paper-register.json')
        for name in ('workspace.js', 'application.css', 'classic-site.css'):
            self.assertEqual(receipt['renderer_assets'][name],
                             hashlib.sha256((ROOT / 'site' / name).read_bytes()).hexdigest())

    def test_old_navigation_or_layout_cannot_pass_as_delivered(self):
        for name in ('workspace.js', 'application.css', 'classic-site.css'):
            def stale(url):
                return b'older release' if url.endswith('/' + name) else self.served(url)
            with self.subTest(name=name), patch('scripts.curation.verify_published_register.public_bytes', stale):
                with self.assertRaisesRegex(ValueError, 'renderer is stale'):
                    verify_sheet_support(URL, self.site / 'data/paper-register.json')
