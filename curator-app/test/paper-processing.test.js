import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {indexRow,indexPage} from './index-fixture.js';

const source = fs.readFileSync(new URL('../../site/paper-register.js', import.meta.url), 'utf8');
function api(extra={}) {
  const context = vm.createContext({AbortController, setTimeout, clearTimeout, URL, document:{querySelector:()=>null}, ...extra});
  vm.runInContext(source, context);
  return context.CILEPaperProcessing;
}
const A = api();
const candidate = {id:'candidate-a', title:'Synthetic title', doi:'10.1234/example', sourceLinks:['https://example.org/paper']};
const projection = (changes={}) => ({availability:'available', research:{assessment_state:'unreviewed_proposal', generation_kind:'automated', source_coverage:'full_text', updated_at:'2026-09-13T19:00:00Z', framework:{status:'proposed', primary:'screening', secondary:[{category:'diagnosis'}], alternative:'prognosis'}, ...changes}});
const identity = (payload, record) => { assert.equal(payload.candidateId, record.id); return payload; };
const dependencies = (read, extra={}) => ({read, selectSupport:(p,r) => { if (!p.records[r.id]) throw Error('missing'); return p.records[r.id]; }, selectResearch:identity, ...extra});
const support = (kind='review_synopsis', synopsis='Source-grounded summary') => ({readingAid:{kind,synopsis}});

for (const coverage of ['abstract_only','partial_text','full_text']) {
  test(`AI filter retains actual ${coverage} consultation coverage`, () => {
    const row = A.researchState(projection({source_coverage:coverage}));
    assert.equal(A.matches(row, 'ai'), true);
    assert.equal(A.matches(row, 'ai_' + coverage), true);
    for (const other of ['abstract_only','partial_text','full_text'].filter(x => x !== coverage)) assert.equal(A.matches(row, 'ai_' + other), false);
  });
}

test('unspecified production is content, not proof of AI or human review', () => {
  const row = A.researchState(projection({generation_kind:'unspecified'}));
  assert.equal(A.matches(row,'ai'),false);
  assert.equal(A.matches(row,'content'),true);
  assert.match(A.describe(row), /origine non attestata/);
});

test('recorded primary and secondary match, an alternative does not', () => {
  const row = A.researchState(projection());
  assert.equal(A.matches(row,'ai','screening'),true);
  assert.equal(A.matches(row,'ai','diagnosis'),true);
  assert.equal(A.matches(row,'ai','prognosis'),false);
  assert.equal(A.matches(row,'ai','therapy'),false);
});

for (const abstention of ['insufficient_evidence','outside_framework']) {
  test(`${abstention} is processed but is not a seventh class`, () => {
    const row = A.researchState(projection({framework:{status:abstention,primary:null,secondary:[],alternative:null}}));
    assert.equal(A.matches(row,'ai'),true);
    assert.equal(A.matches(row,'ai','screening'),false);
    assert.equal(row.classes.length,0);
  });
}

for (const availability of ['not_assessed','not_registered','stale','withheld']) {
  test(`${availability} cannot imply current AI analysis`, () => {
    const row = A.researchState({availability,research:null});
    assert.equal(A.matches(row,'ai'),false);
    assert.equal(A.matches(row,'content'),false);
  });
}

test('invalid and confirmed payloads fail closed', () => {
  assert.throws(() => A.researchState(projection({assessment_state:'confirmed'})));
  assert.throws(() => A.researchState(projection({source_coverage:'unknown'})));
  assert.throws(() => A.researchState(projection({framework:{status:'proposed',primary:'invented',secondary:[]}})));
  assert.throws(() => A.researchState({availability:'not_assessed',research:{}}));
  assert.equal(A.matches(null,'invented'),false);
});

test('actual summaries count, metadata warnings and empty strings do not', async () => {
  const records = Array.from({length:6}, (_,i) => ({...candidate,id:'c'+i}));
  const values = [support(),support('metadata_warning'),support('review_synopsis','  '),{abstract:{status:'available'},retrieval:{status:'full_text'}},support('full_text_intro'),support('publisher_summary')];
  const index = A.createIndex(records, dependencies(async () => ({records:Object.fromEntries(records.map((r,i) => [r.id,values[i]]))})));
  await index.loadSupport();
  assert.deepEqual(records.map(r => A.matches(index.rows.get(r.id),'summary')), [true,false,false,false,true,true]);
  assert.equal([...index.rows.values()].some(r => A.matches(r,'ai')),false);
});

test('matching candidate identity is required for every research response', async () => {
  const index = A.createIndex([candidate], dependencies(async url => url.startsWith('./') ? {records:{[candidate.id]:support()}} : indexPage([indexRow({...candidate,title:'Other identity'},projection())])));
  await index.scan();
  assert.equal(index.rows.get(candidate.id).research,'error');
  assert.equal(A.matches(index.rows.get(candidate.id),'ai'),false);
  assert.equal(index.progress.checked,0);
});

test('support identity failures do not become a missing summary assertion', async () => {
  const index = A.createIndex([candidate], dependencies(async () => ({records:{}})));
  await index.loadSupport();
  assert.equal(index.rows.get(candidate.id).support,'error');
  assert.equal(A.matches(index.rows.get(candidate.id),'unavailable'),true);
});

test('transport failure preserves explicit uncertainty', async () => {
  const index = A.createIndex([candidate], dependencies(async () => { throw Error('offline'); }));
  await index.scan();
  const row = index.rows.get(candidate.id);
  assert.equal(row.support,'error'); assert.equal(row.research,'pending');
  assert.equal(index.progress.checked,0); assert.equal(index.progress.errors,1);
  assert.equal(A.matches(row,'content'),false);
  assert.match(A.describe(row), /non verificabile/);
});

test('reads are credential-free, no-store and bounded by an abort signal', async () => {
  let options;
  const output = await A.readJSON('https://example.org/public', async (_url,o) => { options=o; return {ok:true,json:async () => ({ok:1})}; });
  assert.equal(output.ok,1); assert.equal(options.credentials,'omit'); assert.equal(options.cache,'no-store');
  assert.ok(options.signal instanceof AbortSignal);
});

test('bad HTTP status fails instead of supplying zero analysis', async () => {
  await assert.rejects(() => A.readJSON('https://example.org/public', async () => ({ok:false})), /unavailable/);
});

test('one index request replaces fifteen paper requests without overlapping scans', async () => {
  const records = Array.from({length:15}, (_,i) => ({...candidate,id:'c'+i}));
  let active=0, max=0, requests=0;
  const index = A.createIndex(records, dependencies(async url => {
    if (url.startsWith('./')) return {records:Object.fromEntries(records.map(r => [r.id,{readingAid:null}]))};
    active++; requests++; max=Math.max(max,active);
    await new Promise(resolve => setTimeout(resolve,2)); active--;
    assert.equal(new URL(url).searchParams.get('view'),'index');
    return indexPage(records.map(r=>indexRow(r,projection())));
  }));
  const one=index.scan(), two=index.scan(); assert.equal(one,two);
  await one;
  assert.equal(max,1); assert.equal(requests,1); assert.equal(index.progress.checked,15);
  assert.equal(index.progress.running,false);
});

test('service-wide failure stops opening requests and leaves unchecked records unknown', async () => {
  const records = Array.from({length:40}, (_,i) => ({...candidate,id:'c'+i}));
  const index = A.createIndex(records, dependencies(async url => {
    if (url.startsWith('./')) return {records:Object.fromEntries(records.map(r => [r.id,{readingAid:null}]))};
    throw Error('service unavailable');
  }));
  await index.scan();
  assert.ok(index.progress.attempted<=7);
  assert.ok(index.progress.attempted<records.length);
  assert.equal(index.progress.checked,0);
  assert.ok([...index.rows.values()].some(r => r.research==='pending'));
});

test('refresh observes changed content at the same record count and clears old positives on failure', async () => {
  let mode=0;
  const index = A.createIndex([candidate], dependencies(async url => {
    if (url.startsWith('./')) return {records:{[candidate.id]:{readingAid:null}}};
    if (mode===2) throw Error('offline');
    return indexPage([indexRow(candidate,projection({source_coverage:mode===0?'abstract_only':'full_text'}))]);
  }));
  await index.scan(); assert.equal(A.matches(index.rows.get(candidate.id),'ai_full_text'),false);
  mode=1; await index.scan(); assert.equal(A.matches(index.rows.get(candidate.id),'ai_full_text'),true);
  mode=2; await index.scan(); assert.equal(A.matches(index.rows.get(candidate.id),'ai'),false);
});

test('duplicate register identity rejects the index', () => {
  assert.throws(() => A.createIndex([candidate,candidate],dependencies(async()=>({}))), /identity/);
});

test('the public register composes existing filters with processing and preserves sheets', () => {
  const register=fs.readFileSync(new URL('../../site/paper-register.js',import.meta.url),'utf8');
  assert.match(register,/processing\.matches\(record\)/);
  assert.match(register,/processing\?\.describe\(record\)/);
  assert.match(register,/processing\?\.emptyMessage\(\)/);
  assert.match(register,/CILEPaperProcessing\.mount/);
  assert.match(register,/CILEPaperResearch\.load\(research, record, isCurrent\)/);
  assert.match(register,/row\.addEventListener\("dblclick"/);
});

function fakeDocument() {
  class Element {
    constructor(tag) {this.tagName=tag; this.children=[]; this.attributes={}; this.listeners={}; this.value=''; this.textContent='';}
    append(...children) {for (const child of children) {this.children.push(child); if(this.tagName==='select' && this.children.length===1) this.value=child.value;}}
    after(node) {this.following=node;}
    setAttribute(key,value) {this.attributes[key]=value;}
    addEventListener(event,listener) {this.listeners[event]=listener;}
    fire(event) {this.listeners[event]?.({target:this});}
  }
  return {querySelector:()=>null,createElement:tag=>new Element(tag)};
}
const tick = () => new Promise(resolve => setImmediate(resolve));

test('mounted controls filter real loaded projections, compose classes and reset', async () => {
  const document=fakeDocument(), controls=document.createElement('form');
  const records=[candidate,{...candidate,id:'candidate-b'}];
  let requestCount=0, redraws=0;
  const mountedAPI=api({document,fetch:async url => {
    if (url.startsWith('./')) return {ok:true,json:async()=>({records:{[candidate.id]:support(),'candidate-b':{readingAid:null}}})};
    requestCount++;
    return {ok:true,json:async()=>indexPage([indexRow(candidate,projection()),indexRow(records[1])])};
  }});
  const filter=mountedAPI.mount({controls,records,onChange:()=>redraws++,selectSupport:dependencies(()=>{}).selectSupport,selectResearch:identity});
  await tick();
  const [mode,category,button]=[controls.children[0].children[0],controls.children[1].children[0],controls.children[2]];
  assert.equal(mode.id,'register-processing-filter'); assert.equal(category.id,'register-framework-filter');
  assert.equal(requestCount,0,'initial view does not issue one request per paper');
  mode.value='summary'; mode.fire('change');
  assert.equal(filter.matches(candidate),true); assert.equal(filter.matches(records[1]),false);
  assert.equal(filter.emptyMessage(),'','fully checked summary filter is not an incomplete research scan');
  mode.value='ai_full_text'; mode.fire('change'); await tick();
  assert.equal(requestCount,1); assert.equal(filter.matches(candidate),true); assert.equal(filter.matches(records[1]),false);
  category.value='diagnosis'; category.fire('change'); assert.equal(filter.matches(candidate),true);
  category.value='prognosis'; category.fire('change'); assert.equal(filter.matches(candidate),false);
  assert.equal(requestCount,1,'changing a filter does not start another completed scan');
  controls.fire('reset'); assert.equal(mode.value,'all'); assert.equal(category.value,'all');
  assert.equal(filter.matches(records[1]),true); assert.equal(button.disabled,false); assert.ok(redraws>0);
  assert.equal(controls.following.children[0].attributes.role,'status');
});

test('mount keeps unavailable responses distinct from unanalysed papers', async () => {
  const document=fakeDocument(),controls=document.createElement('form');
  const mountedAPI=api({document,fetch:async()=>{throw Error('unavailable');}});
  const filter=mountedAPI.mount({controls,records:[candidate],onChange:()=>{},selectSupport:dependencies(()=>{}).selectSupport,selectResearch:identity});
  await tick();
  const mode=controls.children[0].children[0];mode.value='ai';mode.fire('change');await tick();
  assert.equal(filter.matches(candidate),false);
  assert.match(filter.emptyMessage(),/non è completa/);
  assert.match(controls.following.children[0].textContent,/Verifica incompleta/);
});

test('all six current contribution classes are supported and no topic code substitutes for them', () => {
  for(const primary of ['aetiology','diagnosis','screening','therapy','prognosis','prevention']) {
    const row=A.researchState(projection({framework:{status:'proposed',primary,secondary:[],alternative:null}}));
    assert.equal(A.matches(row,'ai',primary),true);
  }
  assert.equal(A.matches({research:'not_assessed',summary:false,classes:[],topicCode:'screening'},'all','screening'),false);
});

test('refresh button reloads analysis without a new candidate or a new page build', async () => {
  const document=fakeDocument(),controls=document.createElement('form'); let coverage='abstract_only';
  const mountedAPI=api({document,fetch:async url=>({ok:true,json:async()=>url.startsWith('./')?{records:{[candidate.id]:support()}}:indexPage([indexRow(candidate,projection({source_coverage:coverage}))])})});
  const filter=mountedAPI.mount({controls,records:[candidate],onChange:()=>{},selectSupport:dependencies(()=>{}).selectSupport,selectResearch:identity});
  await tick();const mode=controls.children[0].children[0];mode.value='ai_full_text';mode.fire('change');await tick();
  assert.equal(filter.matches(candidate),false);
  coverage='full_text';controls.children[2].fire('click');await tick();
  assert.equal(filter.matches(candidate),true);
});


test('multiple index pages have bounded requests, stable identity and one revision',async()=>{
 const records=Array.from({length:121},(_,i)=>({...candidate,id:'CAND-PAGE-'+i}));let requests=0;
 const index=A.createIndex(records,dependencies(async url=>{
  if(url.startsWith('./'))return{records:Object.fromEntries(records.map(r=>[r.id,{readingAid:null}]))};
  const u=new URL(url),offset=Number(u.searchParams.get('cursor'));requests++;
  if(offset)assert.equal(u.searchParams.get('revision'),'c'.repeat(64));
  return indexPage(records.slice(offset,offset+50).map(r=>indexRow(r,projection())),{total:records.length,next:offset+50<records.length?offset+50:null});
 }));
 await index.scan();assert.equal(requests,3);assert.equal(index.progress.checked,121);assert.equal(index.progress.errors,0);
});
test('a changed index restarts once; repeated changes preserve unknowns and do not loop',async()=>{
 const records=[candidate];let calls=0;
 const index=A.createIndex(records,dependencies(async url=>{
  if(url.startsWith('./'))return{records:{[candidate.id]:support()}};
  calls++;throw Object.assign(Error('index_changed'),{status:409});
 }));
 await index.scan();assert.equal(calls,2);assert.equal(index.progress.checked,0);assert.equal(index.progress.errors,1);assert.equal(A.isCompleted(index.rows.get(candidate.id)),false);
});
test('accepted backend completion is identical across filters and rejects mismatched revisions',()=>{
 const row=indexRow(candidate,projection(),true),state=A.indexState(row,candidate);
 assert.equal(A.isCompleted(state),true);assert.equal(A.matches(state,'completed'),true);
 row.completion.research_revision='d'.repeat(64);assert.throws(()=>A.indexState(row,candidate),/revision/);
 assert.equal(A.isCompleted({...A.researchState(projection()),completed:true,approved:true}),false);
});
test('outside-framework completion does not create or require a seventh contribution class',()=>{
 const row=indexRow(candidate,projection({framework:{status:'outside_framework',primary:null,secondary:[],alternative:null}}),true),state=A.indexState(row,candidate);
 assert.equal(A.matches(state,'completed'),true);assert.equal(state.classes.length,0);assert.equal(A.matches(state,'completed','diagnosis'),false);
});
test('incomplete pagination cannot certify a complete scan',async()=>{
 const index=A.createIndex([candidate],dependencies(async url=>url.startsWith('./')?{records:{[candidate.id]:support()}}:indexPage([],{total:1})));
 await index.scan();assert.equal(index.progress.checked,0);assert.equal(index.progress.errors,1);
});
