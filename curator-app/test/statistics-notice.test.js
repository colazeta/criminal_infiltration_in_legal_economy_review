import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {createDocument} from './frontend-dom-fixture.js';
const code=fs.readFileSync(new URL('../../site/stats.js',import.meta.url),'utf8');
const baseline=JSON.parse(fs.readFileSync(new URL('../../site/data/research-stats.json',import.meta.url),'utf8'));
const ids=['statistics-notice','statistics-notice-title','latest-execution','statistics-notice-impact','research-statistics-state','statistics-retry','research-kpis','metrics-empty','metrics-content','metrics-error','run-status','daily-chart','daily-chart-title','chart-note','source-table-body','daily-table-body','extra-runs','extra-runs-body','new-candidates-7','all-time-candidates','unique-results-7','source-completion-30','data-through'];
function setup(fetcher,state='idle',timers={setTimeout,clearTimeout}) {
  const document=createDocument(); document.createElementNS=(_ns,tag)=>document.createElement(tag);
  const nodes=Object.fromEntries(ids.map(id=>{const n=document.createElement('div');n.id=id;return[id,n]}));
  nodes['statistics-notice'].setAttribute('data-state',state);
  const context=vm.createContext({document,fetch:fetcher,AbortController,...timers,Intl,Date,console});
  vm.runInContext(code,context);return{context,nodes,load:()=>context.loadResearchStatistics()};
}
const response=data=>({ok:true,json:async()=>data});
const state=t=>t.nodes['statistics-notice'].getAttribute('data-state');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function payload(n=0){const p=structuredClone(baseline),date=new Date().toISOString().slice(0,10);p.daily=[{date,status:'completed',uniqueResults:n,intakeCandidates:n,knownMatches:0,occurrencesReturned:n,candidateRate:n?1:null,intakeIssueCreated:n>0}];p.dataThrough=date;p.calendar={asOf:new Date().toISOString()};p.summary.last7Days={newCandidates:n,uniqueResults:n};p.summary.last30Days={completedRuns:1,sourceCompletionRate:1};p.summary.allTime={newCandidates:n};return p;}

test('loading hides indicators and does not describe browser activity as research progress',async()=>{
 let release;const t=setup(()=>new Promise(r=>{release=r}));
 assert.equal(state(t),'loading');assert.equal(t.nodes['research-kpis'].hidden,true);
 assert.match(t.nodes['latest-execution'].textContent,/non avvia ricerche/);
 assert.equal(t.nodes['statistics-retry'].disabled,true);
 release(response(baseline));await t.load();assert.equal(state(t),'empty');
});
test('a withheld publication remains server-rendered and never reads the empty fallback',async()=>{
 let calls=0;const t=setup(async()=>{calls++;return response(baseline)},'unavailable');
 await t.load();assert.equal(calls,0);assert.equal(state(t),'unavailable');
});
test('empty payload is not evidence of zero searches or of a process that never started',async()=>{
 const t=setup(async()=>response(baseline));await t.load();
 assert.equal(state(t),'empty');assert.equal(t.nodes['research-kpis'].hidden,true);
 assert.match(t.nodes['latest-execution'].textContent,/Non significa/);
 assert.doesNotMatch(t.nodes['latest-execution'].textContent,/serie.*non.*iniziata/);
});
test('a completed observed zero is rendered as zero, not missing',async()=>{
 const t=setup(async()=>response(payload()));await t.load();
 assert.equal(state(t),'ready');assert.equal(t.nodes['new-candidates-7'].textContent,'0');
 assert.equal(t.nodes['research-kpis'].hidden,false);assert.equal(t.nodes['metrics-content'].hidden,false);
});
for(const [kind,fetcher,pattern] of [
 ['network',async()=>{throw Error('private detail')},/Non è stato possibile leggere/],
 ['http',async()=>({ok:false,status:503}),/Non è stato possibile leggere/],
 ['json',async()=>({ok:true,json:async()=>{throw Error('secret payload')}}),/non è leggibile/],
 ['schema',async()=>response({daily:[]}),/non è leggibile/],
]) test(`${kind}: no zero counters, no raw diagnostics, real retry`,async()=>{
 const t=setup(fetcher);await t.load();assert.equal(state(t),'error');
 assert.equal(t.nodes['research-kpis'].hidden,true);assert.equal(t.nodes['metrics-content'].hidden,true);
 assert.match(t.nodes['latest-execution'].textContent,pattern);
 assert.doesNotMatch(t.nodes['latest-execution'].textContent,/secret|private detail|503/);
 assert.equal(t.nodes['statistics-retry'].disabled,false);
});
test('a timeout settles even if a fetch implementation ignores abort',async()=>{
 let expire;const t=setup(()=>new Promise(()=>{}),'idle',{setTimeout(fn){expire=fn;return 1},clearTimeout(){}});
 expire();await t.load();assert.equal(state(t),'error');assert.match(t.nodes['latest-execution'].textContent,/tempo previsto/);
});
test('refresh clears a previous success before failing; one retry can recover',async()=>{
 let good=true,calls=0;const t=setup(async()=>{calls++;if(!good)throw Error('offline');return response(payload(7))});
 await t.load();assert.equal(t.nodes['new-candidates-7'].textContent,'7');
 good=false;const pending=t.load();assert.equal(t.nodes['research-kpis'].hidden,true);await pending;
 assert.equal(state(t),'error');assert.equal(t.nodes['new-candidates-7'].textContent,'—');
 good=true;t.nodes['statistics-retry'].fire('click');await tick();assert.equal(state(t),'ready');assert.equal(calls,3);
});
test('rapid repeated requests share a single in-flight read',async()=>{
 let release,calls=0;const t=setup(()=>{calls++;return new Promise(r=>{release=r})});
 const a=t.load(),b=t.load();assert.equal(a,b);assert.equal(calls,1);release(response(baseline));await a;
});
test('staleness concerns the published snapshot, not whether searches are running',async()=>{
 const p=payload();p.calendar.asOf=new Date(Date.now()-27*3600000).toISOString();
 const t=setup(async()=>response(p));await t.load();assert.equal(state(t),'stale');
 assert.equal(t.nodes['research-kpis'].hidden,false);assert.match(t.nodes['latest-execution'].textContent,/non dimostra/);
 assert.match(t.nodes['run-status'].textContent,/26 ore/);
});
test('partial and failed attempts do not appear as public iterations or zero bars',async()=>{
 const p=payload(2);p.daily.push({date:'2001-01-01',status:'failed',uniqueResults:null,intakeCandidates:null,failureCodes:['private-code']});
 p.extraRuns=[{date:'2001-01-02',status:'partial',uniqueResults:null,intakeCandidates:null}];
 const t=setup(async()=>response(p));await t.load();
 assert.equal(t.context.buildIterationRows(p.daily,p.extraRuns).length,1);
 assert.equal(t.nodes['daily-table-body'].children.length,1);assert.equal(t.nodes['extra-runs'].hidden,true);
 assert.doesNotMatch(t.nodes['run-status'].textContent,/private-code|mancanti|retry|ledger/);
});
test('all requests are read-only, credential-free and abortable',async()=>{
 let options;const t=setup(async(_url,o)=>{options=o;return response(baseline)});await t.load();
 assert.equal(options.cache,'no-store');assert.equal(options.credentials,'omit');assert.equal(options.method,undefined);
 assert.ok(options.signal instanceof AbortSignal);
});
test('non-numeric counts and invalid refresh dates do not produce a success',async()=>{
 for(const change of [p=>p.summary.last7Days.newCandidates='0',p=>p.daily[0].intakeCandidates=-1,p=>p.calendar.asOf='not a date']){
  const p=payload();change(p);const t=setup(async()=>response(p));await t.load();assert.equal(state(t),'error');
 }
});
