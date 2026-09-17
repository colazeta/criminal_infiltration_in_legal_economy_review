"""Release-message tests; no research or publication decisions are generated."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from scripts.metrics.mark_statistics_unavailable import mark_unavailable, WARNING
from scripts.metrics.render_statistics_html import render_statistics_page
ROOT=Path(__file__).resolve().parents[1]

class StatisticsNoticeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.page=Path(self.temp.name)/'stats.html';self.stats=Path(self.temp.name)/'stats.json'
        self.page.write_text((ROOT/'site/stats.html').read_text(encoding='utf-8'),encoding='utf-8')
        self.stats.write_bytes((ROOT/'site/data/research-stats.json').read_bytes())
    def test_static_failure_is_visible_without_javascript_and_has_a_scoped_badge(self):
        original=self.stats.read_bytes()
        mark_unavailable(self.page,self.stats,as_of=datetime(2026,9,18,8,tzinfo=timezone.utc))
        text=self.page.read_text(encoding='utf-8')
        self.assertIn(WARNING,text);self.assertIn('data-state="unavailable"',text)
        self.assertIn('· Dati non disponibili',text);self.assertIn('18/09/2026 alle 10:00',text)
        self.assertRegex(text,r'<section id="research-kpis"[^>]* hidden>')
        self.assertRegex(text,r'<button id="statistics-retry"[^>]* hidden>')
        self.assertNotRegex(text,r'src="\./stats\.js')
        self.assertIn('non corregge il problema',text)
        self.assertIn('bibliometria e analisi dei paper hanno controlli separati',text)
        self.assertEqual(self.stats.read_bytes(),original)
    def test_repeated_failure_render_is_idempotent(self):
        now=datetime(2026,9,18,8,tzinfo=timezone.utc)
        mark_unavailable(self.page,self.stats,as_of=now);once=self.page.read_bytes()
        mark_unavailable(self.page,self.stats,as_of=now);self.assertEqual(self.page.read_bytes(),once)
    def test_marker_cannot_hide_nonempty_or_calendar_data(self):
        for field,value in [('daily',[{'status':'completed'}]),('extraRuns',[{}]),('calendar',{'asOf':'2026-09-18T00:00:00Z'}),('dataThrough','2026-09-18')]:
            original=(ROOT/'site/data/research-stats.json').read_text();p=json.loads(original);p[field]=value
            self.stats.write_text(json.dumps(p));before=self.page.read_bytes()
            with self.assertRaises(ValueError):mark_unavailable(self.page,self.stats)
            self.assertEqual(self.page.read_bytes(),before)
    def test_naive_notice_date_rejects_without_writing(self):
        before=self.page.read_bytes()
        with self.assertRaisesRegex(ValueError,'timezone-aware'):mark_unavailable(self.page,self.stats,as_of=datetime(2026,9,18))
        self.assertEqual(self.page.read_bytes(),before)
    def test_duplicate_notice_target_fails_closed(self):
        self.page.write_text('<p id="latest-execution"></p>'*2)
        with self.assertRaises(ValueError):mark_unavailable(self.page,self.stats)
    def test_empty_is_not_claimed_to_mean_that_searches_never_started(self):
        render_statistics_page(self.page,{'daily':[],'extraRuns':[]})
        text=self.page.read_text();self.assertIn('Nessuna esecuzione completata è pubblicabile',text)
        self.assertIn('non dimostra',text)
    def test_static_success_keeps_ordinary_and_extra_dates_distinct_and_ignores_failed_runs(self):
        p={'daily':[{'status':'completed','date':'2026-09-17'},{'status':'failed','date':'2026-09-18'}],
           'extraRuns':[{'status':'completed','startedAt':'2026-09-16T10:00:00Z','finishedAt':'2026-09-16T11:00:00Z'},
                        {'status':'failed','startedAt':'2026-09-18T10:00:00Z','finishedAt':'2026-09-18T11:00:00Z'}]}
        render_statistics_page(self.page,p);text=self.page.read_text()
        body=re.search(r'<p id="latest-execution"[^>]*>(.*?)</p>',text,re.S)[1]
        self.assertIn('17/09/2026',body);self.assertIn('16/09/2026 12:00',body)
        self.assertNotIn('18/09/2026',body);self.assertNotIn('failed',body)
        self.assertRegex(text,r'src="\./stats\.js')
    def test_successful_extra_summary_preserves_recorded_counts_without_json_fetch(self):
        run={'status':'completed','startedAt':'2026-09-16T10:00:00Z','finishedAt':'2026-09-16T11:00:00Z',
             'queriesCompleted':7,'queriesPlanned':7,'uniqueResults':12,'intakeCandidates':3}
        render_statistics_page(self.page,{'daily':[],'extraRuns':[run]})
        text=self.page.read_text();self.assertIn('Query: 7/7',text)
        self.assertIn('Risultati unici: 12',text);self.assertIn('Nuovi candidati segnalati: 3',text)
        self.assertNotIn('Candidati inviati alla coda',text)
    def test_legacy_minimal_fixture_remains_supported(self):
        self.page.write_text('<p id="latest-execution">Old result</p><script src="./stats.js" defer></script>')
        mark_unavailable(self.page,self.stats);self.assertIn(WARNING,self.page.read_text());self.assertNotIn('stats.js',self.page.read_text())

if __name__=='__main__':unittest.main()
