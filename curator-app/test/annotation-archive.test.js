import test from 'node:test';
import assert from 'node:assert/strict';
import {isolatedStore,captureBackup} from '../../scripts/architecture/private-backup.mjs';
import {archiveBackupPage} from '../src/archive-preservation.js';
import {syncTargets} from '../src/paper-enrichment.js';
import {ingestAnnotation,parseAnnotation,readPublicAnnotations,auditAnnotations,reconcileAnnotationCensus} from '../src/annotation-archive.js';
import {serviceSignature} from '../src/enrichment-store.js';

const now=Date.parse('2026-09-19T00:00:00Z'),secret='annotation-test-only-private-backup-key',commit='d'.repeat(40);
const repo='https://github.com/colazeta/criminal_infiltration_in_legal_economy_review';
const candidate='CAND-ANNOTATION-TEST';
function input(){return {action:'observe',issue:{id:10,number:1,body:'<!-- curator-candidate:'+candidate+' -->',html_url:repo+'/issues/1',created_at:'2026-09-01T00:00:00Z',updated_at:'2026-09-01T00:00:00Z',actor:'PRIVATE REVIEWER'},comment:{id:100,body:`<!-- manual-scientific-enrichment:fixture:${candidate} -->
## Manual scientific enrichment packet — schema-aligned, non-decisional
### Top-level scientific fields
- **summary — reported:** Describes an observed relation.
- contribution: The rationale mentions prevention but does not propose that class.
#### Study S1
- population: First independent population.
#### Study S2
- population: Second independent population.
### Clinical-contribution framework — analyst proposal only
- primary: diagnosis
- secondary: aetiology
- alternative: prevention
- rationale: Compares traits; therapy is only mentioned here.
### Datasets
- D1 is named in the annotation without a verified study link.
### Analyst-only working notes
PRIVATE INTERNAL NOTE; PRIVATE REVIEWER
### Sources consulted, versions and QA
https://example.org/publication
`,html_url:repo+'/issues/1#issuecomment-100',created_at:'2026-09-02T00:00:00Z',updated_at:'2026-09-02T00:00:00Z',actor:'PRIVATE REVIEWER'}}}
async function fixture(){const x=isolatedStore(secret,commit);await x.core.requireReady();x.env=await x.core.environment();x.env.CURATOR_LOGIN='PRIVATE REVIEWER';await syncTargets(x.env,{schemaVersion:1,records:[{id:candidate,title:'Synthetic annotation target',doi:'',sourceLinks:['https://example.org/publication']}]},now);return x}

test('original ingress, scoped annotation and explicit classes are saved once under concurrent replay',async()=>{
 const x=await fixture(),data=input(),result=await Promise.all([ingestAnnotation(x.env,data,now),ingestAnnotation(x.env,data,now)]);
 assert.equal(result[0].annotation_id,result[1].annotation_id);
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_ingress_snapshots').get().n,2);
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_manual_annotations').get().n,1);
 const out=await readPublicAnnotations(x.env,candidate);assert.equal(out.annotations.length,1);
 assert.deepEqual(out.annotations[0].sections.filter(s=>s.scope==='studies').map(s=>s.group_label),['S1','S2']);
 assert.deepEqual(out.annotations[0].classes.map(c=>[c.role,c.category]),[['primary','diagnosis'],['secondary','aetiology'],['alternative','prevention']]);
 for(const privateText of ['PRIVATE REVIEWER','PRIVATE INTERNAL NOTE','storage_key','actor'])assert.ok(!JSON.stringify(out).includes(privateText));
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_proposals').get().n,0);
 assert.deepEqual((await auditAnnotations(x.env)).binding_states,{candidate_bound:1,unresolved:0,conflict:0,unregistered:0});x.db.close();
});
test('conflicting markers are retained privately without inventing a candidate association',async()=>{
 const x=await fixture(),data=input();data.issue.body='<!-- curator-candidate:CAND-DIFFERENT -->';
 const receipt=await ingestAnnotation(x.env,data,now);assert.equal(receipt.binding_state,'conflict');
 assert.equal((await readPublicAnnotations(x.env,candidate)).annotations.length,0);
 assert.equal(x.db.prepare('SELECT target_id FROM enrichment_manual_annotations').get().target_id,null);
 assert.equal((await auditAnnotations(x.env)).binding_states.conflict,1);x.db.close();
});
test('source revisions supersede only their own comment; different comments remain coexisting proposals',async()=>{
 const x=await fixture(),a=input();await ingestAnnotation(x.env,a,now);
 const revised=structuredClone(a);revised.comment.updated_at='2026-09-03T00:00:00Z';revised.comment.body=revised.comment.body.replace('primary: diagnosis','primary: screening');await ingestAnnotation(x.env,revised,now+1);
 await ingestAnnotation(x.env,a,now+2);
 let out=await readPublicAnnotations(x.env,candidate);assert.equal(out.annotations.length,1);assert.equal(out.annotations[0].classes[0].category,'screening');
 const other=structuredClone(a);other.comment.id=101;other.comment.html_url=repo+'/issues/1#issuecomment-101';await ingestAnnotation(x.env,other,now+3);
 out=await readPublicAnnotations(x.env,candidate);assert.equal(out.annotations.length,2);
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_manual_annotations').get().n,3);x.db.close();
});
test('withdrawal is durable and a repeated or newer source observation cannot republish it',async()=>{
 const x=await fixture(),a=input();await ingestAnnotation(x.env,a,now);
 await ingestAnnotation(x.env,{...a,action:'withdraw'},now+1);await ingestAnnotation(x.env,{...a,action:'withdraw'},now+2);
 const newer=structuredClone(a);newer.comment.updated_at='2026-09-04T00:00:00Z';newer.comment.body+='\nNew non-decisional text.';await ingestAnnotation(x.env,newer,now+3);
 assert.equal((await readPublicAnnotations(x.env,candidate)).annotations.length,0);
 assert.equal(x.db.prepare('SELECT state FROM enrichment_annotation_heads').get().state,'withdrawn');
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_manual_annotations').get().n,2);
 assert.throws(()=>x.db.exec("UPDATE enrichment_annotation_heads SET state='current',record_version=record_version+1"),/annotation_withdrawal_requires_human_restore/);x.db.close();
});
test('same source time with different content is a retained conflict, not latest-string selection',async()=>{
 const x=await fixture(),a=input();await ingestAnnotation(x.env,a,now);
 a.comment.body=a.comment.body.replace('primary: diagnosis','primary: therapy');await ingestAnnotation(x.env,a,now+1);
 const out=await readPublicAnnotations(x.env,candidate);assert.equal(out.annotations.length,0);assert.equal(out.conflicts,1);assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_manual_annotations').get().n,2);x.db.close();
});
test('replaying a conflicted original or an observed withdrawal cannot clear the conflict or create endless versions',async()=>{
 const x=await fixture(),a=input();await ingestAnnotation(x.env,a,now);
 const b=structuredClone(a);b.comment.body=b.comment.body.replace('primary: diagnosis','primary: therapy');await ingestAnnotation(x.env,b,now+1);
 await ingestAnnotation(x.env,a,now+2);assert.equal((await readPublicAnnotations(x.env,candidate)).conflicts,1);
 const version=x.db.prepare('SELECT record_version FROM enrichment_annotation_heads').get().record_version;
 await ingestAnnotation(x.env,a,now+3);assert.equal(x.db.prepare('SELECT record_version FROM enrichment_annotation_heads').get().record_version,version);
 await ingestAnnotation(x.env,{...a,action:'withdraw'},now+4);await ingestAnnotation(x.env,a,now+5);
 const withdrawnVersion=x.db.prepare('SELECT record_version FROM enrichment_annotation_heads').get().record_version;
 await ingestAnnotation(x.env,a,now+6);assert.equal(x.db.prepare('SELECT record_version FROM enrichment_annotation_heads').get().record_version,withdrawnVersion);x.db.close();
});
test('failed relation transaction retains original ingress for recovery without a successful annotation receipt',async()=>{
 const x=await fixture(),db=x.env.REVIEW_DB,original=db.batchValidated;db.batchValidated=(writes,reads,verify,receipt)=>original(writes,reads,()=>false,receipt);
 await assert.rejects(ingestAnnotation(x.env,input(),now),/annotation_transaction_failed/);
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_manual_annotations').get().n,0);assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_ingress_snapshots').get().n,2);
 db.batchValidated=original;await ingestAnnotation(x.env,input(),now);assert.equal((await readPublicAnnotations(x.env,candidate)).annotations.length,1);x.db.close();
});
test('parser abstains from free-text class inference and hides private/unsafe fields',()=>{
 const p=parseAnnotation('### Clinical-contribution framework\n- primary: could be diagnosis or therapy\n- rationale: screening and prevention mentioned.\n### Top-level scientific fields\n- summary: Bearer abcdefghijklmnopqrstuvwxyz\n');
 assert.equal(p.classes.length,0);assert.equal(p.sections.at(-1).fields.length,0);assert.ok(p.unparsed_lines>0);
});
test('an external commenter cannot grant public visibility through a copied candidate marker',async()=>{
 const x=await fixture(),data=input();data.comment.actor='untrusted-external-commenter';await ingestAnnotation(x.env,data,now);
 assert.equal((await readPublicAnnotations(x.env,candidate)).annotations.length,0);
 assert.equal(x.db.prepare('SELECT authorised_display FROM enrichment_manual_annotations').get().authorised_display,0);assert.equal((await auditAnnotations(x.env)).annotations,1);x.db.close();
});
test('encrypted archive restoration includes every original input, annotation relation and withdrawal',async()=>{
 const x=await fixture(),data=input();await ingestAnnotation(x.env,data,now);await ingestAnnotation(x.env,{...data,action:'withdraw'},now+1);
 const {bundle,receipt}=await captureBackup(request=>archiveBackupPage(x.env,x.storage,request),secret,commit);
 assert.equal(receipt.isolated_restore_verified,true);assert.equal(receipt.integrity_verified,true);assert.ok(!JSON.stringify(bundle).includes('PRIVATE REVIEWER'));x.db.close();
});
test('complete upstream census retires a missing comment once and defers a concurrent newer head',async()=>{
 const x=await fixture();await ingestAnnotation(x.env,input(),now);
 const value={comment_ids:[],source_sha256:'a'.repeat(64),observed_before:new Date(now-1).toISOString()};
 const deferred=await reconcileAnnotationCensus(x.env,value,now+1);assert.equal(deferred.deferred,1);assert.equal(deferred.withdrawn,0);
 value.observed_before=new Date(now+1).toISOString();assert.equal((await reconcileAnnotationCensus(x.env,value,now+2)).withdrawn,1);
 assert.equal((await reconcileAnnotationCensus(x.env,value,now+3)).withdrawn,0);assert.equal((await readPublicAnnotations(x.env,candidate)).annotations.length,0);
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_manual_annotations').get().n,1);x.db.close();
});
test('machine ingress requires the signed deployed version and bounds each batch',async()=>{
 const x=await fixture();
 async function send(data,signed=true){const body=JSON.stringify(data),timestamp=String(Date.now()),nonce=crypto.randomUUID();return x.core.machine(new Request('https://enrichment.internal/machine',{method:'POST',body,headers:{'Content-Type':'application/json',...(signed?{'X-Enrichment-Timestamp':timestamp,'X-Enrichment-Nonce':nonce,'X-Enrichment-Signature':await serviceSignature(secret,timestamp,nonce,body)}:{})}}))}
 const data={operation:'archive-annotation-batch',expected_commit:commit,ingress:[input(),input()]};
 assert.equal((await send(data,false)).status,401);assert.equal((await send({...data,expected_commit:'e'.repeat(40)})).status,409);
 assert.equal((await send({...data,ingress:Array(26).fill(input())})).status,422);
 const response=await send(data);assert.equal(response.status,200);const receipts=(await response.json()).receipts;assert.equal(receipts.length,2);assert.equal(receipts[0].annotation_id,receipts[1].annotation_id);assert.equal(receipts[1].replayed,true);x.db.close();
});

test('one stored annotation drives the public sheet and index, and retirement invalidates old cursors',async()=>{
 const {readPublicIndex,servePublicResearch}=await import('../src/public-paper-research.js');
 const x=await fixture(),a=input();await ingestAnnotation(x.env,a,now);await ingestAnnotation(x.env,a,now+1);
 const request=()=>new Request('https://public.example/api/public-paper-research?view=annotations&id='+candidate);
 let response=await servePublicResearch(request(),x.core),sheet=await response.json();assert.equal(response.status,200);assert.equal(sheet.annotations.length,1);
 const first=await readPublicIndex(x.env);assert.equal(first.records[0].annotation_summary.revision,sheet.revision);assert.equal(first.records[0].completion.completed,false);assert.equal(first.records[0].availability,'not_assessed');assert.deepEqual(first.records[0].classification.primary,['diagnosis']);
 const revised=structuredClone(a);revised.comment.updated_at='2026-09-05T00:00:00Z';revised.comment.body=revised.comment.body.replace('primary: diagnosis','primary: therapy');await ingestAnnotation(x.env,revised,now+2);
 const second=await readPublicIndex(x.env);assert.notEqual(second.index_revision,first.index_revision);assert.deepEqual(second.records[0].classification.primary,['therapy']);
 await assert.rejects(readPublicIndex(x.env,0,first.index_revision),/index_changed/);
 await ingestAnnotation(x.env,{...revised,action:'withdraw'},now+3);const third=await readPublicIndex(x.env);assert.notEqual(third.index_revision,second.index_revision);assert.equal(third.records[0].annotation_summary.count,0);assert.deepEqual(third.records[0].classification.primary,[]);
 await ingestAnnotation(x.env,revised,now+4);response=await servePublicResearch(request(),x.core);assert.equal((await response.json()).annotations.length,0);assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_manual_annotations').get().n,2);x.db.close();
});
