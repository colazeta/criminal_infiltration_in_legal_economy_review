import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../../site/study-geography.js',import.meta.url),'utf8');
function api(extra={}){const c=vm.createContext({Intl,AbortController,setTimeout,clearTimeout,...extra});vm.runInContext(source,c);return c.CILEStudyGeography;}
const A=api(), normal=x=>JSON.parse(JSON.stringify(x));
const fact=(value,overrides={})=>({status:'reported',value,origin:'source',evidence_span_ids:['e1'],...overrides});
const projection=(geographies,overrides={})=>({availability:'available',research:{assessment_state:'unreviewed_proposal',source_coverage:'abstract_only',generation_kind:'automated',updated_at:'2026-09-13',studies:geographies.map((g,i)=>({id:'s'+i,geography:typeof g==='string'?fact(g):g})),spans:[{id:'e1',source_id:'source1',locator:'Abstract'}],sources:[{id:'source1',url:'https://example.org/paper'}],...overrides}});
for(const[value,codes]of [['South Africa',['ZA']],['North Macedonia',['MK']],['South Korea',['KR']],['North Korea',['KP']],['Italy',['IT']],['Italia',['IT']],['IT',['IT']],['Italy and Germany',['DE','IT']],['Italia, Germania e Paesi Bassi',['DE','IT','NL']],['United Kingdom',['GB']],['UK',['GB']],['United States of America',['US']],['Trinidad and Tobago',['TT']],['Trinidad and Tobago and Italy',['IT','TT']],['Bosnia and Herzegovina; Italy',['BA','IT']],['Northern Italy',['IT']],['Italy (municipalities)',['IT']],['Netherlands; Italy',['IT','NL']]]){
 test('normalises only the full geography phrase: '+value,()=>assert.deepEqual(normal(A.normaliseGeography(value).countries),codes));
}
for(const value of ['Italian mafia in Germany','Italy as origin; Germany as destination','German authors','Italy, except France','outside Italy','Georgia','Congo','Milan','Italy and','Italy and an unnamed country','Italy (France)','Italy; Europe','a global review mentioning Italy']){
 test('does not guess countries from ambiguous text: '+value,()=>assert.equal(A.normaliseGeography(value).kind,'unresolved'));
}
for(const value of ['Global','Europe','European Union','Latin America','multiple countries'])test('does not expand '+value+' to countries',()=>{const r=A.normaliseGeography(value);assert.equal(r.kind,'supranational');assert.equal(r.countries.length,0);});
test('geography is study-local, with original entities and source links retained',()=>{const r=A.extract(projection(['Italy (municipalities)','Germany']));assert.equal(r.studies[0].raw,'Italy (municipalities)');assert.equal(r.studies[0].evidence[0].url,'https://example.org/paper');assert.deepEqual(normal(r.countries),['DE','IT']);assert.equal(r.coverage,'abstract_only');});
test('one paper contributes once per country, not once per study',()=>{const r=A.extract(projection(['Italy','Italy; Germany']));const result=A.aggregate([{id:'a'}],new Map([['a',r]]));assert.equal(result.total,1);assert.equal(result.withCountries,1);assert.equal(result.multinational,1);assert.equal(new Map(result.ranking).get('IT'),1);assert.equal(new Map(result.ranking).get('DE'),1);});
test('denominator includes uncoded records and request failures',()=>{const r=A.extract(projection(['Italy']));const result=A.aggregate([{id:'a'},{id:'b'},{id:'c'}],new Map([['a',r],['b',{state:'error',countries:[]}]]));assert.equal(result.total,3);assert.equal(result.withCountries,1);assert.equal(result.states.get('error'),1);assert.equal(result.states.get('pending'),1);});
test('duplicate ids do not inflate the chart',()=>assert.throws(()=>A.aggregate([{id:'a'},{id:'a'}],new Map()),/duplicate/));
test('author affiliation, title and criminal nationality are never inputs',()=>{const p=projection([fact(null,{status:'not_reported',evidence_span_ids:[]})]);p.title='Italy';p.research.authors_affiliation='Germany';p.research.summary={value:'Italian mafia in France'};assert.equal(A.extract(p).countries.length,0);});
for(const status of ['ambiguous','not_reported','not_verifiable','not_applicable'])test('does not count '+status+' as an observed country',()=>assert.equal(A.extract(projection([fact(status==='ambiguous'?'Italy':null,{status})])).countries.length,0));
test('analyst interpretation cannot stand in for source-attributed geography',()=>assert.equal(A.extract(projection([fact('Italy',{origin:'analyst'})])).countries.length,0));
test('missing source span fails closed',()=>assert.throws(()=>A.extract(projection([fact('Italy',{evidence_span_ids:[]})])),/unsupported/));
test('broken source link fails closed',()=>assert.throws(()=>A.extract(projection(['Italy'],{sources:[]})),/broken/));
for(const state of ['not_assessed','not_registered','stale','withheld'])test('keeps '+state+' distinct',()=>{const r=A.extract({availability:state,research:null});assert.equal(r.state,state);assert.equal(r.countries.length,0);});
test('country coverage can be partial across studies',()=>{const r=A.extract(projection(['Italy',fact(null,{status:'not_reported',evidence_span_ids:[]})]));assert.equal(r.partial,true);assert.equal(A.aggregate([{id:'a'}],new Map([['a',r]])).partiallyCoded,1);});
test('refresh replaces same-count revisions, not cached countries',async()=>{let country='Italy';const i=A.createIndex([{id:'a'}],{read:async()=>projection([country]),selectResearch:x=>x});await i.scan();assert.equal(i.rows.get('a').countries[0],'IT');country='Germany';await i.scan();assert.equal(i.rows.get('a').countries[0],'DE');});
test('identity failures are failures, never missing country',async()=>{const i=A.createIndex([{id:'a'}],{read:async()=>projection(['Italy']),selectResearch:()=>{throw Error('identity_mismatch');}});await i.scan();assert.equal(i.rows.get('a').state,'error');assert.equal(i.progress.errors,1);assert.equal(i.progress.checked,0);});
test('scan has at most four workers and a single active promise',async()=>{let active=0,max=0;const records=Array.from({length:11},(_,n)=>({id:String(n)}));const i=A.createIndex(records,{read:async()=>{active++;max=Math.max(max,active);await new Promise(r=>setTimeout(r,2));active--;return projection(['Italy']);},selectResearch:x=>x});const first=i.scan();assert.equal(first,i.scan());await first;assert.equal(max,4);assert.equal(i.progress.checked,11);});
test('circuit breaker preserves unattempted states as pending',async()=>{const records=Array.from({length:30},(_,n)=>({id:String(n)}));const i=A.createIndex(records,{read:async()=>{throw Error('offline');},selectResearch:x=>x});await i.scan();assert.ok(i.progress.attempted<30);assert.ok([...i.rows.values()].some(x=>x.state==='pending'));assert.equal(i.progress.checked,0);});
test('HTTP requests omit credentials and bypass stale cache',async()=>{let options;await A.readJSON('https://example.org/paper',async(u,o)=>{options=o;return{ok:true,json:async()=>({})};});assert.equal(options.credentials,'omit');assert.equal(options.cache,'no-store');assert.ok(options.signal);});
test('HTTP failures remain explicit failures',async()=>assert.rejects(()=>A.readJSON('https://example.org',async()=>({ok:false})),/unavailable/));
test('no studies is not an assertion that the source omits geography',()=>assert.equal(A.extract(projection([])).state,'no_studies'));
test('not verifiable is not recoded as not reported',()=>assert.equal(A.extract(projection([fact(null,{status:'not_verifiable'})])).state,'not_verifiable'));
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.attributes={};this.style={};this.listeners={};this.textContent='';}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this.children=[...nodes];}
 setAttribute(k,v){this.attributes[k]=v;}
 addEventListener(k,v){this.listeners[k]=v;}
 get text(){return this.textContent+this.children.map(x=>x.text||'').join(' ');}
 walk(){return [this,...this.children.flatMap(x=>x.walk?x.walk():[])];}
}
test('rendered scope, bars, missingness and refresh follow the same selected records',async()=>{
 const host=new Element('div');let n=0,country='Germany';
 const B=api({document:{createElement:t=>new Element(t)},fetch:async url=>{n++;return {ok:true,json:async()=>projection([url.endsWith('a')?'Italy':country])};},CILEPaperResearch:{safeUrl:u=>u}});
 const records=[{id:'a',title:'Synthetic A'},{id:'b',title:'Synthetic B'}];
 const ui=B.mount({host,records,selectResearch:x=>x});ui.setRecords(records);
 await new Promise(r=>setTimeout(r,5));
 assert.match(host.text,/Italia/);assert.match(host.text,/Germania/);assert.match(host.text,/50%/);assert.match(host.text,/2\/2 record/);
 ui.setRecords([records[0]]);assert.match(host.text,/100%/);assert.match(host.text,/1\/1 record/);assert.doesNotMatch(host.text,/Germania/);assert.equal(n,2);
 ui.setRecords([]);assert.match(host.text,/corpus valutato è vuoto/);assert.equal(host.walk().find(x=>x.tag==='button').disabled,true);
 ui.setRecords(records);country='France';host.walk().find(x=>x.tag==='button').listeners.click();await new Promise(r=>setTimeout(r,5));
 assert.match(host.text,/Francia/);assert.doesNotMatch(host.text,/Germania/);assert.equal(n,4);
 const marks=host.walk().filter(x=>x.className==='bibliometric-bar-fill');assert.equal(marks.length,2);assert.ok(marks.every(x=>x.style.width==='100%'));
});
test('late requests do not restore an earlier scope',async()=>{
 const host=new Element('div'),resolve=[];
 const B=api({document:{createElement:t=>new Element(t)},fetch:url=>new Promise(done=>resolve.push(()=>done({ok:true,json:async()=>projection([url.endsWith('a')?'Italy':'Germany'])}))),CILEPaperResearch:{safeUrl:u=>u}});
 const records=[{id:'a',title:'Synthetic A'},{id:'b',title:'Synthetic B'}];const ui=B.mount({host,records,selectResearch:x=>x});ui.setRecords(records);ui.setRecords([records[0]]);resolve.forEach(f=>f());await new Promise(r=>setTimeout(r,5));
 assert.match(host.text,/1\/1 record/);assert.match(host.text,/Italia/);assert.doesNotMatch(host.text,/Germania/);assert.equal(resolve.length,2);
});
