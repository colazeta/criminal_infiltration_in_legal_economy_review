import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import migration from '../src/enrichment-migration.json' with {type:'json'};
import {EnrichmentStoreCore,sqliteAdapter,privateTextStore,serviceSignature,enrichmentStore} from '../src/enrichment-store.js';
import {sha256} from '../src/review-v2.js';
const secret='test-only-secret-never-used-in-production-0123456789';
function setup(){
 const db=new DatabaseSync(':memory:');db.exec('PRAGMA foreign_keys=ON');const kv=new Map();
 const storage={sql:{exec(sql,...v){let rows=[];if(sql.includes('CREATE TABLE enrichment_targets'))db.exec(sql);else rows=db.prepare(sql).all(...v);return{toArray:()=>rows}}},
  transactionSync(fn){db.exec('BEGIN');try{const out=fn();db.exec('COMMIT');return out}catch(e){db.exec('ROLLBACK');throw e}},
  async get(k){return Array.isArray(k)?new Map(k.filter(x=>kv.has(x)).map(x=>[x,kv.get(x)])):kv.get(k)},
  async put(k,v){if(typeof k==='string')kv.set(k,v);else for(const[key,value]of Object.entries(k))kv.set(key,value)},
  async delete(k){for(const key of [k].flat())kv.delete(key)},
  async list({prefix,limit}){return new Map([...kv].filter(([k])=>k.startsWith(prefix)).sort().slice(0,limit))},
  async transaction(fn){const before=new Map(kv);db.exec('BEGIN');try{const out=await fn(storage);db.exec('COMMIT');return out}catch(e){db.exec('ROLLBACK');kv.clear();for(const[k,v]of before)kv.set(k,v);throw e}}
 };
 const env={SESSION_SECRET:secret,DEPLOY_COMMIT:'abc',CURATOR_LOGIN:'colazeta',PAPER_ENRICHMENT_ENABLED:'true'};
 const ctx={storage,blockConcurrencyWhile:fn=>fn()},core=new EnrichmentStoreCore(ctx,env);
 return{db,kv,storage,ctx,env,core};
}
async function request(data,now=Date.now(),key=secret){const body=JSON.stringify({expected_commit:'abc',...data}),ts=String(now),nonce=crypto.randomUUID();return new Request('https://enrichment.internal/machine',{method:'POST',body,headers:{'Content-Type':'application/json','X-Enrichment-Timestamp':ts,'X-Enrichment-Nonce':nonce,'X-Enrichment-Signature':await serviceSignature(key,ts,nonce,body)}})}
test('bundled migration is byte-identical to the normative additive SQL',async()=>{const text=readFileSync(new URL('../migrations/0003_paper_enrichment.sql',import.meta.url),'utf8');assert.equal(migration.sql,text);assert.equal(await sha256(text),migration.sha256)});
test('Durable Object initialises only enrichment tables and is inactive until readback activation',async()=>{const{core,db}=setup();await core.ready;assert.equal((await core.environment()).PAPER_ENRICHMENT_ENABLED,'false');assert.equal(db.prepare("SELECT COUNT(*) n FROM sqlite_master WHERE type='table'").get().n,15);assert.equal((await core.verify()).verified,true)});
test('database adapter preserves atomic proposal transactions and change counts',async()=>{const{core,db,storage}=setup();await core.ready;const a=sqliteAdapter(storage);const sql='INSERT INTO enrichment_targets VALUES (?,?,?,?,?,?,1,?,?)';const stmt=a.prepare(sql).bind('t','c','candidate','r','a'.repeat(64),'{}','now','now');await assert.rejects(a.batch([stmt,stmt]));assert.equal(db.prepare('SELECT COUNT(*) n FROM enrichment_targets').get().n,0);assert.equal((await stmt.run()).meta.changes,1);assert.equal((await a.prepare('UPDATE enrichment_targets SET active=0 WHERE target_id=?').bind('absent').run()).meta.changes,0)});
test('private content larger than a single KV value is chunked and read back intact',async()=>{const{storage}=setup(),store=privateTextStore(storage),text='α😀'.repeat(400000);await store.put('a',text);assert.equal(await(await store.get('a')).text(),text);await store.put('a',text);await assert.rejects(store.put('a','altered'),/immutable/)});
test('missing chunks and tampering are rejected, not returned as source evidence',async()=>{const{storage,kv}=setup(),store=privateTextStore(storage);await store.put('a','Evidence');kv.set('evidence:a:0','altered');await assert.rejects(store.get('a'),/integrity/);kv.delete('evidence:a:0');await assert.rejects(store.get('a'),/incomplete/)});
test('unsigned, expired, wrong-key and replayed machine requests cannot access private data',async()=>{const{core}=setup();await core.ready;assert.equal((await core.machine(new Request('https://enrichment.internal/machine',{method:'POST',body:'{}',headers:{'Content-Type':'application/json'}}))).status,401);assert.equal((await core.machine(await request({operation:'status'},Date.now()-180000))).status,401);assert.equal((await core.machine(await request({operation:'status'},Date.now(),'different-secret-string-longer-than-thirty-two'))).status,401);const r=await request({operation:'status'}),copy=r.clone();assert.equal((await core.machine(r)).status,200);assert.equal((await core.machine(copy)).status,401)});
test('activation requires exact deployment and storage check; disabling/redeployment fail closed',async()=>{const{core,env}=setup();await core.ready;assert.equal((await core.machine(await request({operation:'activate',expected_commit:'stale'}))).status,409);assert.equal((await core.machine(await request({operation:'activate'}))).status,200);assert.equal((await core.environment()).PAPER_ENRICHMENT_ENABLED,'true');env.PAPER_ENRICHMENT_ENABLED='false';assert.equal((await core.environment()).PAPER_ENRICHMENT_ENABLED,'false');env.PAPER_ENRICHMENT_ENABLED='true';env.DEPLOY_COMMIT='changed';assert.equal((await core.environment()).PAPER_ENRICHMENT_ENABLED,'false')});
test('machine interface is closed and cannot execute arbitrary SQL or publish',async()=>{const{core}=setup();await core.ready;for(const data of [{operation:'sql',sql:'DROP TABLE x'},{operation:'publish'}])assert.equal((await core.machine(await request(data))).status,422)});
test('provider or model credentials do not choose the storage backend implicitly',()=>{assert.equal(enrichmentStore({}),null);assert.equal(enrichmentStore({PAPER_ENRICHMENT_STORAGE:'d1_r2',ENRICHMENT_STORE:{}}),null)});
test('a changed migration receipt stops initialisation without rewriting data',async()=>{const{core,ctx,env,kv}=setup();await core.ready;kv.set('schema:enrichment','other');await assert.rejects(new EnrichmentStoreCore(ctx,env).ready,/additive_migration_required/)});
