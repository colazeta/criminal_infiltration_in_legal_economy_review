/* The current extraction is a relational graph. Payload JSON is immutable input
   history, used only as an integrity commitment, never as the public read source. */
import contract from '../../ontology/modules/extraction-relations.json' with {type:'json'};
import {canonicalJson,sha256} from './review-v2.js';

export const RELATIONS_VERSION='CILE-EXTRACTION-RELATIONS-1';
const GROUPS={studies:['study_id'],datasets:['dataset_id','study_id'],analyses:['analysis_id','study_id'],variable_uses:['variable_use_id','analysis_id'],findings:['finding_id','analysis_id']};
const LINKS={analyses:['analysis_datasets','analysis_id','dataset_ids','dataset_id'],variable_uses:['variable_datasets','variable_use_id','dataset_ids','dataset_id'],findings:['finding_variables','finding_id','variable_use_ids','variable_use_id']};
const OWNERS=['study_id','dataset_id','analysis_id','variable_use_id','finding_id','secondary_category'];
const TABLES=Object.keys(contract.tables).filter(t=>t!=='enrichment_normalization_receipts');
const S=(db,sql,...values)=>db.prepare(sql).bind(...values);
const fail=()=>{throw Error('normalized_extraction_integrity')};
const ordered=values=>[...values].sort((a,b)=>a.position-b.position);

export function normalizedReadStatements(db,id){
  return TABLES.map(t=>S(db,`SELECT * FROM ${t} WHERE proposal_id=?`,id));
}
export function reconstructExtraction(proposal,results,children,framework){
  const r=Object.fromEntries(TABLES.map((t,i)=>[t,results[i].results]));
  const details=r.enrichment_proposal_details;
  if(details.length!==1||framework.length!==1||r.enrichment_framework_alternatives.length!==1)fail();
  const d=details[0],out={schema_version:1,protocol_version:proposal.protocol_version,codebook_version:proposal.codebook_version,
    target_id:proposal.target_id,input_sha256:proposal.input_sha256,generated_by:{agent:d.agent,model:d.model,prompt_sha256:d.prompt_sha256},
    source_ids:ordered(r.enrichment_proposal_sources).map(s=>s.source_id),source_coverage:d.source_coverage,
    spans:ordered(r.enrichment_spans).map(s=>({id:s.span_id,source_id:s.source_id,start_offset:s.start_offset,end_offset:s.end_offset,locator:s.locator}))};
  function facts(scope,owner=null){
    const field=GROUPS[scope]?.[0]||(scope==='secondary'?'secondary_category':null);
    const values=r.enrichment_facts.filter(f=>f.scope===scope&&(!field||f[field]===owner));
    if(canonicalJson(values.map(f=>f.field_name).sort())!==canonicalJson([...contract.fact_fields[scope]].sort()))fail();
    return Object.fromEntries(values.map(f=>[f.field_name,{status:f.status,value:f.value,origin:f.origin,
      evidence_span_ids:ordered(r.enrichment_fact_evidence.filter(e=>e.fact_id===f.fact_id)).map(e=>e.span_id)}]));
  }
  Object.assign(out,facts('overview'));
  for(const [group,[key,parent]] of Object.entries(GROUPS)){
    const members=children[group],order=ordered(r['enrichment_'+group+'_order']);
    if(order.length!==members.length)fail();
    out[group]=order.map(o=>{
      const row=members.find(m=>m[key]===o[key]);if(!row)fail();
      const value={id:row[key],...(parent?{[parent]:row[parent]}:{}),...facts(group,row[key])};
      if(LINKS[group]){const [table,owner,property,linked]=LINKS[group];value[property]=ordered(r['enrichment_'+table].filter(l=>l[owner]===row[key])).map(l=>l[linked])}
      return value;
    });
  }
  out.framework={status:framework[0].classification_status,primary:framework[0].primary_category,...facts('framework'),
    secondary:ordered(r.enrichment_secondary_classes).map(s=>({category:s.category,...facts('secondary',s.category)})),
    alternative:r.enrichment_framework_alternatives[0].category};
  return out;
}

export function allReadStatements(db,id){
  return [...normalizedReadStatements(db,id),...Object.entries(GROUPS).map(([group,[key,parent]])=>S(db,`SELECT ${key}${parent?','+parent:''} FROM enrichment_${group} WHERE proposal_id=?`,id)),
    S(db,'SELECT primary_category,classification_status FROM enrichment_framework_proposals WHERE proposal_id=?',id)];
}
export function rebuildFromReadback(proposal,result){
  const children=Object.fromEntries(Object.keys(GROUPS).map((g,i)=>[g,result[TABLES.length+i].results]));
  return reconstructExtraction(proposal,result.slice(0,TABLES.length),children,result.at(-1).results);
}
export async function readNormalizedExtraction(db,proposal,{requireReceipt=true}={}){
  if(proposal.payload_json!==undefined&&await sha256(canonicalJson(JSON.parse(proposal.payload_json)))!==proposal.payload_sha256)fail();
  if(requireReceipt){
    const receipt=await S(db,'SELECT source_sha256,rebuilt_sha256 FROM enrichment_normalization_receipts WHERE proposal_id=?',proposal.proposal_id).first();
    if(!receipt||receipt.source_sha256!==proposal.payload_sha256||receipt.rebuilt_sha256!==proposal.payload_sha256)fail();
  }
  const results=[];for(const stmt of allReadStatements(db,proposal.proposal_id))results.push(await stmt.all());
  const value=rebuildFromReadback(proposal,results);
  if(await sha256(canonicalJson(value))!==proposal.payload_sha256)fail();
  return value;
}

export async function normalizedStatements(db,id,input){
  const statements=[];
  const add=(name,columns,values)=>statements.push(S(db,`INSERT INTO enrichment_${name} (${columns.join(',')}) VALUES (${columns.map(()=>'?').join(',')})`,...values));
  add('proposal_details',['proposal_id','source_coverage','agent','model','prompt_sha256'],[id,input.source_coverage,input.generated_by.agent,input.generated_by.model,input.generated_by.prompt_sha256]);
  input.source_ids.forEach((source,i)=>add('proposal_sources',['proposal_id','source_id','position'],[id,source,i+1]));
  input.spans.forEach((span,i)=>add('spans',['proposal_id','span_id','source_id','position','start_offset','end_offset','locator'],[id,span.id,span.source_id,i+1,span.start_offset,span.end_offset,span.locator]));
  async function facts(scope,value,owner=null){
    const key=GROUPS[scope]?.[0]||(scope==='secondary'?'secondary_category':null);
    for(const field of contract.fact_fields[scope]){
      const fact=value[field],factId=await sha256(canonicalJson([id,scope,owner,field]));
      add('facts',['fact_id','proposal_id','scope','field_name',...OWNERS,'status','value','origin'],[factId,id,scope,field,...OWNERS.map(k=>k===key?owner:null),fact.status,fact.value,fact.origin]);
      fact.evidence_span_ids.forEach((span,i)=>add('fact_evidence',['fact_id','proposal_id','span_id','position'],[factId,id,span,i+1]));
    }
  }
  await facts('overview',input);
  for(const [group,[key]] of Object.entries(GROUPS)){
    for(const [position,value] of input[group].entries()){
      add(group+'_order',['proposal_id',key,'position'],[id,value.id,position+1]);
      await facts(group,value,value.id);
      if(LINKS[group]){const [table,owner,property,linked]=LINKS[group];value[property].forEach((link,i)=>add(table,['proposal_id',owner,linked,'position'],[id,value.id,link,i+1]))}
    }
  }
  for(const [position,value] of input.framework.secondary.entries()){
    add('secondary_classes',['proposal_id','category','position'],[id,value.category,position+1]);await facts('secondary',value,value.category);
  }
  add('framework_alternatives',['proposal_id','category'],[id,input.framework.alternative]);
  await facts('framework',input.framework);
  return statements;
}

export async function persistNormalized(db,proposal,input,prefix=[],{kind='native',now=Date.now()}={}){
  if(typeof db.batchValidated!=='function')throw Error('validated_transaction_required');
  const normalized=await normalizedStatements(db,proposal.proposal_id,input),encoded=canonicalJson(input);
  if(await sha256(encoded)!==proposal.payload_sha256)fail();
  const receiptId=await sha256(proposal.proposal_id+RELATIONS_VERSION);
  const receipt=S(db,'INSERT INTO enrichment_normalization_receipts VALUES (?,?,?,?,?,?,?)',receiptId,proposal.proposal_id,RELATIONS_VERSION,proposal.payload_sha256,proposal.payload_sha256,kind,new Date(now).toISOString());
  const writes=[...prefix,...normalized];if(writes.length>15000)throw Error('proposal_transaction_limit');
  // SQL readback is rebuilt and compared before the transaction can commit.
  let replayed=false;
  try{
    await db.batchValidated(writes,allReadStatements(db,proposal.proposal_id),
      results=>canonicalJson(rebuildFromReadback(proposal,results))===encoded,receipt);
  }catch(error){
    // A competing identical transaction may have committed after the initial read.
    const existing=await S(db,'SELECT receipt_id FROM enrichment_normalization_receipts WHERE proposal_id=?',proposal.proposal_id).first();
    if(!existing)throw error;
    if(canonicalJson(await readNormalizedExtraction(db,proposal))!==encoded)fail();
    replayed=true;
  }
  await readNormalizedExtraction(db,proposal);
  return {receipt_id:receiptId,proposal_id:proposal.proposal_id,transformation_version:RELATIONS_VERSION,replayed};
}
