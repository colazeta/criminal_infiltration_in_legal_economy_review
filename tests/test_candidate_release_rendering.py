from __future__ import annotations
import copy
from html.parser import HTMLParser
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from scripts.curation.build_paper_register import build_payload, render_page, render_source_link
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/metrics'))
import fetch_surveillance_ledger_quarantine as ledger

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.hrefs=[]
    def handle_starttag(self, tag, attrs):
        if tag == 'a': self.hrefs.extend(v for k,v in attrs if k == 'href')

class ReleaseRenderingTests(unittest.TestCase):
    def test_entire_actual_candidate_register_renders_without_http_anchors(self):
        payload=build_payload(ROOT); original=copy.deepcopy(payload)
        with tempfile.TemporaryDirectory() as folder:
            page=Path(folder)/'index.html'
            page.write_text((ROOT/'site/index.html').read_text())
            render_page(page,payload)
            parser=Links(); parser.feed(page.read_text())
            self.assertFalse(any(url.startswith('http:') for url in parser.hrefs))
            self.assertIn(str(len(payload['records']))+' record registrati',page.read_text())
            self.assertEqual(payload,original)
    def test_http_provenance_is_not_dropped_or_silently_upgraded(self):
        url='http://cepr.org/publications/dp12140'
        html=render_source_link(url,1)
        self.assertIn(url,html); self.assertNotIn('href=',html)
        self.assertNotIn('https:',html)
    def test_https_anchor_escapes_markup(self):
        html=render_source_link('https://example.org/?a="<test>"',2)
        self.assertIn('&quot;&lt;test&gt;&quot;',html)
    def test_unsafe_locator_is_never_rendered(self):
        for url in ('javascript:alert(1)','https://user:pass@example.org/a','//example.org/a'):
            with self.assertRaises(ValueError): render_source_link(url,1)
    def test_only_exact_redundant_terminal_is_reconciled(self):
        batch='ACADEMIC-2026-09-12-EXTRA-7652f77d6fde'
        comments=[{'id':cid,'body':batch} for cid in (5647980951,5652046564,99999999)]
        with patch.object(ledger,'_RAW_API_GET',return_value=(comments,{})):
            kept,_=ledger._quarantine_api_get('https://api.github.com/repos/owner/repo/issues/30/comments','unused')
        self.assertEqual([c['id'] for c in kept],[5652046564,99999999])
    def test_exact_comment_id_with_wrong_batch_still_fails(self):
        with patch.object(ledger,'_RAW_API_GET',return_value=([{'id':5647980951,'body':'wrong batch'}],{})):
            with self.assertRaises(ledger._base.MetricsError):
                ledger._quarantine_api_get('https://api.github.com/repos/owner/repo/issues/30/comments','unused')
