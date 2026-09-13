/* Owner-authorised display projection, NOT scientific approval or a private API.
   No new persistence: revalidate immutable evidence and derive a closed response. */
import cycle from '../../config/archive-cycle.json' with {type:'json'};
import schema from '../../schema/public-paper-research.schema.json' with {type:'json'};
import {validateExtraction, validateShape, normalDoi} from './paper-enrichment.js';
import {canonicalJson, sha256} from './review-v2.js';
export const PUBLIC_RESEARCH_PATH='/api/public-paper-research';
export const validCandidate=id=>typeof id==='string'&&/^CAND-[A-Za-z0-9-]{1,100}$/.test(id);
const TOP=['protocol_version','codebook_version','source_coverage','summary','contribution','research_question','infiltration_definition','infiltration_operationalisation','authors_limitations'];
const GROUPS=['studies','datasets','analyses','variable_uses','findings'];
const query=(db,sql,...v)=>db.prepare(sql).bind(...v);
export function safeResearchUrl(value){
  try{
    if(typeof value!=='string'||value.length>2000||/[\u0000-\u0020\u007f]/u.test(value))return false;
    const u=new URL(value);
    return u.protocol==='https:'&&!!u.hostname&&!u.username&&!u.password
      &&!/(^|\.)(localhost|workers\.dev|r2\.dev|internal)$/i.test(u.hostname)
      &&!/^\d+(\.\d+){3}$/.test(u.hostname)&&!u.hostname.includes(':')
      &&![...u.searchParams.keys()].some(k=>/(token|secret|signature|session|api.?key|authorization|^sig$|^key$|x-amz|x-goog)/i.test(k))
      &&!/(token|secret|signature|session|authorization)=/i.test(u.hash);
  }catch{return false}
}
function safeText(value,privateIds){
  if(typeof value!=='string')return;
  if(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/u.test(value)
    || /\b(sk-(?:proj-)?[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._-]{12,}|-----BEGIN .*PRIVATE KEY-----)/i.test(value)
    || privateIds.some(id=>id.length>=12&&value.includes(id)))throw Error('publication_boundary');
  for(const token of value.match(/https?:\/\/[^\s<>"']+/g)||[])if(!safeResearchUrl(token))throw Error('publication_boundary');
}
const words=s=>s.normalize('NFKC').toLowerCase().match(/[\p{L}\p{N}]+/gu)||[];
const COPY_WINDOW_WORDS=5,MAX_PUBLIC_COPY_WINDOWS=20000;
function checkParaphrases(research,sources){
  // Fail closed on substantive verbatim overlap without retaining source-sized
  // n-gram sets. Only bounded public windows are retained; private source text is
  // normalised once and scanned with a five-token rolling buffer.
  const byLast=new Map(),seen=new Set();let count=0;
  function add(pattern){
    const key=pattern.join(' ');if(seen.has(key))return;seen.add(key);
    if(++count>MAX_PUBLIC_COPY_WINDOWS)throw Error('publication_limit');
    const last=pattern.at(-1),list=byLast.get(last)||[];list.push(pattern);byLast.set(last,list);
  }
  function visit(v){
    if(!v||typeof v!=='object')return;
    if(Object.hasOwn(v,'evidence_span_ids')&&typeof v.value==='string'){
      const w=words(v.value);for(let i=0;i+COPY_WINDOW_WORDS<=w.length;i++)add(w.slice(i,i+COPY_WINDOW_WORDS));
    }
    for(const child of Object.values(v))visit(child);
  }
  visit(research);if(!count)return;
  for(const source of sources){
    const tail=[],normalised=source.text.normalize('NFKC');
    for(const match of normalised.matchAll(/[\p{L}\p{N}]+/gu)){
      const token=match[0].toLowerCase();tail.push(token);if(tail.length>COPY_WINDOW_WORDS)tail.shift();
      if(tail.length!==COPY_WINDOW_WORDS)continue;
      for(const pattern of byLast.get(token)||[]){
        let same=true;for(let i=0;i<COPY_WINDOW_WORDS;i++)if(tail[i]!==pattern[i]){same=false;break}
        if(same)throw Error('publication_boundary');
      }
    }
  }
}
export function validatePublicResearch(payload){
  validateShape(payload,schema,'$',schema);
  if((payload.availability==='available')!==(payload.research!==null))throw Error('public_availability_mismatch');
  if(payload.availability!=='not_registered'&&!payload.candidate)throw Error('public_identity_required');
  if(payload.candidate&&(!validCandidate(payload.candidate.id)||payload.candidate.sourceLinks.some(u=>!safeResearchUrl(u))))throw Error('public_identity_invalid');
  if(payload.research){
    if(payload.research.sources.some(s=>!safeResearchUrl(s.url)))throw Error('public_source_url');
    const refs=new Set(payload.research.sources.map(s=>s.id));
    if(payload.research.spans.some(s=>!refs.has(s.source_id)))throw Error('public_source_scope');
  }
  return payload;
}
async function seal(candidate,availability,research=null){
  const out={schema_version:1,projection_version:'CILE-PUBLIC-RESEARCH-1',candidate,availability,research};
  out.revision=await sha256(canonicalJson(out));return validatePublicResearch(out);
}
export async function projectResearch(target,proposal,sources){
  const raw=JSON.parse(target.record_json);
  const candidate={id:raw.id,title:raw.title,doi:normalDoi(raw.doi),sourceLinks:raw.sourceLinks};
  if(candidate.id!==target.record_id||await sha256(canonicalJson(raw))!==target.input_sha256)throw Error('identity_integrity');
  if(!proposal)return seal(candidate,'not_assessed');
  if(proposal.input_sha256!==target.input_sha256)return seal(candidate,'stale');
  try{
    const input=JSON.parse(proposal.payload_json);
    if(await sha256(canonicalJson(input))!==proposal.payload_sha256)throw Error('proposal_integrity');
    for(const source of sources)if(await sha256(source.text)!==source.content_sha256)throw Error('source_integrity');
    validateExtraction(input,target,sources);
    if(!/^\d{4}-\d{2}-\d{2}T/.test(proposal.created_at)||!Number.isFinite(Date.parse(proposal.created_at)))throw Error('date_invalid');
    const sourceMap=new Map(input.source_ids.map((id,i)=>[id,`source-${i+1}`]));
    const spanMap=new Map(input.spans.map((s,i)=>[s.id,`evidence-${i+1}`]));
    const idMaps=Object.fromEntries(GROUPS.map(g=>[g,new Map(input[g].map((r,i)=>[r.id,`${g}-${i+1}`]))]));
    function fact(v){return{status:v.status,value:v.value,origin:v.origin,evidence_span_ids:v.evidence_span_ids.map(id=>spanMap.get(id))}}
    function item(v,g){const out={};for(const[k,value]of Object.entries(v)){
      if(k==='id')out[k]=idMaps[g].get(value);
      else if(k==='study_id')out[k]=idMaps.studies.get(value);
      else if(k==='analysis_id')out[k]=idMaps.analyses.get(value);
      else if(k==='dataset_ids')out[k]=value.map(id=>idMaps.datasets.get(id));
      else if(k==='variable_use_ids')out[k]=value.map(id=>idMaps.variable_uses.get(id));
      else out[k]=fact(value);
    }return out}
    const research=Object.fromEntries(TOP.map(k=>[k,typeof input[k]==='object'?fact(input[k]):input[k]]));
    for(const g of GROUPS)research[g]=input[g].map(v=>item(v,g));
    research.framework={status:input.framework.status,primary:input.framework.primary,rationale:fact(input.framework.rationale),secondary:input.framework.secondary.map(s=>({category:s.category,rationale:fact(s.rationale)})),alternative:input.framework.alternative};
    research.assessment_state='unreviewed_proposal';
    research.generation_kind=input.generated_by.model?'automated':'unspecified';
    research.updated_at=proposal.created_at;
    research.internal_notes='not_released';
    research.sources=input.source_ids.map(id=>{const s=sources.find(s=>s.source_id===id);return{id:sourceMap.get(id),url:s.source_url,kind:s.evidence_kind,version:s.version_label,checked_at:s.observed_at}});
    // Private span locators can themselves contain evidence quotations. Publish a
    // stable ordinal locator only; exact offsets/labels remain private evidence.
    research.spans=input.spans.map((s,i)=>({id:spanMap.get(s.id),source_id:sourceMap.get(s.source_id),locator:`evidence segment ${i+1}`}));
    const ids=[target.target_id,proposal.proposal_id,...sources.flatMap(s=>[s.source_id,s.storage_key]),...input.spans.map(s=>s.id)];
    function inspect(v){if(typeof v==='string')safeText(v,ids);else if(v&&typeof v==='object')for(const x of Object.values(v))inspect(x)}inspect(research);
    checkParaphrases(research,sources);
    if(JSON.stringify(research).length>750000)throw Error('publication_limit');
    return await seal(candidate,'available',research);
  }catch{return seal(candidate,'withheld')}
}
export async function readPublicResearch(env,id){
  if(!validCandidate(id))throw Error('invalid_candidate');
  const db=env.REVIEW_DB;
  const target=await query(db,'SELECT * FROM enrichment_targets WHERE record_id=? AND cycle_id=? AND active=1',id,cycle.review_id).first();
  if(!target)return seal(null,'not_registered');
  const proposal=await query(db,'SELECT * FROM enrichment_proposals WHERE target_id=? ORDER BY CASE WHEN input_sha256=? THEN 0 ELSE 1 END,created_at DESC,proposal_id DESC LIMIT 1',target.target_id,target.input_sha256).first();
  const sources=[];
  if(proposal&&proposal.input_sha256===target.input_sha256){
    try{
      const input=JSON.parse(proposal.payload_json);
      if(!Array.isArray(input.source_ids)||input.source_ids.length>20)throw Error('source_limit');
      let total=0;
      for(const id of input.source_ids){
        const s=await query(db,'SELECT * FROM enrichment_sources WHERE source_id=? AND target_id=? AND input_sha256=?',id,target.target_id,target.input_sha256).first();
        if(!s)throw Error('missing_source');
        const object=await env.REVIEW_EVIDENCE.get(s.storage_key);if(!object)throw Error('missing_evidence');
        const text=await object.text();total+=text.length;if(total>8000000)throw Error('source_limit');sources.push({...s,text});
      }
    }catch{
      // Preserve identity but publish neither unverifiable content nor private errors.
      const empty=await projectResearch(target,null,[]);return seal(empty.candidate,'withheld');
    }
  }
  return projectResearch(target,proposal,sources);
}
export async function publicResearchAudit(env){
  const targets=(await query(env.REVIEW_DB,'SELECT record_id FROM enrichment_targets WHERE active=1 AND cycle_id=? ORDER BY record_id LIMIT 10001',cycle.review_id).all()).results;
  if(targets.length>10000)throw Error('audit_limit');
  const counts={registered:targets.length,available:0,not_assessed:0,stale:0,withheld:0,classified:0,automated:0};
  counts.stored_proposals=Number((await query(env.REVIEW_DB,'SELECT COUNT(*) n FROM enrichment_proposals').first()).n);
  counts.stored_sources=Number((await query(env.REVIEW_DB,'SELECT COUNT(*) n FROM enrichment_sources').first()).n);
  const records=[];
  for(const target of targets){const out=await readPublicResearch(env,target.record_id);counts[out.availability]++;if(out.research?.framework.primary)counts.classified++;if(out.research?.generation_kind==='automated')counts.automated++;records.push({id:target.record_id,availability:out.availability,revision:out.revision})}
  return{schema_version:1,projection_version:'CILE-PUBLIC-RESEARCH-1',counts,records};
}
export async function servePublicResearch(request,store){
  const h={'Cache-Control':'no-store','Content-Type':'application/json','X-Content-Type-Options':'nosniff','Access-Control-Allow-Origin':'https://colazeta.github.io','Vary':'Origin'};
  const response=(data,status)=>Response.json(data,{status,headers:h});
  if(request.method==='OPTIONS')return new Response(null,{status:204,headers:{...h,'Access-Control-Allow-Methods':'GET','Access-Control-Max-Age':'300'}});
  const u=new URL(request.url);
  if(request.method!=='GET')return response({error:'method_not_allowed'},405);
  if([...u.searchParams.keys()].some(k=>k!=='id')||u.searchParams.getAll('id').length!==1||!validCandidate(u.searchParams.get('id')))return response({error:'invalid_candidate'},400);
  if(!store)return response({error:'research_temporarily_unavailable'},503);
  try{
    // Do not forward credentials, cookies or arbitrary request bodies/paths to private storage.
    const internal=await store.fetch(new Request('https://enrichment.internal/public-research?id='+encodeURIComponent(u.searchParams.get('id'))));
    if(!internal.ok)return response({error:'research_temporarily_unavailable'},503);
    const data=await internal.json();validatePublicResearch(data);return response(data,200);
  }catch{return response({error:'research_temporarily_unavailable'},503)}
}