import { sha256 } from './review-v2.js';

export const DEVELOPMENT_CHECKPOINT_PROTOCOL='CILE-FULLTEXT-DEV-CHUNK-1';
export const ASSESSMENT_REFERENCE_PROTOCOL='CILE-ASSESSMENT-REFERENCE-1';
export const ASSESSMENT_COMPARISON_PROTOCOL='CILE-ASSESSMENT-COMPARISON-1';
const HEX64=/^[0-9a-f]{64}$/;
const CANDIDATE=/^CAND-[A-Za-z0-9][A-Za-z0-9._-]{1,199}$/;
const CHUNK=/^chunk-[1-9][0-9]{0,3}$/;
const PUBLIC_REVISION=/^[0-9a-f]{64}$/;
const allowedDevelopmentIdentity=new Set(['protocol','candidate_id','extractor_fingerprint','request_sha256','chunk_id']);
const allowedReferenceIdentity=new Set(['protocol','candidate_id','input_sha256','source_snapshot_sha256','request_sha256','stage']);
const allowedComparisonIdentity=new Set(['protocol','candidate_id','input_sha256','source_snapshot_sha256','proposal_revision','reference_sha256','request_sha256','stage']);

function object(value){return value&&typeof value==='object'&&!Array.isArray(value)}
function exactKeys(value,allowed){return object(value)&&Object.keys(value).every(key=>allowed.has(key))&&Object.keys(value).length===allowed.size}
function failure(code,status=422){const error=Error(code);error.code=code;error.status=status;return error}
function protocolOf(value){return object(value)&&typeof value.protocol==='string'?value.protocol:null}
function identityFields(protocol){
  if(protocol===DEVELOPMENT_CHECKPOINT_PROTOCOL)return allowedDevelopmentIdentity;
  if(protocol===ASSESSMENT_REFERENCE_PROTOCOL)return allowedReferenceIdentity;
  if(protocol===ASSESSMENT_COMPARISON_PROTOCOL)return allowedComparisonIdentity;
  throw failure('development_checkpoint_invalid');
}
function allowedStored(protocol){return new Set([...identityFields(protocol),'output'])}

function validateAssessmentReferenceOutput(output){
  if(!object(output)||Object.keys(output).length!==1||!object(output.assessment))throw failure('development_checkpoint_invalid');
  const raw=JSON.stringify(output.assessment);
  if(raw.length<2||raw.length>480000)throw failure('development_checkpoint_invalid');
}
function validateAssessmentComparisonOutput(output){
  if(!object(output)||Object.keys(output).length!==1||!object(output.comparison))throw failure('development_checkpoint_invalid');
  const comparison=output.comparison;
  const allowed=new Set(['protocol','candidate_id','input_sha256','source_snapshot_sha256','proposal_revision','reference_sha256','assessor','source_fidelity','omissions','classification_agreement','field_accuracy','mandatory_disagreement_paths','optional_disagreement_paths','compared_at']);
  if(!exactKeys(comparison,allowed)||comparison.protocol!==ASSESSMENT_COMPARISON_PROTOCOL||!CANDIDATE.test(comparison.candidate_id)||!HEX64.test(comparison.input_sha256)||!HEX64.test(comparison.source_snapshot_sha256)||!PUBLIC_REVISION.test(comparison.proposal_revision)||!HEX64.test(comparison.reference_sha256))throw failure('development_checkpoint_invalid');
  if(!object(comparison.assessor)||Object.keys(comparison.assessor).some(key=>!['agent','model','prompt_sha256'].includes(key))||!['agent','model','prompt_sha256'].every(key=>Object.hasOwn(comparison.assessor,key))||typeof comparison.assessor.agent!=='string'||!comparison.assessor.agent.trim()||comparison.assessor.agent.length>200||typeof comparison.assessor.model!=='string'||!comparison.assessor.model.trim()||comparison.assessor.model.length>300||!HEX64.test(comparison.assessor.prompt_sha256))throw failure('development_checkpoint_invalid');
  if(!['pass','fail','partial','uncertain'].includes(comparison.source_fidelity)||!['none','nonmaterial','material','uncertain'].includes(comparison.omissions)||!['agree','partial','disagree','uncertain'].includes(comparison.classification_agreement)||!['pass','fail','partial','uncertain'].includes(comparison.field_accuracy))throw failure('development_checkpoint_invalid');
  for(const name of ['mandatory_disagreement_paths','optional_disagreement_paths']){
    const paths=comparison[name];
    if(!Array.isArray(paths)||paths.length>200||new Set(paths).size!==paths.length||paths.some(path=>typeof path!=='string'||!path.trim()||path.length>300))throw failure('development_checkpoint_invalid');
  }
  if(typeof comparison.compared_at!=='string'||!Number.isFinite(Date.parse(comparison.compared_at)))throw failure('development_checkpoint_invalid');
}

export function validateDevelopmentCheckpoint(value,{stored=false}={}){
  const protocol=protocolOf(value),allowed=stored?allowedStored(protocol):identityFields(protocol);
  if(!exactKeys(value,allowed)||!CANDIDATE.test(value.candidate_id))throw failure('development_checkpoint_invalid');
  if(protocol===DEVELOPMENT_CHECKPOINT_PROTOCOL){
    if(!HEX64.test(value.extractor_fingerprint)||!HEX64.test(value.request_sha256)||!CHUNK.test(value.chunk_id))throw failure('development_checkpoint_invalid');
    if(stored&&(!object(value.output)||Object.keys(value.output).length!==1||!Array.isArray(value.output.atoms)))throw failure('development_checkpoint_invalid');
    return value;
  }
  if(!HEX64.test(value.input_sha256)||!HEX64.test(value.source_snapshot_sha256)||!HEX64.test(value.request_sha256))throw failure('development_checkpoint_invalid');
  if(protocol===ASSESSMENT_REFERENCE_PROTOCOL){
    if(value.stage!=='reference')throw failure('development_checkpoint_invalid');
    if(stored)validateAssessmentReferenceOutput(value.output);
    return value;
  }
  if(protocol===ASSESSMENT_COMPARISON_PROTOCOL){
    if(value.stage!=='comparison'||!PUBLIC_REVISION.test(value.proposal_revision)||!HEX64.test(value.reference_sha256))throw failure('development_checkpoint_invalid');
    if(stored){
      validateAssessmentComparisonOutput(value.output);
      const c=value.output.comparison;
      if(c.candidate_id!==value.candidate_id||c.input_sha256!==value.input_sha256||c.source_snapshot_sha256!==value.source_snapshot_sha256||c.proposal_revision!==value.proposal_revision||c.reference_sha256!==value.reference_sha256)throw failure('development_checkpoint_identity_mismatch',409);
    }
    return value;
  }
  throw failure('development_checkpoint_invalid');
}

export async function developmentCheckpointKey(identity){
  const value=validateDevelopmentCheckpoint(identity);
  let parts;
  if(value.protocol===DEVELOPMENT_CHECKPOINT_PROTOCOL)parts=[value.protocol,value.candidate_id,value.extractor_fingerprint,value.request_sha256,value.chunk_id];
  else if(value.protocol===ASSESSMENT_REFERENCE_PROTOCOL)parts=[value.protocol,value.candidate_id,value.input_sha256,value.source_snapshot_sha256,value.request_sha256,value.stage];
  else parts=[value.protocol,value.candidate_id,value.input_sha256,value.source_snapshot_sha256,value.proposal_revision,value.reference_sha256,value.request_sha256,value.stage];
  const digest=await sha256(JSON.stringify(parts));
  return value.protocol===DEVELOPMENT_CHECKPOINT_PROTOCOL?'calibration-development:'+digest:'assessment-frontier:'+digest;
}

function identityOf(value){
  return Object.fromEntries([...identityFields(value.protocol)].map(key=>[key,value[key]]));
}
function sameIdentity(a,b){return [...identityFields(a.protocol)].every(key=>a[key]===b[key])}

export async function readDevelopmentCheckpoint(store,identity){
  const expected=validateDevelopmentCheckpoint(identity),key=await developmentCheckpointKey(expected),objectValue=await store.get(key);
  if(!objectValue){
    const out={status:'missing',protocol:expected.protocol,candidate_id:expected.candidate_id,request_sha256:expected.request_sha256};
    if(expected.protocol===DEVELOPMENT_CHECKPOINT_PROTOCOL)out.chunk_id=expected.chunk_id;
    else out.stage=expected.stage;
    return out;
  }
  let stored;
  try{stored=JSON.parse(await objectValue.text())}catch{throw failure('development_checkpoint_corrupt',500)}
  try{validateDevelopmentCheckpoint(stored,{stored:true})}catch(error){if(error?.code==='development_checkpoint_identity_mismatch')throw error;throw failure('development_checkpoint_corrupt',500)}
  if(!sameIdentity(expected,stored))throw failure('development_checkpoint_identity_mismatch',409);
  return {status:'found',checkpoint:stored};
}

export async function writeDevelopmentCheckpoint(store,checkpoint){
  const stored=validateDevelopmentCheckpoint(checkpoint,{stored:true}),identity=identityOf(stored),key=await developmentCheckpointKey(identity);
  const body=JSON.stringify(stored);
  if(body.length>500000)throw failure('development_checkpoint_too_large',413);
  try{await store.put(key,body)}catch(error){
    if(error?.message==='immutable_content_conflict')throw failure('development_checkpoint_conflict',409);
    throw error;
  }
  const out={status:'stored',protocol:stored.protocol,candidate_id:stored.candidate_id,request_sha256:stored.request_sha256,output_sha256:await sha256(JSON.stringify(stored.output))};
  if(stored.protocol===DEVELOPMENT_CHECKPOINT_PROTOCOL)out.chunk_id=stored.chunk_id;
  else out.stage=stored.stage;
  return out;
}
