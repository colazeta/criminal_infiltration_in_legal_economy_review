import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {createDocument} from './frontend-dom-fixture.js';
import {indexRow,indexPage} from './index-fixture.js';

const source=fs.readFileSync(new URL('../../site/paper-register.js',import.meta.url),'utf8');
const stats=fs.readFileSync(new URL('../../site/enrichment-statistics.js',import.meta.url),'utf8');
const record=Object.freeze({id:'CAND-AUTO-FIXTURE',title:'Synthetic fixture',doi:'10.1234/example',sourceLinks:[]});
const projection={availability:'available',research:{source_coverage:'full_text',generation_kind:'automated',framework:{status:'proposed',primary:'diagnosis',secondary:[]}}};
const ok=data=>({ok:true,json:async()=>data});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function deferred(){let resolve;return {promise:new Promise(r=>{resolve=r;}),resolve:value=>resolve(value)};}
function context(fetch){const document=createDocument();const c=vm.createContext({document,fetch,URL,AbortController,setTimeout,clearTimeout});vm.runInContext(source,c);return c;}
function register(fetch,records=[record]){
 const c=context(fetch),controls=c.document.createElement('form');
 const filter=c.CILEPaperProcessing.mount({controls,records,onChange:()=>{},selectSupport:()=>({readingAid:{kind:'review_synopsis',synopsis:'Synthetic summary'}})});
 return {c,controls,filter,panel:controls.following,button:controls.following.querySelector('button')};
}
function statistics(fetch){
 const c=context(fetch),d=c.document;
 for(const [tag,id] of [['p','enrichment-statistics-status'],['button','enrichment-statistics-refresh']]){const n=d.createElement(tag);n.id=id;}
 vm.runInContext(stats,c);return {c,status:d.getElementById('enrichment-statistics-status'),counts:d.getElementById('enrichment-statistics-counts'),button:d.getElementById('enrichment-statistics-refresh')};
}

test('register requests the analysis index on opening, before any click or filter',async()=>{
 const waiting=deferred(),calls=[];
 const v=register(async(url,options)=>{calls.push({url,options});return url.startsWith('./')?ok({}):waiting.promise;});
 assert.equal(calls.filter(c=>c.url.includes('?view=index')).length,1);
 assert.match(v.panel.querySelector('#register-processing-status').textContent,/Caricamento/);
 assert.equal(v.panel.querySelector('#register-completion-status').hidden,true);
 assert.equal(v.button.hidden,true);
 waiting.resolve(ok(indexPage([indexRow(record,projection)])));await tick();
 assert.match(v.filter.describe(record),/Analisi AI: testo completo/);
 assert.match(v.filter.describe(record),/Diagnosi/);
 assert.equal(v.panel.querySelector('#register-completion-status').hidden,false);
 assert.equal(v.button.hidden,true);
 assert.ok(calls.every(c=>c.options.cache==='no-store'&&c.options.credentials==='omit'));
});

test('a stalled synopsis response does not postpone the independent analysis request',async()=>{
 const waiting=deferred(),calls=[];
 const v=register(async url=>{calls.push(url);return url.startsWith('./')?waiting.promise:ok(indexPage([indexRow(record,projection)]));});
 await tick();assert.match(v.filter.describe(record),/testo completo/);
 assert.match(v.panel.querySelector('#register-processing-status').textContent,/Caricamento delle sintesi/);
 assert.equal(calls.length,2);waiting.resolve(ok({}));await tick();
 assert.match(v.filter.describe(record),/Sintesi disponibile/);
});

test('filter changes during automatic loading do not duplicate index requests',async()=>{
 const waiting=deferred();let calls=0;
 const v=register(async url=>url.startsWith('./')?ok({}):(calls++,waiting.promise));
 const mode=v.controls.querySelector('#register-processing-filter');mode.value='ai';mode.fire('change');
 v.controls.querySelector('#register-framework-filter').fire('change');v.controls.fire('reset');
 assert.equal(calls,1);waiting.resolve(ok(indexPage([indexRow(record,projection)])));await tick();
 mode.value='ai_full_text';mode.fire('change');assert.equal(v.filter.matches(record),true);assert.equal(calls,1);
});

test('automatic index failure exposes retry without zero research counts or retry loops',async()=>{
 let failed=true,calls=0;
 const v=register(async url=>{if(url.startsWith('./'))return ok({});calls++;if(failed)throw Error('offline');return ok(indexPage([indexRow(record,projection)]));});
 await tick();assert.equal(calls,1);assert.equal(v.button.hidden,false);assert.equal(v.panel.open,true);
 assert.equal(v.panel.querySelector('#register-completion-status').hidden,true);
 v.controls.querySelector('#register-processing-filter').fire('change');await tick();assert.equal(calls,1);
 failed=false;v.button.fire('click');assert.equal(v.button.hidden,true);await tick();
 assert.equal(calls,2);assert.equal(v.button.hidden,true);assert.match(v.filter.describe(record),/Analisi AI/);
});

test('synopsis failure offers retry even when analysis loading succeeds',async()=>{
 const v=register(async url=>{if(url.startsWith('./'))throw Error('missing support');return ok(indexPage([indexRow(record,projection)]));});
 await tick();assert.equal(v.button.hidden,false);assert.match(v.filter.describe(record),/Analisi AI/);
});

test('automatic loading traverses all 292 index rows with six bounded requests',async()=>{
 const records=Array.from({length:292},(_,i)=>({...record,id:'CAND-AUTO-'+i}));let calls=0;
 const v=register(async url=>{
  if(url.startsWith('./'))return ok({});calls++;const u=new URL(url),start=Number(u.searchParams.get('cursor'));
  if(start)assert.equal(u.searchParams.get('revision'),'c'.repeat(64));
  return ok(indexPage(records.slice(start,start+50).map(r=>indexRow(r,projection)),{total:292,next:start+50<292?start+50:null}));
 },records);
 await tick();assert.equal(calls,6);assert.equal(records.filter(r=>v.filter.describe(r).includes('Analisi AI')).length,292);
 assert.equal(v.button.hidden,true);
});

test('an empty register does not initiate unnecessary remote reads',async()=>{
 let calls=0;const v=register(async()=>{calls++;throw Error('unexpected');},[]);await tick();
 assert.equal(calls,0);assert.equal(v.button.hidden,true);assert.match(v.panel.textContent,/registro vuoto/);
});

test('statistics load automatically and skip the synopsis dataset they never use',async()=>{
 const calls=[];const v=statistics(async url=>{calls.push(url);return ok(url.startsWith('./')?{schemaVersion:1,records:[record]}:indexPage([indexRow(record,projection)]));});
 assert.equal(v.button.hidden,true);assert.equal(v.counts.hidden,true);await tick();
 assert.equal(calls.length,2);assert.ok(!calls.includes('./paper-support.json'));
 assert.equal(v.counts.hidden,false);assert.match(v.counts.textContent,/Analisi dettagliate: 1/);assert.equal(v.button.hidden,true);
});

test('statistics automatic failure stays unknown; one retry recovers and hides the button',async()=>{
 let failed=true;const v=statistics(async url=>{if(failed)throw Error('offline');return ok(url.startsWith('./')?{schemaVersion:1,records:[record]}:indexPage([indexRow(record,projection)]));});
 await tick();assert.equal(v.counts.hidden,true);assert.equal(v.button.hidden,false);assert.match(v.status.textContent,/Impossibile/);
 failed=false;v.button.fire('click');assert.equal(v.button.hidden,true);await tick();
 assert.equal(v.button.hidden,true);assert.match(v.counts.textContent,/Analisi dettagliate: 1/);
});

test('observed zero remains distinct from not loaded after a successful automatic read',async()=>{
 const v=statistics(async url=>ok(url.startsWith('./')?{schemaVersion:1,records:[record]}:indexPage([indexRow(record)])));
 await tick();assert.equal(v.counts.hidden,false);assert.match(v.counts.textContent,/Analisi dettagliate: 0/);assert.equal(v.button.hidden,true);
});

test('partial index coverage does not certify the whole register',async()=>{
 const v=register(async url=>ok(url.startsWith('./')?{}:indexPage([indexRow(record,projection)])),[record,{...record,id:'CAND-OTHER'}]);
 await tick();assert.equal(v.button.hidden,false);assert.match(v.panel.textContent,/1 di 2/);
 assert.match(v.panel.querySelector('#register-completion-status').textContent,/su 1 paper/);
});

test('all HTML menus and public footer links omit the AML tab; historical collection data remain',()=>{
 const site=new URL('../../site/',import.meta.url);
 for(const file of fs.readdirSync(site).filter(f=>f.endsWith('.html'))){
  const html=fs.readFileSync(new URL(file,site),'utf8');assert.doesNotMatch(html,/<a\b[^>]*href="[^"]*aml\.html"[^>]*>\s*Raccolta AML\s*<\/a>/i,file);
 }
 for(const file of ['aml.html','data/secondary-collections.json','data/secondary-collections.csv'])assert.ok(fs.existsSync(new URL(file,site)));
});

test('entry assets use a new cache key and method explains automatic reading',()=>{
 for(const file of ['index.html','stats.html'])assert.match(fs.readFileSync(new URL('../../site/'+file,import.meta.url),'utf8'),/paper-register\.js\?v=frontend-20260917-nav2-status-auto/);
 assert.match(fs.readFileSync(new URL('../../site/method.html',import.meta.url),'utf8'),/caricate automaticamente all’apertura/);
});
