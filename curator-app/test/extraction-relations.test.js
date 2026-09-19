import test from 'node:test';
import assert from 'node:assert/strict';
import schema from '../../schema/paper-enrichment.schema.json' with {type:'json'};
import {isolatedStore,captureBackup,restoreBackup} from '../../scripts/architecture/private-backup.mjs';
import {archiveBackupPage} from '../src/archive-preservation.js';
import {syncTargets,saveSource,storeExtraction,normalizeExistingExtractions} from '../src/paper-enrichment.js';
import {readNormalizedExtraction} from '../src/extraction-relations.js';
import {readPublicResearch} from '../src/public-paper-research.js';
import {canonicalJson,sha256} from '../src/review-v2.js';

const now=Date.parse('2026-09-19T00:00:00Z');
const missing=()=>({status:'not_verifiable',value:null,origin:'source',evidence_span_ids:[]});
const reported=(value,origin='source')=>({status:'reported',value,origin,evidence_span_ids:['s']});
const fill=name=>Object.fromEntries(Object.entries(schema.$defs[name].properties).filter(([,v])=>v.$ref==='#/$defs/fact').map(([k])=>[k,missing()]));
async function fixture(){
 const x=isolatedStore('synthetic-only-secret-for-normalized-tests', 'c'.repeat(40));await x.core.ready;x.env=await x.core.environment();
 const record={id:'CAND-RELATIONS-TEST',title:'Synthetic relational fixture',doi:'',sourceLinks:['https://example.org/fixture']};
 await syncTargets(x.env,{schemaVersion:1,records:[record]},now);x.target=x.db.prepare('SELECT * FROM enrichment_targets').get();
 const source={provider:'Synthetic',source_url:'https://example.org/fixture',evidence_kind:'abstract',text:'Original source bytes retained privately for this synthetic fixture.'};
 x.source=await saveSource(x.env,x.target,source,now);assert.equal(await saveSource(x.env,x.target,source,now),x.source);
 x.input={schema_version:1,protocol_version:'CILE-ENRICH-1',codebook_version:'1.0.0',target_id:x.target.target_id,input_sha256:x.target.input_sha256,
  generated_by:{agent:'PRIVATE ANALYST',model:null,prompt_sha256:null},source_ids:[x.source],source_coverage:'abstract_only',
  spans:[{id:'s',source_id:x.source,start_offset:0,end_offset:15,locator:'private exact locator'}],
  summary:reported('Compares two separate empirical samples'),contribution:missing(),research_question:missing(),infiltration_definition:missing(),infiltration_operationalisation:missing(),authors_limitations:missing(),analyst_limitations:reported('PRIVATE WORKING NOTE','analyst'),
  studies:[1,2].map(i=>({id:'study-'+i,...fill('study'),population:reported('Population '+i)})),
  datasets:[1,2].map(i=>({id:'data-'+i,study_id:'study-'+i,...fill('dataset'),name:reported('Dataset '+i)})),
  analyses:[1,2].map(i=>({id:'analysis-'+i,study_id:'study-'+i,dataset_ids:['data-'+i],...fill('analysis')})),
  variable_uses:[1,2].map(i=>({id:'variable-'+i,analysis_id:'analysis-'+i,dataset_ids:['data-'+i],...fill('variable_use')})),
  findings:[1,2].map(i=>({id:'finding-'+i,analysis_id:'analysis-'+i,variable_use_ids:['variable-'+i],...fill('finding'),statement:reported('Outcome '+i)})),
  framework:{status:'proposed',primary:'diagnosis',rationale:reported('Characterizes observed attributes','analyst'),secondary:[],alternative:null}};
 x.record=record;return x;
}

test('one validated transaction preserves identity, two studies, typed joins and a safe public sheet',async()=>{
 const x=await fixture();const [a,b]=await Promise.all([storeExtraction(x.env,x.target,x.input,now),storeExtraction(x.env,x.target,x.input,now)]);
 assert.equal(a.proposal_id,b.proposal_id);assert.equal(Number(a.replayed)+Number(b.replayed),1);
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_sources').get().n,1);
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_proposals').get().n,1);
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_normalization_receipts').get().n,1);
 const proposal=x.db.prepare('SELECT * FROM enrichment_proposals').get();
 assert.deepEqual(await readNormalizedExtraction(x.env.REVIEW_DB,proposal),x.input);
 const joined=x.db.prepare('SELECT a.analysis_id,d.dataset_id FROM enrichment_analysis_datasets r JOIN enrichment_analyses a USING(proposal_id,analysis_id) JOIN enrichment_datasets d USING(proposal_id,dataset_id) ORDER BY a.analysis_id').all();
 assert.deepEqual(joined.map(r=>[r.analysis_id,r.dataset_id]),[['analysis-1','data-1'],['analysis-2','data-2']]);
 const projected=await readPublicResearch(x.env,x.record.id);assert.equal(projected.availability,'available');assert.equal(projected.research.studies.length,2);assert.equal(projected.research.findings.length,2);
 for(const value of ['PRIVATE ANALYST','PRIVATE WORKING NOTE','Original source bytes','private exact locator'])assert.ok(!JSON.stringify(projected).includes(value));
 const replay=await storeExtraction(x.env,x.target,x.input,now);assert.equal(replay.replayed,true);x.db.close();
});
test('readback failure rolls back submission, relations and receipt together; retry succeeds once',async()=>{
 const x=await fixture(),db=x.env.REVIEW_DB,original=db.batchValidated;
 db.batchValidated=(writes,reads,verify,receipt)=>original(writes,reads,()=>false,receipt);
 await assert.rejects(storeExtraction(x.env,x.target,x.input,now),/normalized_extraction_integrity/);
 for(const table of ['enrichment_proposals','enrichment_facts','enrichment_fact_evidence','enrichment_normalization_receipts'])assert.equal(x.db.prepare('SELECT COUNT(*) n FROM '+table).get().n,0);
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_sources').get().n,1);
 db.batchValidated=original;await storeExtraction(x.env,x.target,x.input,now);assert.equal((await readPublicResearch(x.env,x.record.id)).availability,'available');x.db.close();
});
test('SQL rejects cross-study dataset use and cross-analysis finding variables',async()=>{
 const x=await fixture(),p=await storeExtraction(x.env,x.target,x.input,now);
 assert.throws(()=>x.db.prepare('INSERT INTO enrichment_analysis_datasets VALUES (?,?,?,?)').run(p.proposal_id,'analysis-1','data-2',2),/cross_study_dataset/);
 assert.throws(()=>x.db.prepare('INSERT INTO enrichment_variable_datasets VALUES (?,?,?,?)').run(p.proposal_id,'variable-1','data-2',2),/variable_dataset_scope/);
 assert.throws(()=>x.db.prepare('INSERT INTO enrichment_finding_variables VALUES (?,?,?,?)').run(p.proposal_id,'finding-1','variable-2',2),/finding_variable_scope/);
 assert.throws(()=>x.db.exec("UPDATE enrichment_facts SET value='changed'"),/append_only/);
 assert.throws(()=>x.db.exec('DELETE FROM enrichment_fact_evidence'),/append_only/);x.db.close();
});
test('controlled backfill preserves original bytes and verifies every source and child before receipt',async()=>{
 const x=await fixture(),encoded=canonicalJson(x.input),hash=await sha256(encoded),id=await sha256(x.target.target_id+x.target.input_sha256+hash);
 x.db.prepare('INSERT INTO enrichment_proposals VALUES (?,?,?,?,?,?,?,?,?)').run(id,x.target.target_id,x.target.input_sha256,'CILE-ENRICH-1','1.0.0',hash,encoded,canonicalJson(x.input.generated_by),new Date(now).toISOString());
 for(const [group,key,parent] of [['studies','study_id'],['datasets','dataset_id','study_id'],['analyses','analysis_id','study_id'],['variable_uses','variable_use_id','analysis_id'],['findings','finding_id','analysis_id']])for(const item of x.input[group]){
  const values=[id,...(parent?[item[parent]]:[]),item.id,canonicalJson(item)];x.db.prepare(`INSERT INTO enrichment_${group} VALUES (${values.map(()=>'?').join(',')})`).run(...values);
 }
 x.db.prepare('INSERT INTO enrichment_framework_proposals VALUES (?,?,?,?)').run(id,x.input.framework.primary,x.input.framework.status,canonicalJson(x.input.framework));
 assert.equal((await readPublicResearch(x.env,x.record.id)).availability,'withheld');
 const first=await normalizeExistingExtractions(x.env,now);assert.equal(first.migrated,1);
 const again=await normalizeExistingExtractions(x.env,now);assert.equal(again.migrated,0);assert.equal(again.verified,1);
 assert.equal(x.db.prepare('SELECT payload_json FROM enrichment_proposals').get().payload_json,encoded);
 const receipt=x.db.prepare('SELECT * FROM enrichment_normalization_receipts').get();assert.equal(receipt.write_kind,'backfill');assert.equal(receipt.source_sha256,receipt.rebuilt_sha256);
 assert.equal((await readPublicResearch(x.env,x.record.id)).availability,'available');x.db.close();
});
test('later input is a new version; old facts remain intact and cannot be silently reattached',async()=>{
 const x=await fixture();const first=await storeExtraction(x.env,x.target,x.input,now);
 await syncTargets(x.env,{schemaVersion:1,records:[{...x.record,title:'Updated observed bibliographic record'}]},now+1000);
 assert.equal((await readPublicResearch(x.env,x.record.id)).availability,'stale');
 await assert.rejects(storeExtraction(x.env,x.db.prepare('SELECT * FROM enrichment_targets').get(),x.input,now+1000),/stale_input/);
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_normalization_receipts WHERE proposal_id=?').get(first.proposal_id).n,1);
 assert.deepEqual(await readNormalizedExtraction(x.env.REVIEW_DB,x.db.prepare('SELECT * FROM enrichment_proposals').get()),x.input);x.db.close();
});
test('a populated normalized graph, original bytes and receipts survive encrypted isolated restoration',async()=>{
 const x=await fixture();await storeExtraction(x.env,x.target,x.input,now);
 const {bundle,receipt}=await captureBackup(request=>archiveBackupPage(x.env,x.storage,request),'synthetic-only-secret-for-normalized-tests','c'.repeat(40));
 assert.equal(receipt.isolated_restore_verified,true);assert.equal(receipt.checked_public_targets,1);
 const restored=await restoreBackup(bundle,'synthetic-only-secret-for-normalized-tests');
 assert.match(receipt.state_sha256,/^[a-f0-9]{64}$/);assert.equal(restored.state_sha256,receipt.state_sha256);assert.equal(restored.integrity_verified,true);
 for(const value of ['PRIVATE ANALYST','PRIVATE WORKING NOTE','Population 1','Dataset 2'])assert.ok(!JSON.stringify(bundle).includes(value));
 x.db.close();
});
