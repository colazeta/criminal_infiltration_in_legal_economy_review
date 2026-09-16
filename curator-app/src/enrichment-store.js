/* SQLite/KV adapter for an isolated private Durable Object, not a D1 permission bypass.
   Both backends implement the same versioned enrichment contract; canonical tables are absent. */
import deliveryMigration from './enrichment-delivery-migration.json' with {type:'json'};
import {privateBinaryStore,importDocument,importBibliography,retainProviderBibliography,listDocuments,documentResponse,publicAssets} from './enrichment-assets.js';
import migration from './enrichment-migration.json' with { type: 'json' };
import scheduleMigration from './enrichment-schedule-migration.json' with { type: 'json' };
import adjudicationMigration from './enrichment-adjudication-migration.json' with { type: 'json' };
import {Hour40Schedule, iterationKey} from './enrichment-schedule.js';
import { sha256 } from './review-v2.js';
import { runEnrichment, handlePaperEnrichment, storeExtraction } from './paper-enrichment.js';
import {completionPacket, importCalibrationApproval, importCompletionApproval} from './enrichment-adjudication.js';
import {readPublicResearch, readPublicCompletion, publicResearchAudit, readPublicIndex} from './public-paper-research.js';
import {readDevelopmentCheckpoint,writeDevelopmentCheckpoint} from './calibration-development-checkpoint.js';
import {claimF1Retention,assertF1RetentionClaim,releaseF1RetentionClaim,abortF1RetentionClaim} from './frontier-retention-claim.js';

const DOMAIN = 'CILE-ENRICH-SERVICE-v1';
const encoder = new TextEncoder();
const headers = { 'Cache-Control': 'no-store', 'Content-Type': 'application/json', 'X-Content-Type-Options': 'nosniff' };
const json = (data, status=200) => new Response(JSON.stringify(data), {status,headers});
const hex = bytes => [...bytes].map(x=>x.toString(16).padStart(2,'0')).join('');
const SAFE_READINESS_ERRORS=new Set([
  'sqlite_storage_required','migration_bundle_integrity','additive_migration_required',
  'schedule_migration_integrity','additive_schedule_migration_required',
  'adjudication_migration_integrity','additive_adjudication_migration_required',
  'delivery_migration_integrity','additive_delivery_migration_required','storage_readback_failed',
]);
const READINESS_PHASES=new Set(['sqlite','base_migration','schedule_migration','adjudication_migration','delivery_migration','adapters','scheduler']);
export function readinessErrorCode(error,phase){
  const code=typeof error?.message==='string'?error.message:'';
  if(SAFE_READINESS_ERRORS.has(code))return code;
  return `store_init_${READINESS_PHASES.has(phase)?phase:'unknown'}_failed`;
}
async function signingKey(secret) {
  if (typeof secret !== 'string' || secret.length < 32) throw Error('service_credential_unavailable');
  const master=await crypto.subtle.importKey('raw',encoder.encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  const derived=await crypto.subtle.sign('HMAC',master,encoder.encode(DOMAIN));
  return crypto.subtle.importKey('raw',derived,{name:'HMAC',hash:'SHA-256'},false,['sign','verify']);
}
export async function serviceSignature(secret, timestamp, nonce, body) {
  return hex(new Uint8Array(await crypto.subtle.sign('HMAC',await signingKey(secret),encoder.encode(`${DOMAIN}\n${timestamp}\n${nonce}\n${body}`))));
}

export function sqliteAdapter(storage) {
  function statement(sql,values=[]) {
    function execute() {
      const cursor=storage.sql.exec(sql,...values), results=cursor.toArray();
      const changes=storage.sql.exec('SELECT changes() AS n').toArray()[0].n;
      return {results,success:true,meta:{changes:Number(changes)}};
    }
    return {sql,values,bind(...args){return statement(sql,args)},async all(){return execute()},async first(){return execute().results[0]||null},async run(){return execute()},execute};
  }
  return {prepare:sql=>statement(sql),async batch(statements){return storage.transactionSync(()=>statements.map(s=>s.execute()))}};
}

export function privateTextStore(storage) {
  return {
    async put(key,text) {
      if (typeof key!=='string'||key.length>500||typeof text!=='string'||text.length>2000000) throw Error('private_content_limit');
      const digest=await sha256(text), root='evidence:'+key, chunks=[];
      for(let i=0;i<text.length;i+=32768)chunks.push(text.slice(i,i+32768));
      await storage.transaction(async tx=>{
        const prior=await tx.get(root);
        if(prior && prior.digest!==digest)throw Error('immutable_content_conflict');
        const entries={[root]:{digest,count:chunks.length}};
        chunks.forEach((part,i)=>{entries[root+':'+i]=part});
        await tx.put(entries);
      });
    },
    async get(key) {
      const root='evidence:'+key, meta=await storage.get(root); if(!meta)return null;
      if(!Number.isInteger(meta.count)||meta.count<0||meta.count>62)throw Error('private_content_header_invalid');
      const keys=Array.from({length:meta.count},(_,i)=>root+':'+i), parts=await storage.get(keys);
      if(keys.some(k=>typeof parts.get(k)!=='string'))throw Error('private_content_incomplete');
      const text=keys.map(k=>parts.get(k)).join('');
      if(await sha256(text)!==meta.digest)throw Error('private_content_integrity');
      return {async text(){return text}};
    }
  };
}

export class EnrichmentStoreCore {
  constructor(ctx,env) {
    this.ctx=ctx; this.env=env; this.readinessError=null;
    this.ready=ctx.blockConcurrencyWhile(async()=>{
      let phase='sqlite';
      try{
        if(!ctx.storage.sql)throw Error('sqlite_storage_required');
        phase='base_migration';
        const digest=await sha256(migration.sql);
        if(digest!==migration.sha256)throw Error('migration_bundle_integrity');
        const applied=await ctx.storage.get('schema:enrichment');
        if(applied && applied!==digest)throw Error('additive_migration_required');
        if(!applied)await ctx.storage.transaction(async tx=>{ctx.storage.sql.exec(migration.sql);await tx.put('schema:enrichment',digest)});
        phase='schedule_migration';
        const scheduleHash=await sha256(scheduleMigration.sql);
        if(scheduleHash!==scheduleMigration.sha256)throw Error('schedule_migration_integrity');
        const scheduleApplied=await ctx.storage.get('schema:enrichment-schedule');
        if(scheduleApplied && scheduleApplied!==scheduleHash)throw Error('additive_schedule_migration_required');
        if(!scheduleApplied)await ctx.storage.transaction(async tx=>{ctx.storage.sql.exec(scheduleMigration.sql);await tx.put('schema:enrichment-schedule',scheduleHash)});
        phase='adjudication_migration';
        const adjudicationHash=await sha256(adjudicationMigration.sql);
        if(adjudicationHash!==adjudicationMigration.sha256)throw Error('adjudication_migration_integrity');
        const adjudicationApplied=await ctx.storage.get('schema:enrichment-adjudication');
        if(adjudicationApplied && adjudicationApplied!==adjudicationHash)throw Error('additive_adjudication_migration_required');
        if(!adjudicationApplied)await ctx.storage.transaction(async tx=>{ctx.storage.sql.exec(adjudicationMigration.sql);await tx.put('schema:enrichment-adjudication',adjudicationHash)});
        phase='delivery_migration';
        const deliveryHash=await sha256(deliveryMigration.sql);
        if(deliveryHash!==deliveryMigration.sha256)throw Error('delivery_migration_integrity');
        const deliveryApplied=await ctx.storage.get('schema:enrichment-delivery');
        if(deliveryApplied&&deliveryApplied!==deliveryHash)throw Error('additive_delivery_migration_required');
        if(!deliveryApplied)await ctx.storage.transaction(async tx=>{ctx.storage.sql.exec(deliveryMigration.sql);await tx.put('schema:enrichment-delivery',deliveryHash)});
        phase='adapters';
        this.db=sqliteAdapter(ctx.storage); this.evidence=privateTextStore(ctx.storage);this.documents=privateBinaryStore(ctx.storage);
        phase='scheduler';
        this.schedule=new Hour40Schedule(ctx.storage,
          async(at,attempt)=>runEnrichment(await this.environment(),{iterationSlot:at,iterationAttempt:attempt}),
          async(at,attempt)=>this.db.prepare('SELECT run_id,status,selected_job_id,error_code FROM enrichment_runs WHERE scheduled_slot=?').bind(iterationKey(at,attempt)).first(),
          async()=> (await this.environment()).PAPER_ENRICHMENT_ENABLED==='true');
      }catch(error){
        this.readinessError=readinessErrorCode(error,phase);
      }
    });
  }
  async requireReady(){
    await this.ready;
    if(this.readinessError){const error=Error(this.readinessError);error.code=this.readinessError;error.status=503;throw error}
  }
  async environment() {
    await this.requireReady();
    const activation=await this.ctx.storage.get('activation:enrichment');
    return {...this.env, REVIEW_DB:this.db, REVIEW_EVIDENCE:this.evidence, REVIEW_DOCUMENTS:this.documents,
      PAPER_ENRICHMENT_ENABLED:this.env.PAPER_ENRICHMENT_ENABLED==='true'&&activation?.commit===this.env.DEPLOY_COMMIT?'true':'false'};
  }
  async aggregate() {
    const env=await this.environment(),counts={};
    for(const table of ['targets','sources','citation_observations','proposals','calibration_receipts','adjudication_receipts','documents','bibliography_snapshots'])counts[table]=Number((await this.db.prepare(`SELECT COUNT(*) n FROM enrichment_${table}`).first()).n);
    const response=await handlePaperEnrichment(new Request('https://enrichment.internal/api/paper-enrichment/status'),env,{login:env.CURATOR_LOGIN});
    return {...await response.json(),storage_backend:'durable_object_sqlite',counts,scheduling:this.schedule.status(),commit:this.env.DEPLOY_COMMIT};
  }
  async verify() {
    await this.requireReady();
    const key='probe:'+crypto.randomUUID(),text='private-storage-roundtrip:'+crypto.randomUUID();
    await this.ctx.storage.put(key,text);
    try{if(await this.ctx.storage.get(key)!==text)throw Error('storage_readback_failed')}finally{await this.ctx.storage.delete(key)}
    await this.db.prepare("UPDATE enrichment_targets SET active=active WHERE target_id='__readiness_probe__'").run();
    return {verified:true,storage_backend:'durable_object_sqlite',migration_sha256:migration.sha256,
      adjudication_migration_sha256:adjudicationMigration.sha256,delivery_migration_sha256:deliveryMigration.sha256,commit:this.env.DEPLOY_COMMIT};
  }
  async authorise(request,body,now) {
    const timestamp=request.headers.get('X-Enrichment-Timestamp'),nonce=request.headers.get('X-Enrichment-Nonce'),signature=request.headers.get('X-Enrichment-Signature');
    if(!/^\d{13}$/.test(timestamp||'')||Math.abs(now-Number(timestamp))>120000||!/^[0-9a-f-]{36}$/.test(nonce||'')||!/^[a-f0-9]{64}$/.test(signature||''))throw Error('service_authentication_required');
    const bytes=Uint8Array.from(signature.match(/../g).map(x=>parseInt(x,16)));
    const valid=await crypto.subtle.verify('HMAC',await signingKey(this.env.SESSION_SECRET),bytes,encoder.encode(`${DOMAIN}\n${timestamp}\n${nonce}\n${body}`));
    if(!valid)throw Error('service_authentication_required');
    return nonce;
  }
  async recordNonce(nonce,now) {
    try{
      await this.ctx.storage.transaction(async tx=>{const key='nonce:'+nonce;if(await tx.get(key))throw Error('service_replay');await tx.put(key,now)});
      const expired=[];for(const[key,time]of await this.ctx.storage.list({prefix:'nonce:',limit:128}))if(now-time>300000)expired.push(key);
      if(expired.length)await this.ctx.storage.delete(expired);
    }catch(error){
      if(error?.message==='service_replay')throw error;
      const unavailable=Error('service_auth_state_unavailable');unavailable.code='service_auth_state_unavailable';unavailable.status=503;throw unavailable;
    }
  }
  async packet(data) {
    const target=data.target_id?await this.db.prepare('SELECT * FROM enrichment_targets WHERE target_id=? AND active=1').bind(data.target_id).first():
      await this.db.prepare("SELECT t.* FROM enrichment_targets t WHERE t.active=1 AND EXISTS(SELECT 1 FROM enrichment_sources s WHERE s.target_id=t.target_id AND s.input_sha256=t.input_sha256 AND s.evidence_kind IN ('abstract','full_text','full_text_excerpt')) AND NOT EXISTS(SELECT 1 FROM enrichment_proposals p WHERE p.target_id=t.target_id AND p.input_sha256=t.input_sha256) ORDER BY t.first_seen_at,t.target_id LIMIT 1").first();
    if(!target)return {status:'no_source_ready'};
    const sources=(await this.db.prepare("SELECT * FROM enrichment_sources WHERE target_id=? AND input_sha256=? AND evidence_kind IN ('abstract','full_text','full_text_excerpt') ORDER BY CASE evidence_kind WHEN 'full_text' THEN 0 ELSE 1 END,observed_at DESC LIMIT 3").bind(target.target_id,target.input_sha256).all()).results;
    const out=[];
    for(const source of sources){const object=await this.evidence.get(source.storage_key);if(!object)throw Error('source_unavailable');const text=await object.text();if(await sha256(text)!==source.content_sha256)throw Error('source_integrity_failure');out.push({...source,text})}
    return {status:out.length?'source_ready':'no_source_ready',target,sources:out,scientific_status:'unreviewed'};
  }
  async machine(request,now=Date.now()) {
    if(request.method!=='POST'||!request.headers.get('Content-Type')?.startsWith('application/json'))return json({error_code:'service_authentication_required'},401);
    let body,nonce;
    try {
      if (Number(request.headers.get('Content-Length')) > 8400000) return json({error_code:'payload_too_large'},413);
      const reader=request.body?.getReader(),parts=[];let total=0;
      if(!reader)return json({error_code:'service_authentication_required'},401);
      while(true){const{done,value}=await reader.read();if(done)break;total+=value.byteLength;if(total>8400000){await reader.cancel();return json({error_code:'payload_too_large'},413)}parts.push(value)}
      const raw=new Uint8Array(total);let at=0;for(const part of parts){raw.set(part,at);at+=part.byteLength}
      body=new TextDecoder('utf-8',{fatal:true}).decode(raw);
      if(body.length>8400000)return json({error_code:'payload_too_large'},413);
      nonce=await this.authorise(request,body,now);
    }catch{return json({error_code:'service_authentication_required'},401)}
    try{
      await this.recordNonce(nonce,now);
    }catch(error){
      if(error?.message==='service_replay')return json({error_code:'service_authentication_required'},401);
      return json({error_code:'service_auth_state_unavailable'},503);
    }
    try{
      const data=JSON.parse(body);
      const allowedFields=['operation','expected_commit','target_id','proposal','run_key','calibration_id','pr_number','source','document','bibliography','document_id','checkpoint'];
      if(!data||typeof data!=='object'||Array.isArray(data)||Object.keys(data).some(k=>!allowedFields.includes(k)))return json({error_code:'invalid_service_envelope'},422);
      const operations=['verify','activate','deactivate','status','run','packet','proposal','public-research-audit','completion-packet','calibration-approval','completion-approval','source','document','documents','document-check','bibliography','provider-bibliography','development-checkpoint-get','development-checkpoint-put','document-retention-claim','source-claimed','document-claimed','document-retention-release','document-retention-abort'];
      if(!operations.includes(data.operation))return json({error_code:'unknown_service_operation'},422);
      if(data.expected_commit!==this.env.DEPLOY_COMMIT)return json({error_code:'stale_deployment'},409);
      if(data.operation==='verify')return json(await this.verify());
      if(data.operation==='activate'){await this.verify();await this.ctx.storage.put('activation:enrichment',{commit:this.env.DEPLOY_COMMIT,at:new Date(now).toISOString()});await this.schedule.start();return json(await this.aggregate())}
      if(data.operation==='deactivate'){await this.ctx.storage.delete('activation:enrichment');return json(await this.aggregate())}
      if(data.operation==='status')return json(await this.aggregate());
      if(data.operation==='public-research-audit')return json(await publicResearchAudit(await this.environment()));
      const env=await this.environment();
      if(data.operation==='completion-packet')return json(await completionPacket(env,data.target_id));
      if(data.operation==='calibration-approval')return json(await importCalibrationApproval(env,{calibration_id:data.calibration_id,pr_number:data.pr_number},undefined,now),201);
      if(data.operation==='completion-approval')return json(await importCompletionApproval(env,{target_id:data.target_id,pr_number:data.pr_number},undefined,now),201);
      if(env.PAPER_ENRICHMENT_ENABLED!=='true')return json({error_code:'enrichment_inactive'},409);
      if(data.operation==='development-checkpoint-get')return json(await readDevelopmentCheckpoint(this.evidence,data.checkpoint));
      if(data.operation==='development-checkpoint-put')return json(await writeDevelopmentCheckpoint(this.evidence,data.checkpoint),201);
      if(data.operation==='document-retention-claim')return json(await claimF1Retention(env,data.target_id,now),201);
      if(data.operation==='document-retention-release')return json(await releaseF1RetentionClaim(env,data.target_id,data.checkpoint,now));
      if(data.operation==='document-retention-abort')return json(await abortF1RetentionClaim(env,data.target_id,data.checkpoint,now));
      if(data.operation==='run'){
        if(this.schedule.busy)return json({status:'leased'});
        if(!/^manual:[0-9a-f-]{36}$/.test(data.run_key||''))return json({error_code:'manual_run_key_required'},422);
        const today=new Date(now).toISOString().slice(0,10), count=await this.db.prepare("SELECT COUNT(*) n FROM enrichment_runs WHERE scheduled_slot LIKE ?").bind(today+'%manual:%').first();
        if(Number(count.n)>=12)return json({error_code:'manual_daily_budget_exhausted'},429);
        return json(await runEnrichment(env,{now,runKey:data.run_key}));
      }
      if(data.operation==='source-claimed'){
        await assertF1RetentionClaim(env,data.target_id,data.checkpoint,now);
        return handlePaperEnrichment(new Request('https://enrichment.internal/api/paper-enrichment/source?id='+encodeURIComponent(data.target_id),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data.source)}),env,{login:env.CURATOR_LOGIN});
      }
      if(data.operation==='document-claimed'){
        await assertF1RetentionClaim(env,data.target_id,data.checkpoint,now);
        return json(await importDocument(env,data.target_id,data.document,now),201);
      }
      if(data.operation==='source')return handlePaperEnrichment(new Request('https://enrichment.internal/api/paper-enrichment/source?id='+encodeURIComponent(data.target_id),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data.source)}),env,{login:env.CURATOR_LOGIN});
      if(data.operation==='document')return json(await importDocument(env,data.target_id,data.document,now),201);
      if(data.operation==='documents')return json({documents:await listDocuments(env,data.target_id)});
      if(data.operation==='document-check'){const r=await documentResponse(env,data.target_id,data.document_id,new Request('https://enrichment.internal/document',{method:'HEAD'}));return json({readable:r.ok,byte_length:Number(r.headers.get('Content-Length')),etag:r.headers.get('ETag'),content_type:r.headers.get('Content-Type'),scope:'authenticated_reader_route_bytes_checked'})}
      if(data.operation==='provider-bibliography')return json(await retainProviderBibliography(env,data.target_id,now));
      if(data.operation==='bibliography')return json(await importBibliography(env,data.target_id,data.bibliography,now),201);
      if(data.operation==='packet')return json(await this.packet(data));
      if(data.operation==='proposal'){
        const target=await this.db.prepare('SELECT * FROM enrichment_targets WHERE target_id=? AND active=1').bind(data.target_id).first();if(!target)return json({error_code:'target_not_found'},404);
        return json(await storeExtraction(env,target,data.proposal,now),201);
      }
      return json({error_code:'unknown_service_operation'},422);
    }catch(error){return json({error_code:error.code||error.message||'service_operation_failed'},error.status||500)}
  }
  async alarm() { await this.requireReady(); return this.schedule.tick(); }
  async fetch(request) {
    const url=new URL(request.url);
    // Authenticate the private machine envelope before requiring a healthy store. A failed
    // initialisation remains visible only to the signed service; public routes stay fail-closed.
    if(url.pathname==='/machine')return this.machine(request);
    await this.requireReady();
    const env=await this.environment();
    if(url.pathname==='/public-index'&&request.method==='GET'){try{return json(await readPublicIndex(env,Number(url.searchParams.get('cursor')||0),url.searchParams.get('revision')))}catch(error){return json({error_code:error.message},error.status||503)}}
    if(url.pathname==='/public-assets'&&['GET','HEAD'].includes(request.method)){
      try{const candidate=url.searchParams.get('id'),doc=url.searchParams.get('document');if(doc){const t=await this.db.prepare('SELECT target_id FROM enrichment_targets WHERE record_id=? AND active=1').bind(candidate).first();if(!t)return json({error:'not_found'},404);return await documentResponse(env,t.target_id,doc,request,{publicOnly:true})}return json(await publicAssets(env,candidate,Number(url.searchParams.get('offset')||0),url.searchParams.get('revision')))}catch(e){return json({error:e.code||'assets_unavailable'},e.status||503)}
    }
    if(url.pathname==='/api/paper-enrichment/documents'&&request.method==='GET'){try{return json({documents:await listDocuments(env,url.searchParams.get('id'))})}catch(e){return json({error:e.code||'documents_unavailable'},e.status||503)}}
    if(url.pathname==='/api/paper-enrichment/document'&&['GET','HEAD'].includes(request.method)){try{return await documentResponse(env,url.searchParams.get('id'),url.searchParams.get('document'),request)}catch(e){return json({error:e.code||'document_unavailable'},e.status||503)}}
    if(url.pathname==='/public-research'&&request.method==='GET')return json(await readPublicResearch(env,url.searchParams.get('id')));
    if(url.pathname==='/public-completion'&&request.method==='GET')return json(await readPublicCompletion(env,url.searchParams.get('id')));
    if(url.pathname==='/tick')return json(await this.schedule.tick());
    if(url.pathname==='/api/paper-enrichment/status'&&request.method==='GET')return json(await this.aggregate());
    return handlePaperEnrichment(request,env,{login:env.CURATOR_LOGIN});
  }
}

export function enrichmentStore(env) {
  if(env.PAPER_ENRICHMENT_STORAGE!=='durable_object_sqlite'||!env.ENRICHMENT_STORE) return null;
  return env.ENRICHMENT_STORE.get(env.ENRICHMENT_STORE.idFromName('cile-enrichment-1'));
}