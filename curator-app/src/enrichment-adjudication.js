/* Independent scientific acceptance for candidate-bound enrichment.
   Engineering can prepare packets; only an exact-head human approval can create a receipt. */
import {canonicalJson, sha256} from './review-v2.js';
import {fetchWithTimeout} from './network.js';

const PROTOCOL='CILE-ENRICH-1', CODEBOOK='1.0.0';
const CLASSES=new Set(['aetiology','diagnosis','screening','therapy','prognosis','prevention']);
const CHECKS=['source_evidence_reviewed','extraction_reviewed','framework_reviewed','bibliography_reviewed','incoming_citations_reviewed','limitations_reviewed'];
const CALIBRATION_CHECKS=['heterogeneous_designs','source_fidelity_checked','omissions_checked','classification_agreement_checked','field_accuracy_checked','cost_limits_checked'];
const S=(db,sql,...values)=>db.prepare(sql).bind(...values);
const rows=async(db,sql,...values)=>(await S(db,sql,...values).all()).results;
const isSha=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
const text=(value,max=400)=>typeof value==='string'&&value.trim()&&value.length<=max;
const exact=(value,keys,label)=>{
  if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).some(k=>!keys.includes(k))||keys.some(k=>!Object.hasOwn(value,k)))throw Error('invalid_'+label);
};
const sortObjects=list=>[...list].sort((a,b)=>canonicalJson(a).localeCompare(canonicalJson(b)));

async function github(path,token){
  const response=await fetchWithTimeout(`https://api.github.com${path}`,{
    headers:{Authorization:`Bearer ${token}`,Accept:'application/vnd.github+json','User-Agent':'cile-enrichment-approval','X-GitHub-Api-Version':'2022-11-28'}
  },10000);
  if(!response.ok)throw Error('github_approval_verification_failed');
  return response.json();
}
export async function verifiedManifest(env,prNumber,path,get=github){
  if(!env.GITHUB_REPOSITORY||!env.GITHUB_TOKEN||!env.CURATOR_LOGIN)throw Error('approval_environment_unavailable');
  if(!Number.isSafeInteger(prNumber)||prNumber<1||!/^[A-Za-z0-9._/-]{1,180}$/.test(path))throw Error('invalid_approval_request');
  const root=`/repos/${env.GITHUB_REPOSITORY}`;
  const pr=await get(`${root}/pulls/${prNumber}`,env.GITHUB_TOKEN);
  if(!pr.merged||pr.base?.ref!=='main'||pr.base?.repo?.full_name!==env.GITHUB_REPOSITORY||pr.head?.repo?.full_name!==env.GITHUB_REPOSITORY)throw Error('scientific_pr_not_merged');
  const reviews=[];
  for(let page=1;page<=20;page++){
    const part=await get(`${root}/pulls/${prNumber}/reviews?per_page=100&page=${page}`,env.GITHUB_TOKEN);
    reviews.push(...part);if(part.length<100)break;if(page===20)throw Error('review_pagination_incomplete');
  }
  const authoritative=reviews.filter(r=>r.user?.login===env.CURATOR_LOGIN&&r.user?.type==='User'&&['APPROVED','CHANGES_REQUESTED','DISMISSED'].includes(r.state));
  const review=authoritative.at(-1);
  if(!review||review.state!=='APPROVED'||review.commit_id!==pr.head.sha)throw Error('exact_head_human_approval_required');
  const file=await get(`${root}/contents/${path}?ref=${pr.head.sha}`,env.GITHUB_TOKEN);
  if(file.encoding!=='base64'||file.size>12000)throw Error('approval_manifest_invalid');
  let manifest;
  try{manifest=JSON.parse(atob(file.content.replace(/\s/g,'')))}catch{throw Error('approval_manifest_invalid')}
  return {manifest,approval:{repository:env.GITHUB_REPOSITORY,pr_number:prNumber,reviewed_commit:pr.head.sha,human_login:env.CURATOR_LOGIN,human_review_id:String(review.id),approved_at:review.submitted_at}};
}

function inspectFacts(value,state){
  if(!value||typeof value!=='object')return;
  if(!Array.isArray(value)&&Object.hasOwn(value,'evidence_span_ids')){
    state.total++;
    if(['ambiguous','not_verifiable'].includes(value.status))state.unresolved++;
  }
  for(const child of Object.values(value))inspectFacts(child,state);
}
async function proposalState(env,target){
  const proposal=await S(env.REVIEW_DB,'SELECT * FROM enrichment_proposals WHERE target_id=? AND input_sha256=? ORDER BY created_at DESC,proposal_id DESC LIMIT 1',target.target_id,target.input_sha256).first();
  if(!proposal)return null;
  let input;try{input=JSON.parse(proposal.payload_json)}catch{throw Error('proposal_integrity_failure')}
  if(await sha256(canonicalJson(input))!==proposal.payload_sha256||input.target_id!==target.target_id||input.input_sha256!==target.input_sha256)throw Error('proposal_integrity_failure');
  if(input.protocol_version!==PROTOCOL||input.codebook_version!==CODEBOOK)throw Error('proposal_contract_mismatch');
  if(input.source_coverage!=='full_text')throw Error('full_text_required');
  if(input.framework?.status!=='proposed'||!CLASSES.has(input.framework.primary))throw Error('six_class_coding_required');
  const facts={total:0,unresolved:0};inspectFacts(input,facts);
  if(facts.unresolved)throw Error('unresolved_mandatory_facts');
  if(!text(input.generated_by?.model,200)||!isSha(input.generated_by?.prompt_sha256))throw Error('accepted_calibration_required');
  return {proposal,input,facts};
}
async function sourceSnapshot(env,target,input){
  const list=[];
  for(const id of input.source_ids){
    const source=await S(env.REVIEW_DB,'SELECT source_id,provider,source_url,evidence_kind,content_sha256,storage_key,version_label,language,retention_basis,licence_status,observed_at FROM enrichment_sources WHERE source_id=? AND target_id=? AND input_sha256=?',id,target.target_id,target.input_sha256).first();
    if(!source||!isSha(source.content_sha256))throw Error('source_integrity_failure');
    const object=await env.REVIEW_EVIDENCE.get(source.storage_key);
    if(!object||await sha256(await object.text())!==source.content_sha256)throw Error('source_integrity_failure');
    const {storage_key,...publicHashFields}=source;
    list.push(publicHashFields);
  }
  if(!list.some(s=>s.evidence_kind==='full_text'))throw Error('full_text_required');
  return sha256(canonicalJson(sortObjects(list)));
}
async function referenceState(env,target,upTo=null){
  const suffix=upTo?' AND observed_at<=?':'';
  const params=upTo?[target.target_id,target.input_sha256,upTo]:[target.target_id,target.input_sha256];
  const observations=await rows(env.REVIEW_DB,`SELECT provider,direction,citing_identifier,cited_identifier,snapshot_id,observed_at FROM enrichment_citation_observations WHERE target_id=? AND input_sha256=?${suffix} ORDER BY provider,direction,snapshot_id,observation_id`,...params);
  const coverage=await rows(env.REVIEW_DB,`SELECT provider,direction,snapshot_id,returned_count,provider_count,next_cursor,status,observed_at FROM enrichment_citation_coverage WHERE target_id=? AND input_sha256=?${suffix} ORDER BY provider,direction,snapshot_id,coverage_id`,...params);
  if(!coverage.some(r=>r.direction==='outgoing')||!coverage.some(r=>r.direction==='incoming'))throw Error('reference_coverage_required');
  return {observations,coverage,hash:await sha256(canonicalJson({observations,coverage}))};
}
async function calibrationFor(env,input,calibrationId=null){
  const sql=calibrationId
    ?'SELECT * FROM enrichment_calibration_receipts WHERE calibration_id=?'
    :'SELECT * FROM enrichment_calibration_receipts WHERE protocol_version=? AND codebook_version=? AND model=? AND prompt_sha256=? ORDER BY approved_at DESC,calibration_id DESC LIMIT 1';
  const row=calibrationId
    ?await S(env.REVIEW_DB,sql,calibrationId).first()
    :await S(env.REVIEW_DB,sql,PROTOCOL,CODEBOOK,input.generated_by.model,input.generated_by.prompt_sha256).first();
  if(!row||row.model!==input.generated_by.model||row.prompt_sha256!==input.generated_by.prompt_sha256||row.protocol_version!==PROTOCOL||row.codebook_version!==CODEBOOK)throw Error('accepted_calibration_required');
  return row;
}
export async function completionPacket(env,targetId){
  const target=await S(env.REVIEW_DB,'SELECT * FROM enrichment_targets WHERE target_id=? AND active=1',targetId).first();
  if(!target)throw Error('target_not_found');
  const state=await proposalState(env,target);if(!state)throw Error('proposal_required');
  const source_snapshot_sha256=await sourceSnapshot(env,target,state.input);
  const reference=await referenceState(env,target);
  const calibration=await calibrationFor(env,state.input);
  const record=JSON.parse(target.record_json);
  return {
    status:'ready_for_human_review',
    candidate_id:record.id,
    manifest:{
      action:'approve_enrichment_completion',candidate_id:record.id,protocol_version:PROTOCOL,codebook_version:CODEBOOK,
      input_sha256:target.input_sha256,proposal_sha256:state.proposal.payload_sha256,source_snapshot_sha256,
      reference_snapshot_sha256:reference.hash,calibration_id:calibration.calibration_id,
      checklist:Object.fromEntries(CHECKS.map(k=>[k,null]))
    },
    reference_coverage:reference.coverage.map(({provider,direction,status,returned_count,provider_count,observed_at})=>({provider,direction,status,returned_count,provider_count,observed_at}))
  };
}
export async function importCalibrationApproval(env,{calibration_id,pr_number},get=github,now=Date.now()){
  if(!/^[A-Za-z0-9-]{8,100}$/.test(calibration_id||''))throw Error('invalid_calibration_id');
  const path=`scientific-approvals/enrichment-calibration-${calibration_id}.json`;
  const {manifest,approval}=await verifiedManifest(env,pr_number,path,get);
  const keys=['action','calibration_id','protocol_version','codebook_version','model','prompt_sha256','benchmark_sha256','metrics_sha256','benchmark_size','reference_checked_cases','full_text_cases','hard_cases',...CALIBRATION_CHECKS];
  exact(manifest,keys,'calibration_manifest');
  if(manifest.action!=='approve_enrichment_calibration'||manifest.calibration_id!==calibration_id||manifest.protocol_version!==PROTOCOL||manifest.codebook_version!==CODEBOOK||!text(manifest.model,200)||!isSha(manifest.prompt_sha256)||!isSha(manifest.benchmark_sha256)||!isSha(manifest.metrics_sha256))throw Error('calibration_manifest_mismatch');
  if(!Number.isInteger(manifest.benchmark_size)||manifest.benchmark_size<12||manifest.benchmark_size>18||manifest.reference_checked_cases!==manifest.benchmark_size||!Number.isInteger(manifest.full_text_cases)||manifest.full_text_cases<1||manifest.full_text_cases>manifest.benchmark_size||!Number.isInteger(manifest.hard_cases)||manifest.hard_cases<1||manifest.hard_cases>manifest.benchmark_size||CALIBRATION_CHECKS.some(k=>manifest[k]!==true))throw Error('calibration_acceptance_incomplete');
  const manifestHash=await sha256(canonicalJson(manifest));
  const existing=await S(env.REVIEW_DB,'SELECT * FROM enrichment_calibration_receipts WHERE calibration_id=?',calibration_id).first();
  if(existing){if(existing.manifest_sha256!==manifestHash)throw Error('calibration_receipt_conflict');return{calibration_id,replayed:true}}
  await S(env.REVIEW_DB,'INSERT INTO enrichment_calibration_receipts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
    calibration_id,PROTOCOL,CODEBOOK,manifest.model,manifest.prompt_sha256,manifest.benchmark_sha256,manifest.metrics_sha256,
    manifest.benchmark_size,manifest.reference_checked_cases,manifest.full_text_cases,manifest.hard_cases,manifestHash,
    approval.repository,approval.pr_number,approval.reviewed_commit,approval.human_login,approval.human_review_id,approval.approved_at,new Date(now).toISOString()).run();
  if(!await S(env.REVIEW_DB,'SELECT calibration_id FROM enrichment_calibration_receipts WHERE calibration_id=?',calibration_id).first())throw Error('calibration_receipt_readback_failed');
  return{calibration_id,replayed:false};
}
export async function importCompletionApproval(env,{target_id,pr_number},get=github,now=Date.now()){
  const packet=await completionPacket(env,target_id);
  const path=`scientific-approvals/enrichment-completion-${packet.candidate_id}.json`;
  const {manifest,approval}=await verifiedManifest(env,pr_number,path,get);
  const keys=['action','candidate_id','protocol_version','codebook_version','input_sha256','proposal_sha256','source_snapshot_sha256','reference_snapshot_sha256','calibration_id','checklist'];
  exact(manifest,keys,'completion_manifest');exact(manifest.checklist,CHECKS,'completion_checklist');
  const expected={...packet.manifest,checklist:Object.fromEntries(CHECKS.map(k=>[k,true]))};
  if(canonicalJson(manifest)!==canonicalJson(expected))throw Error('completion_manifest_mismatch');
  const target=await S(env.REVIEW_DB,'SELECT * FROM enrichment_targets WHERE target_id=? AND active=1',target_id).first();
  const state=await proposalState(env,target);await calibrationFor(env,state.input,manifest.calibration_id);
  const checklistHash=await sha256(canonicalJson(manifest.checklist)),manifestHash=await sha256(canonicalJson(manifest));
  const receiptId=await sha256(canonicalJson([target_id,target.input_sha256,state.proposal.proposal_id,manifestHash,approval.reviewed_commit]));
  const existing=await S(env.REVIEW_DB,'SELECT * FROM enrichment_adjudication_receipts WHERE target_id=? AND input_sha256=? AND proposal_id=?',target_id,target.input_sha256,state.proposal.proposal_id).first();
  if(existing){if(existing.manifest_sha256!==manifestHash)throw Error('adjudication_receipt_conflict');return{receipt_id:existing.receipt_id,replayed:true}}
  await S(env.REVIEW_DB,'INSERT INTO enrichment_adjudication_receipts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
    receiptId,target_id,target.input_sha256,state.proposal.proposal_id,state.proposal.payload_sha256,manifest.source_snapshot_sha256,
    manifest.reference_snapshot_sha256,manifest.calibration_id,checklistHash,manifestHash,approval.repository,approval.pr_number,
    approval.reviewed_commit,approval.human_login,approval.human_review_id,approval.approved_at,new Date(now).toISOString()).run();
  if(!await S(env.REVIEW_DB,'SELECT receipt_id FROM enrichment_adjudication_receipts WHERE receipt_id=?',receiptId).first())throw Error('adjudication_receipt_readback_failed');
  return{receipt_id:receiptId,replayed:false};
}
function latestCoverage(list){
  const by=new Map();
  for(const row of list){
    const key=row.provider+'|'+row.direction,prior=by.get(key);
    if(!prior||String(row.observed_at)>String(prior.observed_at))by.set(key,row);
  }
  return [...by.values()].sort((a,b)=>(a.provider+a.direction).localeCompare(b.provider+b.direction));
}
export async function publicCompletionState(env,candidateId){
  const target=await S(env.REVIEW_DB,'SELECT * FROM enrichment_targets WHERE record_id=? AND active=1',candidateId).first();
  if(!target)return{candidate_id:candidateId,status:'not_registered',completed:false,completed_at:null,protocol_version:null,codebook_version:null,reference_coverage:[],outgoing_references:{identifiers:[],total_observed:0,truncated:false}};
  const coverage=await rows(env.REVIEW_DB,'SELECT provider,direction,status,returned_count,provider_count,observed_at FROM enrichment_citation_coverage WHERE target_id=? AND input_sha256=? ORDER BY observed_at',target.target_id,target.input_sha256);
  const outgoing=await rows(env.REVIEW_DB,"SELECT DISTINCT cited_identifier identifier FROM enrichment_citation_observations WHERE target_id=? AND input_sha256=? AND direction='outgoing' ORDER BY cited_identifier LIMIT 501",target.target_id,target.input_sha256);
  const total=Number((await S(env.REVIEW_DB,"SELECT COUNT(DISTINCT cited_identifier) n FROM enrichment_citation_observations WHERE target_id=? AND input_sha256=? AND direction='outgoing'",target.target_id,target.input_sha256).first())?.n||0);
  const references={identifiers:outgoing.slice(0,500).map(x=>x.identifier),total_observed:total,truncated:total>500};
  const proposal=await S(env.REVIEW_DB,'SELECT * FROM enrichment_proposals WHERE target_id=? AND input_sha256=? ORDER BY created_at DESC,proposal_id DESC LIMIT 1',target.target_id,target.input_sha256).first();
  if(!proposal)return{candidate_id:candidateId,status:'not_attested',completed:false,completed_at:null,protocol_version:null,codebook_version:null,reference_coverage:latestCoverage(coverage),outgoing_references:references};
  const receipt=await S(env.REVIEW_DB,'SELECT * FROM enrichment_adjudication_receipts WHERE target_id=? AND input_sha256=? AND proposal_id=? ORDER BY approved_at DESC LIMIT 1',target.target_id,target.input_sha256,proposal.proposal_id).first();
  if(!receipt){
    const older=await S(env.REVIEW_DB,'SELECT receipt_id FROM enrichment_adjudication_receipts WHERE target_id=? LIMIT 1',target.target_id).first();
    return{candidate_id:candidateId,status:older?'stale':'not_attested',completed:false,completed_at:null,protocol_version:null,codebook_version:null,reference_coverage:latestCoverage(coverage),outgoing_references:references};
  }
  try{
    const state=await proposalState(env,target);
    if(state.proposal.payload_sha256!==receipt.proposal_sha256)throw Error('stale_receipt');
    if(await sourceSnapshot(env,target,state.input)!==receipt.source_snapshot_sha256)throw Error('stale_receipt');
    if((await referenceState(env,target,receipt.approved_at)).hash!==receipt.reference_snapshot_sha256)throw Error('stale_receipt');
    await calibrationFor(env,state.input,receipt.calibration_id);
    return{candidate_id:candidateId,status:'accepted',completed:true,completed_at:receipt.approved_at,protocol_version:PROTOCOL,codebook_version:CODEBOOK,reference_coverage:latestCoverage(coverage),outgoing_references:references};
  }catch{
    return{candidate_id:candidateId,status:'withheld',completed:false,completed_at:null,protocol_version:null,codebook_version:null,reference_coverage:latestCoverage(coverage),outgoing_references:references};
  }
}
