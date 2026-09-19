import test from 'node:test';
import assert from 'node:assert/strict';
import {setup,request} from './enrichment-store.test.js';
import {syncTargets,saveSource} from '../src/paper-enrichment.js';
import {auditArchitecture} from '../src/architecture-audit.js';
import {sha256} from '../src/review-v2.js';

const record={id:'CAND-AUDIT-001',title:'Synthetic architecture fixture',doi:'',sourceLinks:['https://example.org/audit']};
async function fixture(){const x=setup();await x.core.ready;x.runtime=await x.core.environment();await syncTargets(x.runtime,{schemaVersion:1,records:[record]},Date.now());x.target=x.db.prepare('SELECT * FROM enrichment_targets').get();return x}

test('authenticated audit covers every target and returns no source or private row',async()=>{
 const x=await fixture();
 await saveSource(x.runtime,x.target,{provider:'Fixture',source_url:'https://example.org/audit',evidence_kind:'abstract',text:'Private source body never released in audit.'},Date.now());
 const before=x.db.prepare('SELECT COUNT(*) n FROM enrichment_sources').get().n;
 const response=await x.core.machine(await request({operation:'architecture-audit'}));
 assert.equal(response.status,200);const result=await response.json();
 assert.equal(result.complete,true);assert.equal(result.integrity_verified,true);assert.equal(result.checked_public_targets,1);
 assert.equal(result.cutover_ready,false);assert.equal(result.counts.enrichment_sources,1);
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_sources').get().n,before);
 const serial=JSON.stringify(result);
 for(const secret of [record.title,record.id,x.target.target_id,'Private source body','record_json','storage_key'])assert.ok(!serial.includes(secret));
});
test('damaged historical source is detected even when no current proposal uses it',async()=>{
 const x=await fixture();await saveSource(x.runtime,x.target,{provider:'Fixture',source_url:'https://example.org/audit',evidence_kind:'metadata',text:'Retained metadata.'},Date.now());
 const s=x.db.prepare('SELECT * FROM enrichment_sources').get();x.kv.delete('evidence:'+s.storage_key+':0');
 const audit=await auditArchitecture(x.runtime);assert.equal(audit.integrity_verified,false);assert.equal(audit.issues.source_object_unreadable,1);
});
test('all 294 current candidates are checked, including no-proposal records',async()=>{
 const x=await fixture();await syncTargets(x.runtime,{schemaVersion:1,records:Array.from({length:294},(_,i)=>({...record,id:'CAND-AUDIT-'+i}))},Date.now());
 const audit=await auditArchitecture(x.runtime);assert.equal(audit.checked_public_targets,294);assert.equal(audit.public_states.not_assessed,294);assert.equal(audit.integrity_verified,true);
});
test('schema drift blocks certification instead of ignoring an unexpected table',async()=>{
 const x=await fixture();x.db.exec('CREATE TABLE unexpected_private_store(id TEXT)');
 await assert.rejects(auditArchitecture(x.runtime),/architecture_schema_set_mismatch/);
 const r=await x.core.machine(await request({operation:'architecture-audit'}));assert.equal(r.status,503);assert.deepEqual(await r.json(),{error_code:'architecture_schema_set_mismatch'});
});
test('known Cloudflare KV tables are accessed through adapters and do not masquerade as application schema',async()=>{
 const x=await fixture();x.db.exec('CREATE TABLE _cf_KV(key TEXT,value BLOB); CREATE TABLE _cf_EXTERNALS(id INTEGER); CREATE TABLE __cf_kv(key TEXT); CREATE TABLE _cf_METADATA(key INTEGER,value BLOB)');
 const r=await auditArchitecture(x.runtime);assert.equal(r.integrity_verified,true);assert.equal(Object.keys(r.counts).length,55);
 x.db.exec('CREATE TABLE _cf_unknown_application(id TEXT)');
 await assert.rejects(auditArchitecture(x.runtime),/architecture_schema_set_mismatch/);
});
test('disabled foreign keys are a failed integrity gate',async()=>{
 const x=await fixture();x.db.exec('PRAGMA foreign_keys=OFF');
 const r=await auditArchitecture(x.runtime);assert.equal(r.integrity_verified,false);assert.equal(r.issues.foreign_keys_disabled,1);
});
test('schema census reveals only public names and hashes unknown private names',async()=>{
 const x=await fixture();x.db.exec('CREATE TABLE private_unmapped_name(secret TEXT); CREATE TABLE scholarly_works(work_id TEXT)');
 const response=await x.core.machine(await request({operation:'architecture-schema'}));assert.equal(response.status,200);
 const census=await response.json();assert.equal(census.expected_present.length,55);
 assert.deepEqual(census.expected_missing,[]);assert.deepEqual(census.other_mapped_present,['scholarly_works']);
 assert.deepEqual(census.unknown_table_sha256,[await sha256('private_unmapped_name')]);
 assert.ok(!JSON.stringify(census).includes('private_unmapped_name'));
 assert.equal((await x.core.machine(new Request('https://enrichment.internal/machine',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operation:'architecture-schema'})}))).status,401);
});
test('concurrent data change cannot be certified as a single archive revision',async()=>{
 const x=await fixture();await saveSource(x.runtime,x.target,{provider:'Fixture',source_url:'https://example.org/audit',evidence_kind:'metadata',text:'Fixture'},Date.now());
 const original=x.runtime.REVIEW_EVIDENCE.get;let changed=false;
 x.runtime.REVIEW_EVIDENCE.get=async key=>{if(!changed){changed=true;x.db.exec("UPDATE enrichment_targets SET updated_at='changed' ")}return original(key)};
 await assert.rejects(auditArchitecture(x.runtime),/architecture_state_changed/);
});
test('failed private operation returns a closed code rather than private exception text',async()=>{
 const x=await fixture();const original=x.core.environment.bind(x.core);
 x.core.environment=async()=>{throw Error('PRIVATE source body and identity')};
 const response=await x.core.machine(await request({operation:'architecture-audit'}));
 assert.equal(response.status,503);assert.deepEqual(await response.json(),{error_code:'architecture_audit_failed'});x.core.environment=original;
});
