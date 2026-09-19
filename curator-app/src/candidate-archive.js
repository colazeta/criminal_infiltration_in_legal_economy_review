/* Governed candidate observations in the existing archive. No work reconciliation,
   automatic adjudication, source-rights inference or production cutover. */
import contract from '../../ontology/modules/candidate-archive.json' with {type:'json'};
import cycle from '../../config/archive-cycle.json' with {type:'json'};
import {canonicalJson,sha256} from './review-v2.js';

const S=(db,sql,...args)=>db.prepare(sql).bind(...args);
const rows=async(db,sql,...args)=>(await S(db,sql,...args).all()).results;
const fail=(code,status=422)=>{throw Object.assign(Error(code),{code,status})};
const split=value=>value.split(';').map(x=>x.trim()).filter(Boolean);
const keys=(value,names)=>value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join(',')===[...names].sort().join(',');
const domainSpec=domain=>Object.hasOwn(contract.domains,domain)?contract.domains[domain]:fail('candidate_domain_invalid');
const physical=(domain,field)=>domain!=='bibliography'&&['title','doi'].includes(field)?'observed_'+field:field;

export function validateCandidateObservation(input){
 if(!keys(input,['contract','action','domain','source_commit','expected_version','row'])||input.contract!==contract.contract||
    !['initialise','observe','supersede','withdraw'].includes(input.action)||!Number.isSafeInteger(input.expected_version)||input.expected_version<0||
    !/^[a-f0-9]{40}$/.test(input.source_commit||''))fail('candidate_input_invalid');
 const spec=domainSpec(input.domain),row=input.row;
 if(!keys(row,spec.fields)||spec.fields.some(f=>typeof row[f]!=='string'||row[f].length>16000)||
    !/^CAND-[A-Za-z0-9-]{1,100}$/.test(row.candidate_id))fail('candidate_row_invalid');
 for(const f of spec.required_fields)if(!row[f].trim())fail('candidate_required_field');
 for(const [field,allowed] of Object.entries(spec.allowed_values))if(!allowed.includes(row[field]))fail('candidate_controlled_value');
 // This mechanical importer cannot enact or revise scientific decisions. Those
 // require the existing explicit approval path, not an extra string in this input.
 if(input.domain==='bibliography'){
  if(row.current_status!=='pending'||['current_decision','exclusion_reason_code','topic_code','duplicate_target_id','secondary_collection_code','secondary_collection_rationale','last_action_id'].some(f=>row[f]))fail('candidate_scientific_approval_required',409);
  if(row.year&&!/^\d{4}$/.test(row.year))fail('candidate_year_invalid');
  if(!row.title.trim()||row.title.length>3000)fail('candidate_title_invalid');
 }
 if(input.domain==='access'&&row.access_status==='open'&&(!row.access_url||!row.evidence_source))fail('candidate_access_evidence_required');
 if(input.domain==='access'&&row.access_status==='restricted'&&(!row.evidence_source||!row.evidence_detail))fail('candidate_access_evidence_required');
 for(const f of spec.repeated)if(split(row[f]).length>200)fail('candidate_relation_limit');
 return spec;
}

export async function readCandidateObservation(env,revisionId){
 const db=env.REVIEW_DB,revision=await S(db,'SELECT * FROM enrichment_candidate_revisions WHERE revision_id=?',revisionId).first();
 if(!revision)fail('candidate_revision_missing',404);
 const spec=domainSpec(revision.domain),record=await S(db,`SELECT * FROM enrichment_candidate_${revision.domain} WHERE revision_id=?`,revisionId).first();
 if(!record)fail('candidate_relations_incomplete',503);
 const values=await rows(db,'SELECT field,position,value FROM enrichment_candidate_values WHERE revision_id=? ORDER BY field,position',revisionId);
 const result={candidate_id:revision.candidate_id};
 for(const f of spec.fields){
  if(f==='candidate_id')continue;
  result[f]=spec.repeated.includes(f)?values.filter(v=>v.field===f).map(v=>v.value).join('; '):record[physical(revision.domain,f)];
 }
 return {revision,row:result};
}

export async function ingestCandidateObservation(env,input,now=Date.now()){
 const spec=validateCandidateObservation(input),db=env.REVIEW_DB,id=input.row.candidate_id,domain=input.domain;
 const encoded=canonicalJson(input.row),contentHash=await sha256(encoded);
 const revisionId=await sha256(canonicalJson([contract.contract,cycle.review_id,id,domain,input.source_commit,contentHash]));
 const receiptId=await sha256(canonicalJson(input)),storageKey=`candidate-observations/${revisionId}/${contentHash}.json`;
 const previousReceipt=await S(db,'SELECT * FROM enrichment_candidate_receipts WHERE receipt_id=?',receiptId).first();
 if(previousReceipt)return {contract:contract.contract,receipt_id:receiptId,revision_id:revisionId,replayed:true};
 const head=await S(db,'SELECT * FROM enrichment_candidate_heads WHERE candidate_id=? AND cycle_id=? AND domain=?',id,cycle.review_id,domain).first();
 if((head?.record_version||0)!==input.expected_version)fail('candidate_revision_conflict',409);
 if(input.action==='initialise'&&head||['supersede','withdraw'].includes(input.action)&&!head)fail('candidate_transition_invalid',409);
 if(head?.state==='withdrawn'&&input.action!=='observe')fail('candidate_restore_requires_reviewed_procedure',409);
 if(input.action==='withdraw'&&revisionId!==head.revision_id)fail('candidate_withdrawal_revision_mismatch',409);
 // Coverage does not create a registered candidate or silently invent bibliography.
 if(domain!=='bibliography'&&!await S(db,'SELECT candidate_id FROM enrichment_candidate_records WHERE candidate_id=? AND cycle_id=?',id,cycle.review_id).first())fail('candidate_identity_missing',409);
 const object=await env.REVIEW_EVIDENCE.get(storageKey);
 if(!object)await env.REVIEW_EVIDENCE.put(storageKey,encoded);
 const verified=await env.REVIEW_EVIDENCE.get(storageKey);
 if(!verified||await sha256(await verified.text())!==contentHash)fail('candidate_source_readback_failed',503);
 const time=new Date(now).toISOString(),statements=[];
 statements.push(S(db,'INSERT OR IGNORE INTO enrichment_candidate_records VALUES (?,?,?)',id,cycle.review_id,time));
 const exists=await S(db,'SELECT revision_id FROM enrichment_candidate_revisions WHERE revision_id=?',revisionId).first();
 if(!exists){
  statements.push(S(db,'INSERT INTO enrichment_candidate_revisions VALUES (?,?,?,?,?,?,?,?)',revisionId,id,cycle.review_id,domain,input.source_commit,contentHash,storageKey,time));
  const fields=spec.fields.filter(f=>f!=='candidate_id'&&!spec.repeated.includes(f));
  statements.push(S(db,`INSERT INTO enrichment_candidate_${domain}(revision_id,${fields.map(f=>physical(domain,f)).join(',')}) VALUES (${Array(fields.length+1).fill('?').join(',')})`,revisionId,...fields.map(f=>input.row[f])));
  for(const f of spec.repeated)split(input.row[f]).forEach((value,position)=>statements.push(S(db,'INSERT INTO enrichment_candidate_values VALUES (?,?,?,?)',revisionId,f,position,value)));
 }
 if(input.action==='initialise')statements.push(S(db,"INSERT INTO enrichment_candidate_heads VALUES (?,?,?,?,1,'active',?)",id,cycle.review_id,domain,revisionId,time));
 if(['supersede','withdraw'].includes(input.action))statements.push(S(db,'UPDATE enrichment_candidate_heads SET revision_id=?,record_version=record_version+1,state=?,updated_at=? WHERE candidate_id=? AND cycle_id=? AND domain=? AND record_version=?',revisionId,input.action==='withdraw'?'withdrawn':'active',time,id,cycle.review_id,domain,input.expected_version));
 const receipt=S(db,'INSERT INTO enrichment_candidate_receipts VALUES (?,?,?,?,?,?,?,?,?)',receiptId,id,cycle.review_id,domain,revisionId,head?.revision_id||null,input.action,input.expected_version,time);
 const checks=[S(db,`SELECT * FROM enrichment_candidate_${domain} WHERE revision_id=?`,revisionId),S(db,'SELECT * FROM enrichment_candidate_heads WHERE candidate_id=? AND cycle_id=? AND domain=?',id,cycle.review_id,domain),S(db,'SELECT field,position,value FROM enrichment_candidate_values WHERE revision_id=? ORDER BY field,position',revisionId)];
 if(!db.batchValidated)fail('candidate_atomic_storage_required',503);
 try{await db.batchValidated(statements,checks,results=>{
  const record=results[0].results[0],current=results[1].results[0];
  if(!record||spec.fields.filter(f=>f!=='candidate_id'&&!spec.repeated.includes(f)).some(f=>record[physical(domain,f)]!==input.row[f]))return false;
  const expected=spec.repeated.flatMap(f=>split(input.row[f]).map((value,position)=>({field:f,position,value}))).sort((a,b)=>a.field.localeCompare(b.field)||a.position-b.position);
  if(canonicalJson(expected)!==canonicalJson(results[2].results))return false;
  if(input.action==='observe')return (current?.record_version||0)===input.expected_version&&(current?.revision_id||null)===(head?.revision_id||null);
  return current?.revision_id===revisionId&&current.record_version===input.expected_version+1&&current.state===(input.action==='withdraw'?'withdrawn':'active');
 },receipt);}catch{fail('candidate_transaction_conflict',409)}
 return {contract:contract.contract,receipt_id:receiptId,revision_id:revisionId,replayed:false};
}

export async function exportCandidateObservations(env,domain){
 domainSpec(domain);
 const stamp=async()=>await sha256(canonicalJson(await rows(env.REVIEW_DB,'SELECT receipt_id FROM enrichment_candidate_receipts WHERE cycle_id=? AND domain=? ORDER BY receipt_id',cycle.review_id,domain)));
 const before=await stamp();
 const heads=await rows(env.REVIEW_DB,"SELECT * FROM enrichment_candidate_heads WHERE cycle_id=? AND domain=? AND state='active' ORDER BY candidate_id",cycle.review_id,domain);
 const records=[];
 for(const head of heads){
  const unresolved=await rows(env.REVIEW_DB,"SELECT DISTINCT r.revision_id FROM enrichment_candidate_receipts r WHERE r.candidate_id=? AND r.cycle_id=? AND r.domain=? AND r.action='observe' AND NOT EXISTS(SELECT 1 FROM enrichment_candidate_receipts s WHERE s.revision_id=r.revision_id AND s.action IN ('initialise','supersede')) ORDER BY r.revision_id",head.candidate_id,cycle.review_id,domain);
  records.push({head,...await readCandidateObservation(env,head.revision_id),unresolved_revision_ids:unresolved.map(r=>r.revision_id)});
 }
 if(before!==await stamp())fail('candidate_export_changed',409);
 return {contract:contract.contract,cycle_id:cycle.review_id,domain,revision:before,records};
}

export async function auditCandidateArchive(env){
 const revisions=await rows(env.REVIEW_DB,'SELECT * FROM enrichment_candidate_revisions ORDER BY revision_id');
 for(const revision of revisions){
  const object=await env.REVIEW_EVIDENCE.get(revision.storage_key);
  if(!object)fail('candidate_source_missing',503);
  const text=await object.text();if(await sha256(text)!==revision.content_sha256)fail('candidate_source_integrity',503);
  const original=JSON.parse(text),spec=validateCandidateObservation({contract:contract.contract,action:'observe',domain:revision.domain,source_commit:revision.source_commit,expected_version:0,row:original});
  if(original.candidate_id!==revision.candidate_id)fail('candidate_source_identity',503);
  for(const field of spec.repeated)original[field]=split(original[field]).join('; ');
  if(canonicalJson(original)!==canonicalJson((await readCandidateObservation(env,revision.revision_id)).row))fail('candidate_relational_integrity',503);
 }
 return {revisions_checked:revisions.length,integrity_verified:true};
}
