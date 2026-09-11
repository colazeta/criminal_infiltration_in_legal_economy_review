import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {sqliteAdapter, privateTextStore} from '../src/enrichment-store.js';
import {syncTargets, runEnrichment} from '../src/paper-enrichment.js';

function fixture(t) {
  const db=new DatabaseSync(':memory:');
  t.after(()=>db.close());
  db.exec('PRAGMA foreign_keys=ON');
  db.exec(readFileSync(new URL('../migrations/0003_paper_enrichment.sql',import.meta.url),'utf8'));
  const kv=new Map();
  const storage={
    sql:{exec(sql,...values){return {toArray:()=>db.prepare(sql).all(...values)};}},
    transactionSync(fn){db.exec('BEGIN');try{const result=fn();db.exec('COMMIT');return result;}catch(error){db.exec('ROLLBACK');throw error;}},
    async get(key){return Array.isArray(key)?new Map(key.filter(k=>kv.has(k)).map(k=>[k,kv.get(k)])):kv.get(key);},
    async put(key,value){if(typeof key==='string')kv.set(key,value);else for(const [k,v]of Object.entries(key))kv.set(k,v);},
    async transaction(fn){return fn(storage);}
  };
  return {db, env:{PAPER_ENRICHMENT_ENABLED:'true',REVIEW_DB:sqliteAdapter(storage),REVIEW_EVIDENCE:privateTextStore(storage)}};
}
const start=Date.parse('2026-09-11T10:00:00Z');
const identified={id:'CAND-SYNTHETIC-IDENTIFIED',title:'Synthetic identified work',doi:'10.9999/synthetic',sourceLinks:[]};
const unresolved={id:'CAND-SYNTHETIC-UNRESOLVED',title:'Synthetic unresolved work',doi:'',sourceLinks:[]};
const registry={schemaVersion:1,records:[unresolved,identified]};

test('due DOI-ready work precedes an older unresolved target without dropping that target',async t=>{
  const {db,env}=fixture(t);await syncTargets(env,registry,start);
  db.prepare("UPDATE enrichment_jobs SET due_at=? WHERE target_id=(SELECT target_id FROM enrichment_targets WHERE record_id=?)").run(new Date(start-3600000).toISOString(),unresolved.id);
  let calls=0;
  const receipt=await runEnrichment(env,{now:start,registry,fetcher:async()=>{
    calls++;return Response.json({message:{DOI:identified.doi,title:[identified.title],abstract:'Synthetic source only.'}});
  }});
  assert.equal(receipt.status,'completed');assert.equal(calls,1);
  assert.equal(db.prepare('SELECT COUNT(*) n FROM enrichment_targets').get().n,2);
  assert.equal(db.prepare("SELECT COUNT(*) n FROM enrichment_jobs j JOIN enrichment_targets t USING(target_id) WHERE t.record_id=? AND j.kind IN ('metadata','citations') AND j.status='pending'").get(unresolved.id).n,2);
  assert.equal(db.prepare('SELECT COUNT(*) n FROM enrichment_proposals').get().n,0);
});

test('preference never runs a DOI-ready job before due time or invents a missing identifier',async t=>{
  const {db,env}=fixture(t);await syncTargets(env,registry,start);
  db.prepare("UPDATE enrichment_jobs SET due_at=? WHERE target_id=(SELECT target_id FROM enrichment_targets WHERE record_id=?)").run(new Date(start+3600000).toISOString(),identified.id);
  const receipt=await runEnrichment(env,{now:start,registry,fetcher:async()=>{assert.fail('No provider request is due');}});
  assert.equal(receipt.status,'failed');assert.equal(receipt.error_code,'identifier_resolution_required');
  assert.equal(JSON.parse(db.prepare('SELECT record_json FROM enrichment_targets WHERE record_id=?').get(unresolved.id).record_json).doi,'');
  assert.equal(db.prepare('SELECT COUNT(*) n FROM enrichment_sources').get().n,0);
});
