/* Candidate-bound F1 document-retention lease on the existing enrichment job row.
   This is an operational claim only: it does not complete extraction or make a scientific decision. */

const S=(db,sql,...v)=>db.prepare(sql).bind(...v);
const fail=(message,status=422)=>{throw Object.assign(Error(message),{code:message,status})};
const iso=now=>new Date(now).toISOString();
const PROTOCOL='CILE-ENRICH-1';
const LEASE_MS=10*60*1000;

async function currentTarget(env,targetId){
  const target=await S(env.REVIEW_DB,'SELECT * FROM enrichment_targets WHERE target_id=? AND active=1',targetId).first();
  if(!target)fail('target_not_found',404);
  return target;
}

async function extractionJob(env,target){
  const job=await S(env.REVIEW_DB,"SELECT * FROM enrichment_jobs WHERE target_id=? AND input_sha256=? AND kind='extraction' AND protocol_version=?",target.target_id,target.input_sha256,PROTOCOL).first();
  if(!job)fail('f1_retention_claim_job_missing',409);
  if(job.status!=='blocked'||job.error_code!=='model_calibration_required')fail('f1_retention_claim_job_not_blocked',409);
  return job;
}

function tokenFrom(checkpoint){
  const token=checkpoint?.lease_token;
  if(typeof token!=='string'||!/^[0-9a-f-]{36}$/.test(token))fail('f1_retention_claim_token_required',409);
  return token;
}

export async function claimF1Retention(env,targetId,now=Date.now()){
  const target=await currentTarget(env,targetId),job=await extractionJob(env,target),stamp=iso(now),token=crypto.randomUUID(),leaseUntil=iso(now+LEASE_MS);
  const claim=await S(env.REVIEW_DB,"UPDATE enrichment_jobs SET lease_token=?,lease_until=?,updated_at=? WHERE job_id=? AND status='blocked' AND error_code='model_calibration_required' AND (lease_token IS NULL OR lease_until IS NULL OR lease_until<=?)",token,leaseUntil,stamp,job.job_id,stamp).run();
  if(!claim.meta?.changes)return{status:'leased',target_id:targetId,input_sha256:target.input_sha256};
  const readback=await S(env.REVIEW_DB,'SELECT target_id,input_sha256,status,error_code,lease_token,lease_until FROM enrichment_jobs WHERE job_id=?',job.job_id).first();
  if(readback?.lease_token!==token||readback.input_sha256!==target.input_sha256||readback.status!=='blocked'||readback.lease_until!==leaseUntil)fail('f1_retention_claim_readback_failed',503);
  return{status:'claimed',target_id:targetId,input_sha256:target.input_sha256,lease_token:token,lease_until:leaseUntil};
}

export async function assertF1RetentionClaim(env,targetId,checkpoint,now=Date.now()){
  const token=tokenFrom(checkpoint),target=await currentTarget(env,targetId),job=await extractionJob(env,target),stamp=iso(now);
  if(job.lease_token!==token||!job.lease_until||job.lease_until<=stamp)fail('f1_retention_claim_lost',409);
  return{target,job,lease_token:token};
}

export async function releaseF1RetentionClaim(env,targetId,checkpoint,now=Date.now()){
  const {target,job,lease_token}=await assertF1RetentionClaim(env,targetId,checkpoint,now),stamp=iso(now);
  const released=await S(env.REVIEW_DB,"UPDATE enrichment_jobs SET lease_token=NULL,lease_until=NULL,updated_at=? WHERE job_id=? AND target_id=? AND input_sha256=? AND status='blocked' AND lease_token=?",stamp,job.job_id,target.target_id,target.input_sha256,lease_token).run();
  if(!released.meta?.changes)fail('f1_retention_claim_release_failed',409);
  const readback=await S(env.REVIEW_DB,'SELECT lease_token,lease_until,status,input_sha256 FROM enrichment_jobs WHERE job_id=?',job.job_id).first();
  if(readback?.lease_token!==null||readback?.lease_until!==null||readback?.status!=='blocked'||readback?.input_sha256!==target.input_sha256)fail('f1_retention_claim_release_readback_failed',503);
  return{status:'released',target_id:targetId,input_sha256:target.input_sha256};
}

export async function abortF1RetentionClaim(env,targetId,checkpoint,now=Date.now()){
  const token=tokenFrom(checkpoint),target=await currentTarget(env,targetId),stamp=iso(now);
  const job=await S(env.REVIEW_DB,"SELECT * FROM enrichment_jobs WHERE target_id=? AND input_sha256=? AND kind='extraction' AND protocol_version=?",target.target_id,target.input_sha256,PROTOCOL).first();
  if(!job)return{status:'absent'};
  if(job.lease_token!==token)return{status:'not_owner'};
  await S(env.REVIEW_DB,"UPDATE enrichment_jobs SET lease_token=NULL,lease_until=NULL,updated_at=? WHERE job_id=? AND lease_token=?",stamp,job.job_id,token).run();
  return{status:'aborted',target_id:targetId,input_sha256:target.input_sha256};
}
