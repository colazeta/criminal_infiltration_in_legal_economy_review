import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {retainedCrossrefReferences,referenceSnapshot} from '../src/crossref-references.js';
import {syncTargets,saveSource,runEnrichment} from '../src/paper-enrichment.js';
const now = Date.parse('2026-09-11T16:00:00Z');
const record = {id:'CAND-REFERENCE-FIXTURE',title:'Synthetic citation fixture',doi:'10.1234/test',sourceLinks:['https://example.org/test']};
const registry = {schemaVersion:1,records:[record]};
async function fixture(t, reference, count) {
  const sqlite = new DatabaseSync(':memory:'); t.after(() => sqlite.close()); sqlite.exec('PRAGMA foreign_keys=ON');
  sqlite.exec(readFileSync(new URL('../migrations/0003_paper_enrichment.sql',import.meta.url),'utf8'));
  const db={prepare(sql){let args=[];return{bind(...values){args=values;return this;},async first(){return sqlite.prepare(sql).get(...args)||null;},async all(){return{results:sqlite.prepare(sql).all(...args)};},async run(){return{meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};},
    async batch(list){sqlite.exec('BEGIN');try{const out=[];for(const item of list)out.push(await item.run());sqlite.exec('COMMIT');return out;}catch(error){sqlite.exec('ROLLBACK');throw error;}}};
  const objects=new Map(),env={PAPER_ENRICHMENT_ENABLED:'true',CURATOR_LOGIN:'owner',REVIEW_DB:db,
    REVIEW_EVIDENCE:{async put(key,text){objects.set(key,text);},async get(key){return objects.has(key)?{async text(){return objects.get(key);}}:null;}}};
  await syncTargets(env,registry,now);
  const target=sqlite.prepare('SELECT * FROM enrichment_targets').get();
  const message={DOI:record.doi,title:[record.title]};
  if(reference!==undefined)message.reference=reference;
  if(count!==undefined)message['reference-count']=count;
  const id=await saveSource(env,target,{provider:'Crossref',evidence_kind:'metadata',text:JSON.stringify(message),source_url:'https://api.crossref.org/works/10.1234%2Ftest'},now);
  return{sqlite,db,env,target,id,objects};
}

test('retained references produce directed private DOI observations without network or corpus writes',async t=>{
  const f=await fixture(t,[{DOI:'10.7777/A'},{DOI:'https://doi.org/10.7777/B'}],2);
  const cp=await retainedCrossrefReferences(f.env,f.target,null,now);
  assert.equal(cp.done,true);assert.equal(cp.coverage_status,'provider_complete');
  const edges=f.sqlite.prepare('SELECT * FROM enrichment_citation_observations ORDER BY cited_identifier').all();
  assert.equal(edges.length,2);assert.equal(edges[0].citing_identifier,'doi:10.1234/test');
  assert.equal(edges[0].cited_identifier,'doi:10.7777/a');assert.equal(edges[0].provider,'Crossref');
  assert.equal(edges[0].direction,'outgoing');assert.equal(f.sqlite.prepare('SELECT COUNT(*) n FROM enrichment_targets').get().n,1);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) n FROM enrichment_proposals').get().n,0);
});

test('reference paging is bounded, idempotent and retains unresolved entries in original evidence',async t=>{
  const refs=Array.from({length:205},(_,i)=>({DOI:'10.7777/'+i}));refs.push({unstructured:'Unresolved fixture'});
  const f=await fixture(t,refs,206);
  let cp=await retainedCrossrefReferences(f.env,f.target,null,now);
  assert.equal(cp.offset,100);assert.equal(cp.done,false);assert.equal(cp.unresolved_entries,1);
  await retainedCrossrefReferences(f.env,f.target,null,now+1);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) n FROM enrichment_citation_observations').get().n,100);
  cp=await retainedCrossrefReferences(f.env,f.target,cp,now+2);assert.equal(cp.offset,200);
  cp=await retainedCrossrefReferences(f.env,f.target,cp,now+3);
  assert.equal(cp.done,true);assert.equal(cp.coverage_status,'partial');assert.equal(cp.offset,206);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) n FROM enrichment_citation_observations').get().n,205);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) n FROM enrichment_citation_coverage').get().n,3);
  assert.ok([...f.objects.values()].some(text=>text.includes('Unresolved fixture')));
});

test('missing lists, measured zeros and unconfirmed totals are distinguished',async t=>{
  for(const [refs,count,expected] of [[undefined,undefined,'not_returned'],[[],0,'provider_complete'],[[],9,'partial'],[[{DOI:'10.7777/a'}],undefined,'partial']]) {
    const f=await fixture(t,refs,count);
    const cp=await retainedCrossrefReferences(f.env,f.target,null,now);
    assert.equal(cp.coverage_status,expected);
  }
});

test('metadata hash and target identity are verified before any derived write',async t=>{
  const f=await fixture(t,[{DOI:'10.7777/a'}],1),key=[...f.objects.keys()][0];
  f.objects.set(key,'modified');
  await assert.rejects(retainedCrossrefReferences(f.env,f.target,null,now),/source_integrity/);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) n FROM enrichment_citation_observations').get().n,0);
  assert.throws(()=>referenceSnapshot({DOI:'10.8888/other'},record.doi),/identity_conflict/);
});

test('a source checkpoint cannot cross input versions and invalid cursors never become success',async t=>{
  const f=await fixture(t,[{DOI:'10.7777/a'}],1);
  await assert.rejects(retainedCrossrefReferences(f.env,{...f.target,input_sha256:'b'.repeat(64)},{source_id:f.id},now),/source_unavailable/);
  await assert.rejects(retainedCrossrefReferences(f.env,f.target,{source_id:f.id,offset:2},now),/cursor_invalid/);
});

test('invalid reference arrays and excessive lists are rejected before partial writes',()=>{
  assert.throws(()=>referenceSnapshot({DOI:record.doi,reference:{}},record.doi),/payload_invalid/);
  assert.throws(()=>referenceSnapshot({DOI:record.doi,reference:Array(20001).fill({})},record.doi),/payload_limit/);
  const parsed=referenceSnapshot({DOI:record.doi,reference:[{DOI:'invalid'},null,{DOI:'10.7777/a'}]},record.doi);
  assert.equal(parsed.unresolved,2);assert.equal(parsed.returned,3);
});

test('existing references persist when the next independent provider is rate limited',async t=>{
  const f=await fixture(t,[{DOI:'10.7777/a'}],1);
  f.sqlite.exec("UPDATE enrichment_jobs SET status='blocked' WHERE kind='metadata'");
  let calls=0;
  const fetcher=async()=>{calls++;return new Response('',{status:429,headers:{'Retry-After':'3600'}});};
  let result=await runEnrichment(f.env,{now,registry,fetcher});
  assert.equal(result.status,'partial');assert.equal(calls,0);
  result=await runEnrichment(f.env,{now:now+3600000,registry,fetcher});
  assert.equal(result.status,'failed');assert.equal(result.error_code,'rate_limited');assert.equal(calls,1);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) n FROM enrichment_citation_observations').get().n,1);
  assert.equal(JSON.parse(f.sqlite.prepare("SELECT checkpoint_json FROM enrichment_jobs WHERE kind='citations'").get().checkpoint_json).crossref_done,true);
});
