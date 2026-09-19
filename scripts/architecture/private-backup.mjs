/* No plaintext backup, source body, key, request or raw error is logged/uploaded.
   The encrypted artifact can be restored with the same protected session secret;
   retain the old secret through the backup retention period when rotating it. */
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {BACKUP_CONTRACT,openBackupPage,decodeStored,digestRows} from '../../curator-app/src/archive-preservation.js';
import {EnrichmentStoreCore,serviceSignature} from '../../curator-app/src/enrichment-store.js';
import {ARCHIVE_TABLES,auditArchitecture} from '../../curator-app/src/architecture-audit.js';
import {canonicalJson,sha256} from '../../curator-app/src/review-v2.js';

const ORIGIN='https://criminal-infiltration-curator.colazeta-research.workers.dev';
const assert=(condition)=>{if(!condition)throw Error('archive_preservation_gate_failed')};
const same=(a,b)=>canonicalJson(a)===canonicalJson(b);
const digest=value=>sha256(canonicalJson(value));
const kvDigest=entries=>digest([...entries].sort(([a],[b])=>a<b?-1:a>b?1:0));

function restoreTableOrder(db){
  // Keep every physical guard enabled; trigger dependencies supplement the FKs.
  const triggerDependencies={
    enrichment_variable_datasets:['enrichment_analysis_datasets'],
    enrichment_normalization_receipts:['enrichment_facts','enrichment_fact_evidence'],
  };
  const remaining=new Map(ARCHIVE_TABLES.map(table=>[table,new Set([
    ...db.prepare(`PRAGMA foreign_key_list(${table})`).all().map(f=>f.table),
    ...(triggerDependencies[table]||[]),
  ].filter(parent=>parent!==table))]));
  const order=[];
  while(remaining.size){
    const ready=[...remaining].filter(([,parents])=>[...parents].every(p=>order.includes(p))).map(([name])=>name);
    assert(ready.length>0);
    for(const table of ready){order.push(table);remaining.delete(table)}
  }
  return order;
}

export function isolatedStore(secret,commit){
  const db=new DatabaseSync(':memory:');db.exec('PRAGMA foreign_keys=ON');
  const kv=new Map();let alarm=null;
  const storage={sql:{exec(sql,...values){let rows=[];if(/CREATE TABLE/.test(sql))db.exec(sql);else rows=db.prepare(sql).all(...values);return{toArray:()=>rows}}},
    transactionSync(fn){db.exec('BEGIN');try{const result=fn();db.exec('COMMIT');return result}catch(error){db.exec('ROLLBACK');throw error}},
    async get(key){return Array.isArray(key)?new Map(key.filter(k=>kv.has(k)).map(k=>[k,kv.get(k)])):kv.get(key)},
    async put(key,value){if(typeof key==='string')kv.set(key,value);else for(const [k,v] of Object.entries(key))kv.set(k,v)},
    async delete(key){for(const k of [key].flat())kv.delete(k)},
    async list({prefix='',startAfter='',limit=1000}={}){return new Map([...kv].filter(([k])=>k.startsWith(prefix)&&k>startAfter).sort(([a],[b])=>a<b?-1:1).slice(0,limit))},
    async transaction(fn){const before=new Map(kv);db.exec('BEGIN');try{const result=await fn(storage);db.exec('COMMIT');return result}catch(error){db.exec('ROLLBACK');kv.clear();for(const [k,v] of before)kv.set(k,v);throw error}},
    async getAlarm(){return alarm},async setAlarm(value){alarm=value}};
  const env={SESSION_SECRET:secret,DEPLOY_COMMIT:commit,CURATOR_LOGIN:'restore-test',PAPER_ENRICHMENT_ENABLED:'false'};
  const core=new EnrichmentStoreCore({storage,blockConcurrencyWhile:fn=>fn()},env);
  return {core,db,kv,storage};
}

async function readKv(getPage,accept=()=>{}){
  let after='';const entries=new Map();
  for(let count=0;count<10000;count++){
    const {page,envelope}=await getPage({part:'kv',after});
    assert(page.part==='kv'&&page.after===after&&Array.isArray(page.entries));
    for(const [key,value] of page.entries){assert(typeof key==='string'&&key>after&&!entries.has(key)&&!key.startsWith('nonce:')&&!key.startsWith('probe:'));decodeStored(value);entries.set(key,value)}
    accept(envelope);if(page.next===null)return entries;
    assert(typeof page.next==='string'&&page.next>after);after=page.next;
  }
  throw Error('archive_preservation_gate_failed');
}

export async function captureBackup(call,secret,commit,snapshot_id=crypto.randomUUID()){
  const pages=[];let total=0;
  const accept=envelope=>{total+=JSON.stringify(envelope).length;assert(total<=300000000);pages.push(envelope)};
  const getPage=async request=>{const envelope=await call({...request,snapshot_id});return{envelope,page:await openBackupPage(envelope,secret,commit,snapshot_id)}};
  const first=await getPage({part:'catalogue'}),catalogue=first.page;
  assert(catalogue.part==='catalogue'&&same(Object.keys(catalogue.counts).sort(),ARCHIVE_TABLES));accept(first.envelope);
  for(const table of ARCHIVE_TABLES){
    const count=catalogue.counts[table];assert(Number.isSafeInteger(count)&&count>=0&&count<=100000);
    const all=[];
    for(let offset=0;offset<count;offset+=100){
      const {page,envelope}=await getPage({part:'sql',table,offset});
      assert(page.part==='sql'&&page.table===table&&page.offset===offset&&page.rows.length===Math.min(100,count-offset));
      all.push(...page.rows);accept(envelope);
    }
    assert(await digestRows(all)===catalogue.digests[table]);
  }
  const kv=await readKv(getPage,accept),readback=await readKv(getPage);
  assert(await kvDigest(kv)===await kvDigest(readback));
  const last=await getPage({part:'catalogue'});
  assert(last.page.schema_sha256===catalogue.schema_sha256&&last.page.state_sha256===catalogue.state_sha256);accept(last.envelope);
  const bundle={contract:BACKUP_CONTRACT,commit,snapshot_id,pages};
  // Replay the saved pages through a second independent reading path.
  const receipt=await restoreBackup(bundle,secret);
  return {bundle,receipt:{...receipt,concurrent_change_checked:true,ciphertext_sha256:await digest(bundle)}};
}

export async function restoreBackup(bundle,secret){
  assert(bundle?.contract===BACKUP_CONTRACT&&typeof bundle.commit==='string'&&Array.isArray(bundle.pages)&&bundle.pages.length>=3);
  let cursor=0;
  const next=async()=>{assert(cursor<bundle.pages.length);return openBackupPage(bundle.pages[cursor++],secret,bundle.commit,bundle.snapshot_id)};
  const catalogue=await next();assert(catalogue.part==='catalogue'&&same(Object.keys(catalogue.counts).sort(),ARCHIVE_TABLES));
  const tables={};
  for(const table of ARCHIVE_TABLES){
    const all=[];for(let offset=0;offset<catalogue.counts[table];offset+=100){const page=await next();assert(page.part==='sql'&&page.table===table&&page.offset===offset&&page.rows.length===Math.min(100,catalogue.counts[table]-offset));all.push(...page.rows)}
    assert(all.length===catalogue.counts[table]&&await digestRows(all)===catalogue.digests[table]);tables[table]=all;
  }
  const kv=await readKv(async()=>({page:await next()}));
  const last=await next();assert(cursor===bundle.pages.length&&last.part==='catalogue'&&last.schema_sha256===catalogue.schema_sha256&&last.state_sha256===catalogue.state_sha256);
  const x=isolatedStore(secret,bundle.commit);await x.core.requireReady();
  try{
    x.db.exec('BEGIN');x.db.exec('PRAGMA defer_foreign_keys=ON');
    for(const table of restoreTableOrder(x.db)){
      const columns=x.db.prepare(`PRAGMA table_info(${table})`).all().map(r=>r.name);
      const insert=x.db.prepare(`INSERT INTO ${table} (${columns.join(',')}) VALUES (${columns.map(()=>'?').join(',')})`);
      for(const row of tables[table]){assert(same(Object.keys(row).sort(),[...columns].sort()));insert.run(...columns.map(k=>row[k]))}
    }
    x.db.exec('COMMIT');
    x.kv.clear();for(const [key,value] of kv)x.kv.set(key,decodeStored(value));
    const restarted=new EnrichmentStoreCore({storage:x.storage,blockConcurrencyWhile:fn=>fn()},{SESSION_SECRET:secret,DEPLOY_COMMIT:bundle.commit,CURATOR_LOGIN:'restore-test',PAPER_ENRICHMENT_ENABLED:'false'});
    await restarted.requireReady();const audit=await auditArchitecture(await restarted.environment());
    assert(audit.state_sha256===catalogue.state_sha256&&same(audit.counts,catalogue.counts));
    assert(audit.schema_sha256===catalogue.schema_sha256);
    return {contract:BACKUP_CONTRACT,commit:bundle.commit,scope:'entire_enrichment_store',snapshot_id:bundle.snapshot_id,
      sql_tables:ARCHIVE_TABLES.length,sql_rows:Object.values(catalogue.counts).reduce((a,b)=>a+b,0),kv_entries:kv.size,
      state_sha256:catalogue.state_sha256,kv_sha256:await kvDigest(kv),isolated_restore_verified:true,
      integrity_verified:audit.integrity_verified,issues:audit.issues,checked_public_targets:audit.checked_public_targets,
      public_states:audit.public_states,completion_states:audit.completion_states,
      excluded_transient_prefixes:catalogue.kv_exclusions,other_stores_included:false,
      plaintext_persisted:false,production_restored:false,cutover_ready:false};
  }finally{x.db.close()}
}

async function fetchJSON(url,options={}){
  const response=await fetch(url,{...options,redirect:'error',signal:AbortSignal.timeout(90000)});
  assert(response.ok);const text=await response.text();assert(text.length<10000000);return JSON.parse(text);
}
async function main(){
  const secret=process.env.CURATOR_SESSION_SECRET;assert(typeof secret==='string'&&secret.length>=32);
  if(process.argv[2]==='restore'){
    const receipt=await restoreBackup(JSON.parse(readFileSync(process.argv[3],'utf8')),secret);
    process.stdout.write(JSON.stringify(receipt,null,2)+'\n');return;
  }
  assert(process.argv[2]==='capture'&&process.argv.length===4);
  const {commit}=await fetchJSON(ORIGIN+'/version');assert(/^[a-f0-9]{40}$/.test(commit)&&commit===process.env.GITHUB_SHA);
  const call=async backup=>{
    const body=JSON.stringify({operation:'architecture-backup',expected_commit:commit,backup}),timestamp=String(Date.now()),nonce=crypto.randomUUID();
    return fetchJSON(ORIGIN+'/api/paper-enrichment-machine',{method:'POST',body,headers:{'Content-Type':'application/json','Accept':'application/json',
      'X-Enrichment-Timestamp':timestamp,'X-Enrichment-Nonce':nonce,'X-Enrichment-Signature':await serviceSignature(secret,timestamp,nonce,body)}});
  };
  const {bundle,receipt}=await captureBackup(call,secret,commit),bytes=JSON.stringify(bundle);
  writeFileSync(process.argv[3],bytes,{mode:0o600,flag:'wx'});
  assert(await restoreBackup(JSON.parse(readFileSync(process.argv[3],'utf8')),secret));
  process.stdout.write(JSON.stringify({...receipt,file_sha256:createHash('sha256').update(bytes).digest('hex')},null,2)+'\n');
}
if(process.argv[1]===fileURLToPath(import.meta.url))main().catch(()=>{process.stderr.write('archive_preservation_gate_failed\n');process.exitCode=1});
