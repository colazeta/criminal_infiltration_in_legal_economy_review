import test from 'node:test';
import assert from 'node:assert/strict';
import {isolatedStore,captureBackup,restoreBackup} from '../../scripts/architecture/private-backup.mjs';
import {archiveBackupPage,encodeStored,decodeStored,openBackupPage} from '../src/archive-preservation.js';
import {syncTargets,saveSource} from '../src/paper-enrichment.js';
import {serviceSignature} from '../src/enrichment-store.js';

const secret='synthetic-backup-secret-not-a-production-credential',commit='b'.repeat(40);
async function fixture(){
 const x=isolatedStore(secret,commit);await x.core.requireReady();x.env=await x.core.environment();
 await syncTargets(x.env,{schemaVersion:1,records:Array.from({length:294},(_,i)=>({id:'CAND-BACKUP-'+i,title:'Private fixture '+i,doi:'',sourceLinks:['https://example.org/'+i]}))},Date.now());
 const target=x.db.prepare('SELECT * FROM enrichment_targets LIMIT 1').get();
 const source={provider:'Fixture',source_url:'https://example.org/0',evidence_kind:'abstract',text:'PRIVATE SOURCE NEVER STORED IN AN ARTIFACT'};
 await saveSource(x.env,target,source,Date.now());await saveSource(x.env,target,source,Date.now());
 x.kv.set('unattached:retained-bytes',new Uint8Array([0,1,2,255]));x.kv.set('nonce:excluded','transient');
 x.call=request=>archiveBackupPage(x.env,x.storage,request,x.core.backupPagination);
 return x;
}
test('encrypted complete-store backup restores all 294 identities and retained bytes without publishing',async()=>{
 const x=await fixture();const {bundle,receipt}=await captureBackup(x.call,secret,commit);
 assert.equal(receipt.isolated_restore_verified,true);assert.equal(receipt.integrity_verified,true);
 assert.equal(receipt.checked_public_targets,294);assert.equal(receipt.production_restored,false);assert.equal(receipt.cutover_ready,false);
 const encoded=JSON.stringify(bundle);for(const privateText of ['PRIVATE SOURCE','CAND-BACKUP','unattached:','transient'])assert.ok(!encoded.includes(privateText));
 const again=await restoreBackup(JSON.parse(encoded),secret);assert.equal(again.kv_sha256,receipt.kv_sha256);
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_sources').get().n,1);
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_proposals').get().n,0);
 x.db.close();
});
test('encrypted pages reject tampering, wrong key, mixed snapshot IDs and truncation',async()=>{
 const x=await fixture();const {bundle}=await captureBackup(x.call,secret,commit);
 await assert.rejects(restoreBackup(bundle,secret+'wrong'));
 const bad=structuredClone(bundle);bad.pages[0].ciphertext='A'+bad.pages[0].ciphertext.slice(1);
 if(bad.pages[0].ciphertext===bundle.pages[0].ciphertext)bad.pages[0].ciphertext='B'+bad.pages[0].ciphertext.slice(1);
 await assert.rejects(restoreBackup(bad,secret));
 const mixed=structuredClone(bundle);mixed.pages[1].snapshot_id=crypto.randomUUID();await assert.rejects(restoreBackup(mixed,secret));
 await assert.rejects(restoreBackup({...bundle,pages:bundle.pages.slice(0,-1)},secret));x.db.close();
});
test('SQL change during capture is not certified as a consistent snapshot',async()=>{
 const x=await fixture();let catalogues=0;
 await assert.rejects(captureBackup(async request=>{if(request.part==='catalogue'&&++catalogues===2)x.db.exec("UPDATE enrichment_targets SET updated_at='changed'");return x.call(request)},secret,commit));x.db.close();
});
test('KV change and unsupported values stop capture rather than silently omitting material',async()=>{
 const x=await fixture();let passes=0;
 await assert.rejects(captureBackup(async request=>{if(request.part==='kv'&&!request.after&&++passes===2)x.kv.set('unattached:retained-bytes',new Uint8Array([3]));return x.call(request)},secret,commit));
 assert.throws(()=>encodeStored(new Map([['unsupported',1]])));x.db.close();
});
test('backup preserves structured clone binary values and object keys without prototypes',()=>{
 const input={a:[true,null,'text',new Uint8Array([0,255])],b:12};assert.deepEqual(decodeStored(encodeStored(input)),input);
 const data=decodeStored({type:'object',value:[['__proto__',{type:'scalar',value:'retained'}]]});assert.equal(Object.getPrototypeOf(data),Object.prototype);assert.equal(data.__proto__,'retained');
});
test('backup operation requires a signed exact deployment and a closed fixed read envelope',async()=>{
 const x=await fixture();const body=JSON.stringify({operation:'architecture-backup',expected_commit:commit,backup:{part:'catalogue',snapshot_id:crypto.randomUUID()}});
 const unsigned=new Request('https://enrichment.internal/machine',{method:'POST',headers:{'Content-Type':'application/json'},body});assert.equal((await x.core.machine(unsigned)).status,401);
 const ts=String(Date.now()),nonce=crypto.randomUUID();const request=new Request('https://enrichment.internal/machine',{method:'POST',body,headers:{'Content-Type':'application/json','X-Enrichment-Timestamp':ts,'X-Enrichment-Nonce':nonce,'X-Enrichment-Signature':await serviceSignature(secret,ts,nonce,body)}});
 const response=await x.core.machine(request);assert.equal(response.status,200);assert.ok((await response.json()).ciphertext);
 await assert.rejects(x.call({part:'sql',table:'sqlite_master',offset:0,snapshot_id:crypto.randomUUID()}));x.db.close();
});

test('sequential backup pages seek sparse rowids and preserve the existing encrypted row contract',async()=>{
 const x=await fixture();
 try{
  // Exercise SQLite rowids beyond JavaScript's safe integer range without rounding.
  x.db.exec('UPDATE enrichment_targets SET rowid=rowid+9007199254740992');
  const expected=x.db.prepare('SELECT * FROM enrichment_targets ORDER BY rowid').all().map(r=>({...r}));
  const sql=[],original=x.env.REVIEW_DB.prepare;
  x.env.REVIEW_DB.prepare=query=>{sql.push(query);return original(query)};
  const snapshot_id=crypto.randomUUID(),actual=[];
  for(let offset=0;offset<expected.length;offset+=100){
   const page=await openBackupPage(await x.call({part:'sql',table:'enrichment_targets',offset,snapshot_id}),secret,commit,snapshot_id);
   assert.deepEqual(Object.keys(page).sort(),['offset','part','rows','table']);
   assert.equal(page.offset,offset);actual.push(...page.rows);
  }
  assert.deepEqual(actual,expected);
  assert.equal(sql.filter(s=>s.includes('OFFSET')).length,1);
  assert.equal(sql.filter(s=>s.includes('WHERE rowid > ?')).length,2);
  const plan=x.db.prepare('EXPLAIN QUERY PLAN SELECT * FROM enrichment_targets WHERE rowid > ? ORDER BY rowid LIMIT 100').all('9007199254740992');
  assert.ok(plan.some(p=>/SEARCH.*INTEGER PRIMARY KEY/.test(p.detail)));
 }finally{x.db.close()}
});

test('backup retries, interleaved tables, new snapshots and cache eviction never skip rows',async()=>{
 const x=await fixture();
 try{
  x.db.exec('UPDATE enrichment_targets SET rowid=-rowid*3-1000');
  const snapshot_id=crypto.randomUUID(),table='enrichment_targets';
  const page=async(offset,id=snapshot_id)=>openBackupPage(await x.call({part:'sql',table,offset,snapshot_id:id}),secret,commit,id);
  const expected=offset=>x.db.prepare('SELECT * FROM enrichment_targets ORDER BY rowid LIMIT 100 OFFSET ?').all(offset).map(r=>({...r}));
  assert.deepEqual((await page(0)).rows,expected(0));
  assert.deepEqual((await page(0)).rows,expected(0));
  await x.call({part:'sql',table:'enrichment_inputs',offset:0,snapshot_id});
  assert.deepEqual((await page(100)).rows,expected(100));
  assert.deepEqual((await page(100,crypto.randomUUID())).rows,expected(100));
  assert.deepEqual((await page(0)).rows,expected(0));
  for(let i=0;i<65;i++)await page(0,crypto.randomUUID());
  assert.equal(x.core.backupPagination.size,64);
  assert.deepEqual((await page(100)).rows,expected(100));
  assert.deepEqual((await page(250)).rows,expected(250));
 }finally{x.db.close()}
});
