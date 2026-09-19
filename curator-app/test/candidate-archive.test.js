import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {isolatedStore} from '../../scripts/architecture/private-backup.mjs';
import {ingestCandidateObservation,readCandidateObservation,exportCandidateObservations} from '../src/candidate-archive.js';
import contract from '../../ontology/modules/candidate-archive.json' with {type:'json'};
import migration from '../src/candidate-archive-migration.json' with {type:'json'};
import {sha256} from '../src/review-v2.js';
import {serviceSignature} from '../src/enrichment-store.js';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {preflightCandidates} from '../../scripts/architecture/preflight_candidates.mjs';

const input=(changes={})=>({contract:contract.contract,action:'initialise',domain:'bibliography',source_commit:'a'.repeat(40),expected_version:0,
 row:{...Object.fromEntries(contract.domains.bibliography.fields.map(f=>[f,''])),candidate_id:'CAND-EXAMPLE-1',title:'A reported work',year:'2026',authors:'Names remain source assertions',review_stage:'metadata_fix',current_status:'pending',origin:'daily_surveillance',provenance:'github-issue:#1',source_links:'https://example.org/a; https://example.org/b'},...changes});
async function setup(){const x=isolatedStore('test-candidate-key-long-enough-for-signing','f'.repeat(40));await x.core.requireReady();return {...x,env:await x.core.environment()}}

test('candidate SQL bundle matches its migration; observation replay creates one version and receipt',async()=>{
 assert.equal(migration.sql,readFileSync(new URL('../migrations/0009_candidate_archive.sql',import.meta.url),'utf8'));
 assert.equal(migration.sha256,await sha256(migration.sql));
 const x=await setup();try{const a=input(),first=await ingestCandidateObservation(x.env,a),again=await ingestCandidateObservation(x.env,a);
 assert.equal(again.replayed,true);assert.equal(first.receipt_id,again.receipt_id);
 assert.equal(x.db.prepare('SELECT count(*) n FROM enrichment_candidate_revisions').get().n,1);
 assert.equal(x.db.prepare('SELECT count(*) n FROM enrichment_candidate_values').get().n,2);
 assert.equal((await readCandidateObservation(x.env,first.revision_id)).row.title,a.row.title);
 assert.equal(x.db.prepare('PRAGMA foreign_key_check').all().length,0);
 }finally{x.db.close()}
});
test('source disagreements remain separate assertions; only explicit CAS supersession changes the head',async()=>{
 const x=await setup();try{
  const a=input();await ingestCandidateObservation(x.env,a);
  const alternate=input({action:'observe',expected_version:1,source_commit:'b'.repeat(40),row:{...a.row,title:'Contradictory title'}});
  await ingestCandidateObservation(x.env,alternate);
  const disputed=await exportCandidateObservations(x.env,'bibliography');
  assert.equal(disputed.records[0].row.title,a.row.title);
  assert.equal(disputed.records[0].unresolved_revision_ids.length,1);
  await ingestCandidateObservation(x.env,{...alternate,action:'supersede'});
  assert.equal((await exportCandidateObservations(x.env,'bibliography')).records[0].row.title,'Contradictory title');
  await assert.rejects(ingestCandidateObservation(x.env,{...alternate,action:'supersede',source_commit:'c'.repeat(40)}),/candidate_revision_conflict/);
  assert.equal(x.db.prepare('SELECT count(*) n FROM enrichment_candidate_revisions').get().n,2);
 }finally{x.db.close()}
});
test('signed machine ingress persists and exports rows; the public research route cannot expose private fields',async()=>{
 const x=await setup();try{
  const call=async(operation,ingress)=>{
   const body=JSON.stringify({operation,ingress,expected_commit:'f'.repeat(40)}),ts=String(Date.now()),nonce=crypto.randomUUID();
   return x.core.machine(new Request('https://enrichment.internal/machine',{method:'POST',body,headers:{'Content-Type':'application/json','X-Enrichment-Timestamp':ts,'X-Enrichment-Nonce':nonce,'X-Enrichment-Signature':await serviceSignature(x.env.SESSION_SECRET,ts,nonce,body)}}));
  };
  const a=input();a.row.intake_reason='PRIVATE-NOTE-MARKER';
  assert.equal((await call('archive-candidate',a)).status,200);
  const exported=await call('candidate-export','bibliography');assert.equal(exported.status,200);
  assert.equal((await exported.json()).records[0].row.intake_reason,'PRIVATE-NOTE-MARKER');
  const publicRead=await x.core.fetch(new Request('https://enrichment.internal/public-research?id='+a.row.candidate_id));
  assert.ok(!(await publicRead.text()).includes('PRIVATE-NOTE-MARKER'));
 }finally{x.db.close()}
});
test('entire repository bibliography and three coverage populations survive the real writer, replay and encrypted restore',async()=>{
 const capture=spawnSync('python3',['-c',`
import csv,hashlib,io,json
from pathlib import Path
spec=json.loads(Path('ontology/modules/candidate-archive.json').read_text())['domains']
result={'commit':'a'*40,'domains':{},'file_sha256':{}}
for domain,item in spec.items():
 raw=Path(item['path']).read_bytes()
 result['domains'][domain]=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
 result['file_sha256'][domain]=hashlib.sha256(raw).hexdigest()
print(json.dumps(result))
`],{cwd:fileURLToPath(new URL('../../',import.meta.url)),encoding:'utf8',maxBuffer:16000000});
 assert.equal(capture.status,0);
 const source=JSON.parse(capture.stdout),result=await preflightCandidates(source);
 assert.equal(result.report.source_integrity.revisions_checked,Object.values(source.domains).reduce((n,r)=>n+r.length,0));
 assert.equal(result.report.registered_public_targets,source.domains.bibliography.length);
 assert.equal(result.report.isolated_restore.integrity_verified,true);
 assert.equal(result.report.authority_cutover,false);
});
test('withdrawal excludes the record, retains history and cannot be reversed by replay or old migration',async()=>{
 const x=await setup();try{
  const a=input();await ingestCandidateObservation(x.env,a);
  await ingestCandidateObservation(x.env,{...a,action:'withdraw',expected_version:1});
  assert.equal((await exportCandidateObservations(x.env,'bibliography')).records.length,0);
  await ingestCandidateObservation(x.env,a);
  assert.equal((await exportCandidateObservations(x.env,'bibliography')).records.length,0);
  await assert.rejects(ingestCandidateObservation(x.env,{...a,action:'supersede',expected_version:2,source_commit:'b'.repeat(40)}),/restore_requires/);
  assert.throws(()=>x.db.exec('DELETE FROM enrichment_candidate_revisions'),/append_only/);
 }finally{x.db.close()}
});
test('failed object retention and failed transaction cannot produce a saved receipt; retry recovers',async()=>{
 const x=await setup();try{
  const a=input(),broken={...x.env,REVIEW_EVIDENCE:{put:async()=>{},get:async()=>null}};
  await assert.rejects(ingestCandidateObservation(broken,a),/readback_failed/);
  assert.equal(x.db.prepare('SELECT count(*) n FROM enrichment_candidate_receipts').get().n,0);
  x.db.exec("CREATE TRIGGER injected_receipt_failure BEFORE INSERT ON enrichment_candidate_receipts BEGIN SELECT RAISE(ABORT,'failure'); END");
  await assert.rejects(ingestCandidateObservation(x.env,a),/transaction_conflict/);
  assert.equal(x.db.prepare('SELECT count(*) n FROM enrichment_candidate_records').get().n,0);
  x.db.exec('DROP TRIGGER injected_receipt_failure');
  await ingestCandidateObservation(x.env,a);
  assert.equal(x.db.prepare('SELECT count(*) n FROM enrichment_candidate_receipts').get().n,1);
 }finally{x.db.close()}
});
test('competing updates do not lose either the first committed version or its history',async()=>{
 const x=await setup();try{
  const a=input();await ingestCandidateObservation(x.env,a);
  const outcomes=await Promise.allSettled(['b','c'].map(c=>ingestCandidateObservation(x.env,{...a,action:'supersede',expected_version:1,source_commit:c.repeat(40),row:{...a.row,title:c}})));
  assert.equal(outcomes.filter(r=>r.status==='fulfilled').length,1);
  assert.equal(x.db.prepare('SELECT count(*) n FROM enrichment_candidate_revisions').get().n,2);
  assert.equal(x.db.prepare('SELECT record_version FROM enrichment_candidate_heads').get().record_version,2);
 }finally{x.db.close()}
});
test('closed mechanical ingress cannot invent a decision, unknown field, domain or coverage identity',async()=>{
 const x=await setup();try{
  const a=input();
  await assert.rejects(ingestCandidateObservation(x.env,{...a,row:{...a.row,current_decision:'eligible_core'}}),/approval_required/);
  await assert.rejects(ingestCandidateObservation(x.env,{...a,row:{...a.row,invented:'field'}}),/row_invalid/);
  await assert.rejects(ingestCandidateObservation(x.env,{...a,domain:'arbitrary'}),/domain_invalid/);
  assert.equal(x.db.prepare('SELECT count(*) n FROM enrichment_candidate_records').get().n,0);
 }finally{x.db.close()}
});
