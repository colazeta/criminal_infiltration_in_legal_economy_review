"""Offline regressions for the read-only archive workspace (no browser dependency)."""
import json
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class Page(HTMLParser):
    def __init__(self, filename):
        super().__init__()
        self.elements = []
        self.feed((ROOT / 'site' / filename).read_text(encoding='utf-8'))
    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))
    def element(self, identifier):
        return next((tag, attrs) for tag, attrs in self.elements if attrs.get('id') == identifier)

class FrontendWorkspaceTests(unittest.TestCase):
    def test_pagination_preserves_the_population(self):
        code = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const context={document:{querySelector:()=>null}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);
const paginate=context.CILEPaperProcessing.pageRecords;
const records=Object.freeze(Array.from({length:292},(_,id)=>Object.freeze({id})));
const seen=[];
for(let n=1;n<=12;n++){const p=paginate(records,n,25);assert.equal(p.page,n);assert.equal(p.pages,12);seen.push(...p.rows.map(r=>r.id));}
assert.deepEqual(seen,records.map(r=>r.id));
assert.equal(paginate(records,12,25).rows.length,17);
assert.equal(paginate(records,999,25).page,12);
assert.equal(paginate(records,-1,25).page,1);
assert.equal(paginate(records,NaN,25).page,1);
assert.equal(paginate([],9,25).page,1);
assert.equal(paginate([],9,25).total,0);
assert.equal(paginate([],9,25).rows.length,0);
assert.equal(paginate(records,1,50).rows.length,50);
assert.equal(paginate(records,3,100).rows.length,92);
assert.equal(paginate(records.slice(0,2),12,25).page,1);
assert.throws(()=>paginate(records,1,0));
assert.equal(records.length,292);
"""
        result = subprocess.run(['node', '-e', code, str(ROOT/'site/paper-register.js')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_archive_retains_both_governed_collections(self):
        page = Page('index.html')
        for identifier in ['register', 'archive', 'registered-papers', 'paper-list', 'register-controls', 'archive-controls']:
            page.element(identifier)
        self.assertEqual(page.element('registered-papers')[0], 'tbody')
        self.assertEqual(page.element('register-filter-panel')[0], 'details')
        self.assertTrue(any(tag=='details' and attrs.get('class')=='reviewed-disclosure' for tag, attrs in page.elements))
        self.assertTrue(any(tag=='a' and attrs.get('class')=='skip-link' and attrs.get('href')=='#register' for tag, attrs in page.elements))

    def test_counts_and_downloads_name_distinct_populations(self):
        page = Page('index.html')
        for identifier in ['register-total-count', 'register-metadata-count', 'register-summary-count', 'included-count', 'editorial-count', 'coverage-date', 'archive-version']:
            page.element(identifier)
        hrefs = {attrs.get('href') for tag, attrs in page.elements if tag=='a'}
        self.assertTrue({'./data/paper-register.json','./data/archive.csv','./data/archive.json'} <= hrefs)

    def test_existing_style_stack_does_not_grow(self):
        styles = [attrs['href'] for tag, attrs in Page('index.html').elements if tag=='link' and attrs.get('rel')=='stylesheet']
        self.assertEqual(styles, ['./styles.css','./classic-site.css','./application.css'])

    def test_statistics_keep_operational_data_available(self):
        page = Page('stats.html')
        self.assertEqual(page.element('research-statistics')[0], 'details')
        page.element('enrichment-statistics')
        for identifier in ['daily-chart','source-table-body','daily-table-body','include-pending-toggle']:
            page.element(identifier)
        self.assertTrue(any(tag=='a' and attrs.get('href')=='./method.html' for tag,attrs in page.elements))

    def test_javascript_syntax(self):
        for name in ['paper-register.js','paper-sheet-support.js','paper-sheet-research.js']:
            result=subprocess.run(['node','--check',str(ROOT/'site'/name)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

if __name__ == '__main__':
    unittest.main()
