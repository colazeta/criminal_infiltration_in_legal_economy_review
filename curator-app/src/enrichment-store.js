/* SQLite/KV adapter for an isolated private Durable Object, not a D1 permission bypass.
   Both backends implement the same versioned enrichment contract; canonical tables are absent. */
import migration from './enrichment-migration.json' with { type: 'json' };
import { sha256 } from './review-v2.js';
import { runEnrichment, handlePaperEnrichment, storeExtraction } from './paper-enrichment.js';

const DOMAIN = 'CILE-ENRICH-SERVICE-v1';
const encoder = new TextEncoder();
const headers = { 'Cache-Control': 'no-store', 'Content-Type': 'application/json', 'X-Content-Type-Options': 'nosniff' };
const json = (data, status=200) => new Response(JSON.stringify(data), {status,headers});
const hex = bytes => [...bytes].map(x=>x.toString(16).padStart(2,'0')).join('');
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
    this.ctx=ctx; this.env=env;
    this.ready=ctx.blockConcurrencyWhile(async()=>{
      if(!ctx.storage.sql)throw Error('sqlite_storage_required');
      const digest=await sha256(migration.sql);
      if(digest!==migration.sha256)throw Error('migration_bundle_integrity');
      const applied=await ctx.storage.get('schema:enrichment');
      if(applied && applied!==digest)throw Error('additive_migration_required');
      if(!applied)await ctx.storage.transaction(async tx=>{ctx.storage.sql.exec(migration.sql);await tx.put('schema:enrichment',digest)});
      this.db=sqliteAdapter(ctx.storage); this.evidence=privateTextStore(ctx.storage);
    });
  }
  async environment() {
    await this.ready;
    const activation=await this.ctx.storage.get('activation:enrichment');
    return {...this.env, REVIEW_DB:this.db, REVIEW_EVIDENCE:this.evidence,
      PAPER_ENRICHMENT_ENABLED:this.env.PAPER_ENRICHMENT_ENABLED==='true'&&activation?.commit===this.env.DEPLOY_COMMIT?'true':'false'};
  }
  async aggregate() {
    const env=await this.environment(),counts={};
    for(const table of ['targets','sources','citation_observations','proposals'])counts[table]=Number((await this.db.prepare(`SELECT COUNT(*) n FROM enrichment_${table}`).first()).n);
    const response=await handlePaperEnrichment(new Request('https://enrichment.internal/api/paper-enrichment/status'),env,{login:env.CURATOR_LOGIN});
    return {...await response.json(),storage_backend:'durable_object_sqlite',counts,commit:this.env.DEPLOY_COMMIT};
  }
  async verify() {
    await this.ready;
    const key='probe:'+crypto.randomUUID(),text='private-storage-roundtrip:'+crypto.randomUUID();
    await this.ctx.storage.put(key,text);
    try{if(await this.ctx.storage.get(key)!==text)throw Error('storage_readback_failed')}finally{await this.ctx.storage.delete(key)}
    // A real write-capability check, without inventing a candidate or a research receipt.
    await this.db.prepare("UPDATE enrichment_targets SET active=active WHERE target_id='__readiness_probe__'").run();
    return {verified:true,storage_backend:'durable_object_sqlite',migration_sha256:migration.sha256,commit:this.env.DEPLOY_COMMIT};
  }
  async authorise(request,body,now) {
    const timestamp=request.headers.get('X-Enrichment-Timestamp'),nonce=request.headers.get('X-Enrichment-Nonce'),signature=request.headers.get('X-Enrichment-Signature');
    if(!/^\d{13}$/.test(timestamp||'')||Math.abs(now-Number(timestamp))>120000||!/^[0-9a-f-]{36}$/.test(nonce||'')||!/^[a-f0-9]{64}$/.test(signature||''))throw Error('service_authentication_required');
    const bytes=Uint8Array.from(signature.match(/../g).map(x=>parseInt(x,16)));
    const valid=await crypto.subtle.verify('HMAC',await signingKey(this.env.SESSION_SECRET),bytes,encoder.encode(`${DOMAIN}\n${timestamp}\n${nonce}\n${body}`));
    if(!valid)throw Error('service_authentication_required');
    await this.ctx.storage.transaction(async tx=>{const key='nonce:'+nonce;if(await tx.get(key))throw Error('service_replay');await tx.put(key,now)});
    const expired=[];for(const[key,time]of await this.ctx.storage.list({prefix:'nonce:',limit:128}))if(now-time>300000)expired.push(key);
    if(expired.length)await this.ctx.storage.delete(expired);
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
    let body;
    try {
      if (Number(request.headers.get('Content-Length')) > 8400000) return json({error_code:'payload_too_large'},413);
      const reader=request.body?.getReader(),parts=[];let total=0;
      if(!reader)return json({error_code:'service_authentication_required'},401);
      while(true){const{done,value}=await reader.read();if(done)break;total+=value.byteLength;if(total>8400000){await reader.cancel();return json({error_code:'payload_too_large'},413)}parts.push(value)}
      const raw=new Uint8Array(total);let at=0;for(const part of parts){raw.set(part,at);at+=part.byteLength}
      body=new TextDecoder('utf-8',{fatal:true}).decode(raw);
      if(body.length>2100000)return json({error_code:'payload_too_large'},413);
      await this.authorise(request,body,now);
    }catch{return json({error_code:'service_authentication_required'},401)}
    try{
      const data=JSON.parse(body);
      if(!data||typeof data!=='object'||Array.isArray(data)||Object.keys(data).some(k=>!['operation','expected_commit','target_id','proposal','run_key'].includes(k)))return json({error_code:'invalid_service_envelope'},422);
      if(!['verify','activate','deactivate','status','run','packet','proposal'].includes(data.operation))return json({error_code:'unknown_service_operation'},422);
      if(data.expected_commit!==this.env.DEPLOY_COMMIT)return json({error_code:'stale_deployment'},409);
      if(data.operation==='verify')return json(await this.verify());
      if(data.operation==='activate'){await this.verify();await this.ctx.storage.put('activation:enrichment',{commit:this.env.DEPLOY_COMMIT,at:new Date(now).toISOString()});return json(await this.aggregate())}
      if(data.operation==='deactivate'){await this.ctx.storage.delete('activation:enrichment');return json(await this.aggregate())}
      if(data.operation==='status')return json(await this.aggregate());
      const env=await this.environment();if(env.PAPER_ENRICHMENT_ENABLED!=='true')return json({error_code:'enrichment_inactive'},409);
      if(data.operation==='run'){
        if(!/^manual:[0-9a-f-]{36}$/.test(data.run_key||''))return json({error_code:'manual_run_key_required'},422);
        const today=new Date(now).toISOString().slice(0,10), count=await this.db.prepare("SELECT COUNT(*) n FROM enrichment_runs WHERE scheduled_slot LIKE ?").bind(today+'%manual:%').first();
        if(Number(count.n)>=12)return json({error_code:'manual_daily_budget_exhausted'},429);
        return json(await runEnrichment(env,{now,runKey:data.run_key}));
      }
      if(data.operation==='packet')return json(await this.packet(data));
      if(data.operation==='proposal'){
        const target=await this.db.prepare('SELECT * FROM enrichment_targets WHERE target_id=? AND active=1').bind(data.target_id).first();if(!target)return json({error_code:'target_not_found'},404);
        return json(await storeExtraction(env,target,data.proposal,now),201);
      }
      return json({error_code:'unknown_service_operation'},422);
    }catch(error){return json({error_code:error.code||'service_operation_failed'},error.status||500)}
  }
  async fetch(request) {
    await this.ready;
    const url=new URL(request.url);
    if(url.pathname==='/machine')return this.machine(request);
    const env=await this.environment();
    if(url.pathname==='/tick')return json(await runEnrichment(env));
    return handlePaperEnrichment(request,env,{login:env.CURATOR_LOGIN});
  }
}

export function enrichmentStore(env) {
  if(env.PAPER_ENRICHMENT_STORAGE!=='durable_object_sqlite'||!env.ENRICHMENT_STORE) return null;
  return env.ENRICHMENT_STORE.get(env.ENRICHMENT_STORE.idFromName('cile-enrichment-1'));
}
