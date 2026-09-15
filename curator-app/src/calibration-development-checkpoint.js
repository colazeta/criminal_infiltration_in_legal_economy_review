import { sha256 } from './review-v2.js';

export const DEVELOPMENT_CHECKPOINT_PROTOCOL='CILE-FULLTEXT-DEV-CHUNK-1';
const HEX64=/^[0-9a-f]{64}$/;
const CANDIDATE=/^CAND-[A-Z0-9][A-Z0-9._-]{1,199}$/;
const CHUNK=/^chunk-[1-9][0-9]{0,3}$/;
const allowedIdentity=new Set(['protocol','candidate_id','extractor_fingerprint','request_sha256','chunk_id']);
const allowedStored=new Set([...allowedIdentity,'output']);

function object(value){return value&&typeof value==='object'&&!Array.isArray(value)}
function exactKeys(value,allowed){return object(value)&&Object.keys(value).every(key=>allowed.has(key))&&Object.keys(value).length===allowed.size}
function failure(code,status=422){const error=Error(code);error.code=code;error.status=status;return error}

export function validateDevelopmentCheckpoint(value,{stored=false}={}){
  const allowed=stored?allowedStored:allowedIdentity;
  if(!exactKeys(value,allowed)||value.protocol!==DEVELOPMENT_CHECKPOINT_PROTOCOL)throw failure('development_checkpoint_invalid');
  if(!CANDIDATE.test(value.candidate_id)||!HEX64.test(value.extractor_fingerprint)||!HEX64.test(value.request_sha256)||!CHUNK.test(value.chunk_id))throw failure('development_checkpoint_invalid');
  if(stored&&(!object(value.output)||Object.keys(value.output).length!==1||!Array.isArray(value.output.atoms)))throw failure('development_checkpoint_invalid');
  return value;
}

export async function developmentCheckpointKey(identity){
  const value=validateDevelopmentCheckpoint(identity);
  const digest=await sha256(JSON.stringify([
    value.protocol,value.candidate_id,value.extractor_fingerprint,value.request_sha256,value.chunk_id,
  ]));
  return 'calibration-development:'+digest;
}

function identityOf(value){
  return Object.fromEntries([...allowedIdentity].map(key=>[key,value[key]]));
}
function sameIdentity(a,b){return [...allowedIdentity].every(key=>a[key]===b[key])}

export async function readDevelopmentCheckpoint(store,identity){
  const expected=validateDevelopmentCheckpoint(identity),key=await developmentCheckpointKey(expected),objectValue=await store.get(key);
  if(!objectValue)return {status:'missing',candidate_id:expected.candidate_id,chunk_id:expected.chunk_id,request_sha256:expected.request_sha256};
  let stored;
  try{stored=JSON.parse(await objectValue.text())}catch{throw failure('development_checkpoint_corrupt',500)}
  try{validateDevelopmentCheckpoint(stored,{stored:true})}catch{throw failure('development_checkpoint_corrupt',500)}
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
  return {
    status:'stored',candidate_id:stored.candidate_id,chunk_id:stored.chunk_id,
    request_sha256:stored.request_sha256,output_sha256:await sha256(JSON.stringify(stored.output)),
  };
}
