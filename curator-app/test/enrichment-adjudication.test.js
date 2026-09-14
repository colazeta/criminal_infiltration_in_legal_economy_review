import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {syncTargets,saveSource,storeExtraction} from '../src/paper-enrichment.js';
import {importCalibrationApproval,importCompletionApproval,completionPacket,publicCompletionState,verifiedManifest} from '../src/enrichment-adjudication.js';

const now=Date.parse('2026-09-14T09:00:00Z');
const head='a'.repeat(40);
function setup(){
  const sqlite=new DatabaseSync(':memory:');sqlite.exec('PRAGMA foreign_keys=ON');
  sqlite.exec(readFileSync(new URL('../migrations/0003_paper_enrichment.sql',import.meta.url),'utf8'));
  sqlite.exec(readFileSync(new URL('../migrations/0005_enrichment_adjudication.sql',import.meta.url),'utf8'));
  const db={sqlite,prepare(sql){let v=[];return{bind(...a){v=a;return this},async first(){return sqlite.prepare(sql).get(...v)||null},async all(){return{results:sqlite.prepare(sql).all(...v)}},async run(){return{meta:{changes:Number(sqlite.prepare(sql).run(...v).changes)}}}}},async batch(ss){sqlite.exec('BEGIN');try{const r=[];for(const s of ss)r.push(await s.run());sqlite.exec('COMMIT');return r}catch(e){sqlite.exec('ROLLBACK');throw e}}};
  const evidence=new Map(),env={REVIEW_DB:db,REVIEW_EVIDENCE:{async put(k,v){evidence.set(k,v)},async get(k){return evidence.has(k)?{async text(){return evidence.get(k)}}:null}},GITHUB_REPOSITORY:'colazeta/test',GITHUB_TOKEN:'token',CURATOR_LOGIN:'owner'};
  return{sqlite,db,evidence,env};
}
const record={id:'CAND-COMPLETE-001',title:'Synthetic complete paper',doi:'10.1234/complete',sourceLinks:['https://example.org/paper']};
const missing=()=>({status:'not_reported',value:null,evidence_span_ids:[],origin:'source'});
const reported=(value,origin='source')=>({status:'reported',value,evidence_span_ids:['span-1'],origin});
async function prepared(){
  const x=setup();await syncTargets(x.env,{schemaVersion:1,records:[record]},now);
  const target=x.sqlite.prepare('SELECT * FROM enrichment_targets').get();
  const text='Full text evidence for completion and grounded framework rationale.';
  const sourceId=await saveSource(x.env,target,{provider:'Fixture',source_url:'https://example.org/full',evidence_kind:'full_text',text,version_label:'author manuscript',licence_status:'verified_for_private_research'},now);
  const proposal={schema_version:1,protocol_version:'CILE-ENRICH-1',codebook_version:'1.0.0',target_id:target.target_id,input_sha256:target.input_sha256,
    generated_by:{agent:'fixture',model:'model-1',prompt_sha256:'b'.repeat(64)},source_ids:[sourceId],source_coverage:'full_text',
    spans:[{id:'span-1',source_id:sourceId,start_offset:0,end_offset:9,locator:'p. 1'}],
    summary:reported('Grounded summary'),contribution:missing(),research_question:missing(),infiltration_definition:missing(),infiltration_operationalisation:missing(),authors_limitations:missing(),analyst_limitations:missing(),
    studies:[],datasets:[],analyses:[],variable_uses:[],findings:[],
    framework:{status:'proposed',primary:'diagnosis',rationale:reported('Grounded class rationale','analyst'),secondary:[],alternative:null}};
  await storeExtraction(x.env,target,proposal,now+1);
  x.sqlite.prepare('INSERT INTO enrichment_citation_observations VALUES (?,?,?,?,?,?,?,?,?,?)').run('obs-o',target.target_id,target.input_sha256,'Crossref','outgoing','doi:self','doi:ref','crossref:s1','https://api.crossref.org/works/x','2026-09-14T09:01:00Z');
  x.sqlite.prepare('INSERT INTO enrichment_citation_observations VALUES (?,?,?,?,?,?,?,?,?,?)').run('obs-i',target.target_id,target.input_sha256,'OpenAlex','incoming','https://openalex.org/W2','https://openalex.org/W1','2026-09-14T09:01:00Z','https://api.openalex.org/works','2026-09-14T09:01:00Z');
  x.sqlite.prepare('INSERT INTO enrichment_citation_coverage VALUES (?,?,?,?,?,?,?,?,?,?,?,?)').run('cov-o',target.target_id,target.input_sha256,'Crossref','outgoing','crossref:s1','https://api.crossref.org/works/x',1,1,null,'provider_complete','2026-09-14T09:01:00Z');
  x.sqlite.prepare('INSERT INTO enrichment_citation_coverage VALUES (?,?,?,?,?,?,?,?,?,?,?,?)').run('cov-i',target.target_id,target.input_sha256,'OpenAlex','incoming','2026-09-14T09:01:00Z','https://api.openalex.org/works',1,1,null,'provider_complete','2026-09-14T09:01:00Z');
  return{...x,target,proposal};
}
const encoded=value=>Buffer.from(JSON.stringify(value)).toString('base64');
function approvedGet(manifest,pr=10,{reviewCommit=head,state='APPROVED'}={}){
  return async path=>{
    if(path.includes('/pulls/'+pr+'/reviews'))return[{id:123,state,commit_id:reviewCommit,submitted_at:'2026-09-14T09:10:00Z',user:{login:'owner',type:'User'}}];
    if(path.endsWith('/pulls/'+pr))return{merged:true,base:{ref:'main',repo:{full_name:'colazeta/test'}},head:{sha:head,repo:{full_name:'colazeta/test'}}};
    if(path.includes('/contents/'))return{encoding:'base64',size:JSON.stringify(manifest).length,content:encoded(manifest)};
    throw Error('unexpected:'+path);
  };
}
const calibrationManifest={action:'approve_enrichment_calibration',calibration_id:'CAL-2026-001',protocol_version:'CILE-ENRICH-1',codebook_version:'1.0.0',model:'model-1',prompt_sha256:'b'.repeat(64),benchmark_sha256:'c'.repeat(64),metrics_sha256:'d'.repeat(64),benchmark_size:12,reference_checked_cases:12,full_text_cases:4,hard_cases:3,heterogeneous_designs:true,source_fidelity_checked:true,omissions_checked:true,classification_agreement_checked:true,field_accuracy_checked:true,cost_limits_checked:true};

test('adjudication migration starts empty and is append-only',()=>{
  const {sqlite}=setup();assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM enrichment_adjudication_receipts').get().n,0);
  assert.throws(()=>sqlite.exec("DELETE FROM enrichment_adjudication_receipts"),/append_only/);
});
test('completion packet fails closed before accepted calibration',async()=>{
  const {env,target}=await prepared();await assert.rejects(completionPacket(env,target.target_id),/accepted_calibration_required/);
});
test('calibration import requires an exact-head human approval and is idempotent',async()=>{
  const {env,sqlite}=setup();
  await assert.rejects(importCalibrationApproval(env,{calibration_id:'CAL-2026-001',pr_number:10},approvedGet(calibrationManifest,10,{reviewCommit:'f'.repeat(40)})),/exact_head/);
  const one=await importCalibrationApproval(env,{calibration_id:'CAL-2026-001',pr_number:10},approvedGet(calibrationManifest),now);
  const two=await importCalibrationApproval(env,{calibration_id:'CAL-2026-001',pr_number:10},approvedGet(calibrationManifest),now+1);
  assert.equal(one.replayed,false);assert.equal(two.replayed,true);assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM enrichment_calibration_receipts').get().n,1);
});
test('only an exact accepted current packet creates a completion receipt',async()=>{
  const {env,target,sqlite}=await prepared();
  await importCalibrationApproval(env,{calibration_id:'CAL-2026-001',pr_number:10},approvedGet(calibrationManifest),now);
  const packet=await completionPacket(env,target.target_id);
  assert.equal(packet.status,'ready_for_human_review');assert.equal(packet.manifest.checklist.bibliography_reviewed,null);
  const manifest={...packet.manifest,checklist:Object.fromEntries(Object.keys(packet.manifest.checklist).map(k=>[k,true]))};
  const out=await importCompletionApproval(env,{target_id:target.target_id,pr_number:11},approvedGet(manifest,11),now+1000);
  assert.equal(out.replayed,false);assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM enrichment_adjudication_receipts').get().n,1);
  const publicState=await publicCompletionState(env,record.id);assert.equal(publicState.completed,true);assert.equal(publicState.status,'accepted');
  assert.equal(publicState.outgoing_references.identifiers.includes('doi:ref'),true);
});
test('changed scientific input cannot inherit an accepted receipt',async()=>{
  const {env,target}=await prepared();
  await importCalibrationApproval(env,{calibration_id:'CAL-2026-001',pr_number:10},approvedGet(calibrationManifest),now);
  const packet=await completionPacket(env,target.target_id),manifest={...packet.manifest,checklist:Object.fromEntries(Object.keys(packet.manifest.checklist).map(k=>[k,true]))};
  await importCompletionApproval(env,{target_id:target.target_id,pr_number:11},approvedGet(manifest,11),now+1000);
  await syncTargets(env,{schemaVersion:1,records:[{...record,title:'Changed title'}]},now+2000);
  const state=await publicCompletionState(env,record.id);assert.equal(state.completed,false);assert.equal(state.status,'stale');
});
test('verified manifest rejects approval superseded by changes-requested',async()=>{
  const get=async path=>{
    if(path.includes('/reviews'))return[
      {id:1,state:'APPROVED',commit_id:head,submitted_at:'2026-09-14T09:00:00Z',user:{login:'owner',type:'User'}},
      {id:2,state:'CHANGES_REQUESTED',commit_id:head,submitted_at:'2026-09-14T09:01:00Z',user:{login:'owner',type:'User'}}];
    if(path.endsWith('/pulls/10'))return{merged:true,base:{ref:'main',repo:{full_name:'colazeta/test'}},head:{sha:head,repo:{full_name:'colazeta/test'}}};
    return{encoding:'base64',size:2,content:encoded({})};
  };
  await assert.rejects(verifiedManifest({GITHUB_REPOSITORY:'colazeta/test',GITHUB_TOKEN:'token',CURATOR_LOGIN:'owner'},10,'scientific-approvals/x.json',get),/exact_head/);
});
