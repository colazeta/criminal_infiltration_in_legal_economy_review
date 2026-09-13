"""Offline software fixtures: not calibration evidence or real paper metadata."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StudyGeographyTests(unittest.TestCase):
    def test_source_scope_and_unique_country_counts(self):
        script = r"""
const assert=require('node:assert/strict');
require('./site/paper-sheet-research.js');
const g=globalThis.CILEPaperGeography;
assert.deepEqual(g.parse('Italy').countries,['IT']);
assert.deepEqual(g.parse('Italia').countries,['IT']);
assert.deepEqual(g.parse('Italy and Germany').countries,['DE','IT']);
assert.deepEqual(g.parse('Italy; Italy; Germany').countries,['DE','IT']);
assert.deepEqual(g.parse('UK; United States').countries,['GB','US']);
assert.deepEqual(g.parse('Bosnia and Herzegovina; France').countries,['BA','FR']);
assert.deepEqual(g.parse('Trinidad and Tobago').countries,['TT']);
assert.deepEqual(g.parse('Northern Italy').countries,['IT']);
assert.deepEqual(g.parse('Calabria (Italy)').countries,['IT']);
assert.deepEqual(g.parse('Italy (Lombardy)').countries,['IT']);
assert.deepEqual(g.parse('Countries: Italy; Germany | Scope: local case studies').countries,['DE','IT']);
for(const text of ['Italian mafia in Germany','Italian firms','University of Milan, Italy', 'Italy and other countries', 'Congo', 'Korea', 'Georgia', 'Sicily', 'Milan', 'former Soviet Union'])assert.equal(g.parse(text).countries.length,0,text);
assert.equal(g.parse('Europe').kind,'supranational');
assert.equal(g.parse('Global').kind,'global');
const fact=(value,status='reported',origin='source')=>({value,status,origin,evidence_span_ids:['e1']});
const research=studies=>({availability:'available',research:{assessment_state:'unreviewed_proposal',studies,spans:[{id:'e1'}],source_coverage:'abstract_only',updated_at:'2026-09-13'}});
const a=g.fromResearch(research([{geography:fact('Italy')},{geography:fact('Italy; France')}]));
assert.deepEqual(a.countries,['FR','IT']);
assert.equal(g.fromResearch(research([{geography:fact('Italy','ambiguous')}])).countries.length,0);
assert.equal(g.fromResearch(research([{geography:fact('Italy','reported','analyst')}])).countries.length,0);
assert.equal(g.fromResearch({availability:'withheld',research:null}).countries.length,0);
const broken=research([{geography:fact('Italy')}]);broken.research.spans=[];
assert.equal(g.fromResearch(broken).countries.length,0);
const b=g.fromResearch(research([{geography:fact('Italy')},{geography:fact(null,'not_reported')}]));
const records=[{id:'a',title:'Synthetic A'},{id:'b',title:'Synthetic B'},{id:'c',title:'Synthetic C'},{id:'a',title:'duplicate id'}];
const result=g.aggregate(records,new Map([['a',a],['b',b],['c',{status:'error',countries:[]}]]));
assert.equal(result.total,3);assert.equal(result.known,2);assert.equal(result.partial,1);
assert.deepEqual(result.rows.map(r=>[r.code,r.count]),[['IT',2],['FR',1]]);
assert.equal(result.rows[0].papers.length,2);
assert.equal(g.aggregate(records.slice(2,3),new Map([['a',a],['b',b]])).known,0);
console.log('Geography scope, evidence, identity, missingness and counting checks passed');
"""
        subprocess.run(['node', '-e', script], cwd=ROOT, check=True, capture_output=True, text=True)

    def test_public_projection_and_shared_population_wiring(self):
        stats = (ROOT / 'site/geography-statistics.js').read_text()
        self.assertIn('CILEPaperResearch.selectRecord', stats)
        self.assertIn("credentials:'omit'", stats)
        self.assertIn("cache:'no-store'", stats)
        self.assertIn("cile:bibliometric-view", stats)
        self.assertNotIn('/api/paper-enrichment/', stats)
        self.assertNotIn('localStorage', stats)
        self.assertNotIn('innerHTML', stats)
        self.assertIn('signatures.get(record.id)===sig', stats)
        self.assertIn('failures<4', stats)
        self.assertIn('study-geography', stats)
        self.assertIn("import('./geography-statistics.js')", (ROOT / 'site/bibliometrics.js').read_text())
        self.assertIn("CILEBibliometricView = data", (ROOT / 'site/bibliometrics.js').read_text())
        self.assertIn("Ambito geografico dell’analisi", (ROOT / 'site/paper-sheet-research.js').read_text())


if __name__ == '__main__':
    unittest.main()
