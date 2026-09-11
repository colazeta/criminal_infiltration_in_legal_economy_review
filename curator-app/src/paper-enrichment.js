/* Private, candidate-bound enrichment. No eligibility or public-registry writes. */
import cycle from '../../config/archive-cycle.json' with { type: 'json' };
import schema from '../../schema/paper-enrichment.schema.json' with { type: 'json' };
import { canonicalJson, sha256 } from './review-v2.js';
import { fetchWithTimeout } from './network.js';

export const ENRICHMENT_PROTOCOL = 'CILE-ENRICH-1';
const HOUR = 3600000, WEEK = 7 * 24 * HOUR;
const REGISTRY = 'https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/data/paper-register.json';
const TYPES = ['metadata', 'citations', 'extraction', 'classification'];
const S = (db, sql, ...values) => db.prepare(sql).bind(...values);
const rows = async (db, sql, ...v) => (await S(db, sql, ...v).all()).results;
const iso = (now) => new Date(now).toISOString();
class EnrichmentError extends Error { constructor(code, status = 422, retryAt = null) { super(code); this.code = code; this.status = status; this.retryAt = retryAt; } }
const err = (code, status = 422) => { throw new EnrichmentError(code, status); };
const bounded = (s, n = 6000) => typeof s === 'string' && s.length > 0 && s.length <= n;
const normalTitle = (s) => String(s).normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
export const normalDoi = (s) => String(s || '').trim().replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, '').toLowerCase();
function validDoi(s) { return /^10\.\d{4,9}\/\S+$/i.test(s) && s.length <= 512; }
function validHttps(s) { try { const u = new URL(s); return u.protocol === 'https:' && !u.username && !u.password && s.length <= 2000; } catch { return false; } }
async function batch(db, list) { for (let i = 0; i < list.length; i += 40) await db.batch(list.slice(i, i + 40)); }

// Supports exactly the JSON Schema keywords used by the versioned closed envelope.
export function validateShape(value, spec = schema, path = '$') {
  if (spec.$ref) return validateShape(value, schema.$defs[spec.$ref.split('/').at(-1)], path);
  if ('const' in spec && value !== spec.const) err('schema_const:' + path);
  if (spec.enum && !spec.enum.includes(value)) err('schema_enum:' + path);
  const type = value === null ? 'null' : Array.isArray(value) ? 'array' : typeof value;
  if (spec.type && ![spec.type].flat().some(t => t === type || (t === 'integer' && typeof value === 'number' && Number.isInteger(value)))) err('schema_type:' + path);
  if (type === 'object') {
    for (const key of spec.required || []) if (!Object.hasOwn(value, key)) err('schema_required:' + path + '.' + key);
    for (const [key, child] of Object.entries(value)) {
      if (!Object.hasOwn(spec.properties || {}, key)) { if (spec.additionalProperties === false) err('schema_extra:' + path + '.' + key); }
      else validateShape(child, spec.properties[key], path + '.' + key);
    }
  }
  if (type === 'array') {
    if (spec.maxItems !== undefined && value.length > spec.maxItems) err('schema_array_limit:' + path);
    for (let i = 0; i < value.length; i++) validateShape(value[i], spec.items, path + '[' + i + ']');
  }
  if (type === 'string') {
    if ((spec.minLength !== undefined && value.length < spec.minLength) || (spec.maxLength !== undefined && value.length > spec.maxLength)) err('schema_length:' + path);
    if (spec.pattern && !new RegExp(spec.pattern).test(value)) err('schema_pattern:' + path);
  }
  if (type === 'number' && spec.minimum !== undefined && value < spec.minimum) err('schema_minimum:' + path);
  return value;
}
function uniqueIds(items, name) {
  const ids = items.map(i => i.id);
  if (ids.some(i => !bounded(i, 100)) || new Set(ids).size !== ids.length) err('duplicate_or_blank_' + name);
  return new Set(ids);
}
export function validateExtraction(input, target, sources) {
  validateShape(input);
  if (input.target_id !== target.target_id || input.input_sha256 !== target.input_sha256) err('stale_input', 409);
  if (!input.source_ids.length || new Set(input.source_ids).size !== input.source_ids.length) err('source_ids_required');
  const selected = new Map();
  for (const id of input.source_ids) {
    const source = sources.find(s => s.source_id === id);
    if (!source || source.target_id !== target.target_id || source.input_sha256 !== target.input_sha256 || source.evidence_kind === 'metadata') err('invalid_source_scope');
    selected.set(id, source);
  }
  const kinds = [...selected.values()].map(s => s.evidence_kind);
  const coverage = kinds.includes('full_text') ? 'full_text' : kinds.every(k => k === 'abstract' || k === 'publisher_summary') ? 'abstract_only' : 'partial_text';
  if (input.source_coverage !== coverage) err('unsupported_source_coverage');
  const spans = uniqueIds(input.spans, 'span');
  for (const span of input.spans) {
    const source = selected.get(span.source_id);
    if (!source || !bounded(span.locator, 500) || span.end_offset <= span.start_offset || span.end_offset > source.text.length || !source.text.slice(span.start_offset, span.end_offset).trim()) err('invalid_source_span');
  }
  function facts(v) {
    if (!v || typeof v !== 'object') return;
    if (!Array.isArray(v) && Object.hasOwn(v, 'evidence_span_ids')) {
      if (new Set(v.evidence_span_ids).size !== v.evidence_span_ids.length || v.evidence_span_ids.some(id => !spans.has(id))) err('unknown_evidence_span');
      if (v.status === 'reported' && (!bounded(v.value) || !v.evidence_span_ids.length)) err('reported_fact_requires_evidence');
      if (['not_reported', 'not_verifiable', 'not_applicable'].includes(v.status) && v.value !== null) err('missingness_requires_null');
      if (v.status === 'ambiguous' && !bounded(v.value)) err('ambiguity_requires_explanation');
    }
    for (const child of Object.values(v)) facts(child);
  }
  facts(input);
  const studies = uniqueIds(input.studies, 'study'), datasets = uniqueIds(input.datasets, 'dataset'), analyses = uniqueIds(input.analyses, 'analysis'), variables = uniqueIds(input.variable_uses, 'variable');
  uniqueIds(input.findings, 'finding');
  for (const item of [...input.datasets, ...input.analyses]) if (!studies.has(item.study_id)) err('unknown_study');
  for (const item of [...input.analyses, ...input.variable_uses]) if(new Set(item.dataset_ids).size!==item.dataset_ids.length)err('duplicate_dataset_reference');
  for (const f of input.findings) if(new Set(f.variable_use_ids).size!==f.variable_use_ids.length)err('duplicate_variable_reference');
  for (const a of input.analyses) for (const id of a.dataset_ids) if (!datasets.has(id) || input.datasets.find(d => d.id === id).study_id !== a.study_id) err('cross_study_dataset');
  for (const v of input.variable_uses) {
    if (!analyses.has(v.analysis_id)) err('unknown_analysis');
    const a = input.analyses.find(a => a.id === v.analysis_id);
    for (const id of v.dataset_ids) if (!a.dataset_ids.includes(id)) err('variable_dataset_scope');
  }
  for (const f of input.findings) {
    if (!analyses.has(f.analysis_id)) err('unknown_analysis');
    for (const id of f.variable_use_ids) if (!variables.has(id) || input.variable_uses.find(v => v.id === id).analysis_id !== f.analysis_id) err('finding_variable_scope');
  }
  const f = input.framework;
  if (f.status === 'proposed' && (f.primary === null || f.rationale.status !== 'reported' || f.rationale.origin !== 'analyst')) err('framework_requires_grounded_rationale');
  if (f.status !== 'proposed' && (f.primary !== null || f.secondary.length)) err('abstention_cannot_assign_categories');
  const codes = f.secondary.map(s => s.category);
  if (new Set(codes).size !== codes.length || codes.includes(f.primary) || f.alternative === f.primary && f.primary !== null) err('duplicate_framework_category');
  if (f.secondary.some(s => s.rationale.status !== 'reported' || s.rationale.origin !== 'analyst')) err('secondary_requires_grounded_rationale');
  return input;
}

export function validateRegistry(payload) {
  if (payload?.schemaVersion !== 1 || !Array.isArray(payload.records) || payload.records.length > 10000) err('invalid_registry');
  const seen = new Set();
  for (const r of payload.records) {
    if (!/^CAND-[A-Za-z0-9-]{1,100}$/.test(r.id || '') || seen.has(r.id) || !bounded(r.title, 3000) || typeof r.doi !== 'string' || !Array.isArray(r.sourceLinks) || r.sourceLinks.some(u => !validHttps(u))) err('invalid_registry_record');
    seen.add(r.id);
  }
  return payload.records;
}
async function fetchJSON(url, fetcher, now) {
  const controller=new AbortController(); let timer;
  try {
    return await Promise.race([
      fetchJSONBody(url,fetcher,now,controller.signal),
      new Promise((resolve,reject)=>{timer=setTimeout(()=>{controller.abort();reject(new EnrichmentError('provider_timeout',503));},12000);})
    ]);
  } finally { clearTimeout(timer); controller.abort(); }
}
async function fetchJSONBody(url, fetcher, now, signal) {
  const u = new URL(url);
  if (!['api.crossref.org','api.openalex.org','colazeta.github.io'].includes(u.hostname) || u.protocol !== 'https:') err('provider_not_authorised');
  const response = await fetcher(url, { redirect: 'error', signal, headers: { Accept: 'application/json' } }, 10000);
  if (response.status === 429) {
    const retry = response.headers.get('Retry-After');
    const time = /^\d+$/.test(retry || '') ? now + Number(retry) * 1000 : Date.parse(retry || '');
    throw new EnrichmentError('rate_limited', 503, Number.isFinite(time) ? time : now + HOUR);
  }
  if ([401,403].includes(response.status)) err('provider_authentication_required', 503);
  if (response.status === 404) err('provider_record_not_found', 404);
  if (!response.ok) err('provider_unavailable', 503);
  if (Number(response.headers.get('content-length') || 0) > 3000000) err('provider_response_too_large');
  const reader = response.body.getReader(); const chunks = []; let total = 0;
  const cancelBody=()=>{void reader.cancel().catch(()=>{});};
  signal.addEventListener("abort",cancelBody,{once:true});
  try { while (true) { const { value, done } = await reader.read(); if (done) break; total += value.byteLength; if (total > 3000000) err('provider_response_too_large'); chunks.push(value); } }
  finally { signal.removeEventListener("abort",cancelBody); void reader.cancel().catch(() => {}); }
  const bytes = new Uint8Array(total); let offset = 0; for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  try { return JSON.parse(new TextDecoder().decode(bytes)); } catch { err('invalid_provider_json'); }
}
export async function syncTargets(env, payload, now) {
  const records = validateRegistry(payload), db = env.REVIEW_DB;
  const statements = [];
  const existing = new Map((await rows(db, 'SELECT * FROM enrichment_targets WHERE cycle_id=?', cycle.review_id)).map(t => [t.record_id, t]));
  for (const r of records) {
    const record = { id:r.id, title:r.title, doi:normalDoi(r.doi), sourceLinks:r.sourceLinks };
    const encoded = canonicalJson(record), hash = await sha256(encoded), target = await sha256(cycle.review_id + ':candidate:' + r.id);
    const old = existing.get(r.id); existing.delete(r.id);
    if (old?.input_sha256 === hash && old.active === 1) continue;
    statements.push(S(db, 'INSERT INTO enrichment_targets VALUES (?,?,?,?,?,?,1,?,?) ON CONFLICT(target_id) DO UPDATE SET input_sha256=excluded.input_sha256,record_json=excluded.record_json,active=1,updated_at=excluded.updated_at', target,cycle.review_id,'candidate',r.id,hash,encoded,iso(now),iso(now)));
    statements.push(S(db, 'INSERT OR IGNORE INTO enrichment_inputs VALUES (?,?,?,?,?)',await sha256(target+hash),target,hash,encoded,iso(now)));
    statements.push(S(db, "UPDATE enrichment_jobs SET status='superseded',lease_token=NULL,lease_until=NULL WHERE target_id=? AND input_sha256<>? AND status<>'superseded'",target,hash));
    for (const kind of TYPES) {
      const blocked = ['extraction','classification'].includes(kind);
      statements.push(S(db, 'INSERT OR IGNORE INTO enrichment_jobs(job_id,target_id,input_sha256,kind,protocol_version,status,due_at,error_code,updated_at) VALUES (?,?,?,?,?,?,?,?,?)',await sha256(target+hash+kind+ENRICHMENT_PROTOCOL),target,hash,kind,ENRICHMENT_PROTOCOL,blocked?'blocked':'pending',blocked?null:iso(now),blocked?'model_calibration_required':null,iso(now)));
      statements.push(S(db, "UPDATE enrichment_jobs SET status=?,due_at=?,failure_streak=0,error_code=?,updated_at=? WHERE target_id=? AND input_sha256=? AND kind=? AND status='superseded'",blocked?'blocked':'pending',blocked?null:iso(now),blocked?'model_calibration_required':null,iso(now),target,hash,kind));
    }
  }
  for (const old of existing.values()) statements.push(S(db,'UPDATE enrichment_targets SET active=0,updated_at=? WHERE target_id=?',iso(now),old.target_id));
  await batch(db,statements);
  return { registered:records.length, changed_statements:statements.length };
}
export async function saveSource(env, target, { provider, source_url, evidence_kind, text, version_label = 'unspecified', language = null, retention_basis = 'Owner-authorised private research; no redistribution', licence_status = 'not_verified' }, now) {
  if (!bounded(provider,100) || !validHttps(source_url) || !['abstract','metadata','full_text','full_text_excerpt','publisher_summary'].includes(evidence_kind) || !bounded(text,2000000) || !bounded(retention_basis,2000) || !bounded(version_label,200) || !bounded(licence_status,200) || !(language===null || bounded(language,100))) err('invalid_source');
  const hash = await sha256(text), id = await sha256(canonicalJson([target.target_id,target.input_sha256,provider,source_url,evidence_kind,hash]));
  const key = `${cycle.review_id}/enrichment/sources/${id}/${hash}.txt`;
  if (!await S(env.REVIEW_DB,'SELECT source_id FROM enrichment_sources WHERE source_id=?',id).first()) {
    await env.REVIEW_EVIDENCE.put(key,text,{httpMetadata:{contentType:'text/plain; charset=utf-8'}});
    const stored = await env.REVIEW_EVIDENCE.get(key);
    if (!stored || await sha256(await stored.text()) !== hash) err('source_readback_failed',503);
    await S(env.REVIEW_DB,'INSERT OR IGNORE INTO enrichment_sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',id,target.target_id,target.input_sha256,provider,source_url,evidence_kind,hash,key,version_label,language,retention_basis,licence_status,iso(now)).run();
    if (!await S(env.REVIEW_DB,'SELECT source_id FROM enrichment_sources WHERE source_id=?',id).first()) err('source_database_readback_failed',503);
  }
  return id;
}
function matched(record, doi, title) {
  if (!validDoi(record.doi)) err('identifier_resolution_required',409);
  if (normalDoi(doi)!==record.doi || !title || normalTitle(record.title)!==normalTitle(title)) err('identity_conflict',409);
}
async function metadata(env, target, checkpoint, now, fetcher) {
  const record=JSON.parse(target.record_json); if(!validDoi(record.doi))err('identifier_resolution_required',409);
  const url='https://api.crossref.org/works/'+encodeURIComponent(record.doi), response=await fetchJSON(url,fetcher,now), m=response.message;
  matched(record,m?.DOI,m?.title?.[0]);
  await saveSource(env,target,{provider:'Crossref',source_url:url,evidence_kind:'metadata',text:canonicalJson(m)},now);
  let abstractSource=null;
  if(typeof m.abstract==='string'&&m.abstract.trim()) {
    // Preserve the exact returned JATS/XML text. Do not silently change offset units or wording.
    abstractSource=await saveSource(env,target,{provider:'Crossref',source_url:url,evidence_kind:'abstract',text:m.abstract,version_label:'provider-supplied abstract; publication version not independently verified'},now);
  }
  return {complete:true, due:now+30*24*HOUR, checkpoint:{abstract_status:abstractSource?'available':'not_returned',abstract_source_id:abstractSource}};
}
async function citations(env,target,checkpoint,now,fetcher,job,token) {
  const record=JSON.parse(target.record_json);if(!validDoi(record.doi))err('identifier_resolution_required',409);
  let cp={...checkpoint};
  if(!cp.snapshot_id) {
    const url='https://api.openalex.org/works/https://doi.org/'+encodeURIComponent(record.doi)+'?select=id,doi,title,referenced_works,cited_by_count';
    const work=await fetchJSON(url,fetcher,now);matched(record,work.doi,work.title);
    if(!/^https:\/\/openalex\.org\/W\d+$/.test(work.id)||!Array.isArray(work.referenced_works)||work.referenced_works.length>20000||work.referenced_works.some(x=>!/^https:\/\/openalex\.org\/W\d+$/.test(x)))err('invalid_citation_payload');
    cp={snapshot_id:iso(now), work_id:work.id, outgoing:work.referenced_works, outgoing_offset:0, cursor:'*', provider_count:Number.isInteger(work.cited_by_count)?work.cited_by_count:null};
    const saved=await S(env.REVIEW_DB,"UPDATE enrichment_jobs SET checkpoint_json=? WHERE job_id=? AND lease_token=? AND status='running'",canonicalJson(cp),job.job_id,token).run();
    if(!saved.meta?.changes)err('lease_lost',409);
  }
  const statements=[];
  async function edge(direction,citing,cited,url){statements.push(S(env.REVIEW_DB,'INSERT OR IGNORE INTO enrichment_citation_observations VALUES (?,?,?,?,?,?,?,?,?,?)',await sha256(canonicalJson([target.target_id,'OpenAlex',direction,citing,cited,cp.snapshot_id])),target.target_id,target.input_sha256,'OpenAlex',direction,citing,cited,cp.snapshot_id,url,iso(now)));}
  async function coverage(direction,url,count,total,cursor,status){statements.push(S(env.REVIEW_DB,'INSERT OR IGNORE INTO enrichment_citation_coverage VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',await sha256(canonicalJson([target.target_id,cp.snapshot_id,direction,cp.outgoing_offset,cp.cursor,status])),target.target_id,target.input_sha256,'OpenAlex',direction,cp.snapshot_id,url,count,total,cursor,status,iso(now)));}
  if(cp.outgoing_offset<cp.outgoing.length || cp.outgoing_offset===0 && !cp.outgoing_done) {
    const url='https://api.openalex.org/works/'+cp.work_id.split('/').at(-1);
    const part=cp.outgoing.slice(cp.outgoing_offset,cp.outgoing_offset+100);
    for(const cited of part)await edge('outgoing',cp.work_id,cited,url);
    cp.outgoing_offset+=part.length;cp.outgoing_done=cp.outgoing_offset>=cp.outgoing.length;
    await coverage('outgoing',url,part.length,cp.outgoing.length,cp.outgoing_done?null:String(cp.outgoing_offset),cp.outgoing_done?'provider_complete':'partial');
    await batch(env.REVIEW_DB,statements);return{complete:false,due:now+HOUR,checkpoint:cp};
  }
  const url='https://api.openalex.org/works?filter=cites:'+cp.work_id.split('/').at(-1)+'&per-page=50&select=id,doi,title&cursor='+encodeURIComponent(cp.cursor);
  const data=await fetchJSON(url,fetcher,now);
  if(!Array.isArray(data.results)||data.results.length>50||!data.meta||!Object.hasOwn(data.meta,'next_cursor')||!(data.meta.next_cursor===null||bounded(data.meta.next_cursor,4000)))err('invalid_citation_page');
  if(data.meta.next_cursor!==null&&data.meta.next_cursor===cp.cursor)err('citation_cursor_not_advancing');
  for(const work of data.results){if(!/^https:\/\/openalex\.org\/W\d+$/.test(work.id))err('invalid_citation_identifier');await edge('incoming',work.id,cp.work_id,url);}
  const next=data.meta.next_cursor;
  await coverage('incoming',url,data.results.length,Number.isInteger(data.meta.count)?data.meta.count:null,next,next===null?'provider_complete':'partial');
  await batch(env.REVIEW_DB,statements);
  return{complete:next===null,due:now+(next===null?WEEK:HOUR),checkpoint:next===null?{}:{...cp,cursor:next}};
}

export async function runEnrichment(env, {now=Date.now(),fetcher=fetchWithTimeout,registry=null}={}) {
  if(env.PAPER_ENRICHMENT_ENABLED!=='true')return{status:'disabled'};
  if(!env.REVIEW_DB||!env.REVIEW_EVIDENCE)return{status:'blocked',error_code:'private_storage_required'};
  const wallStarted=Date.now(), clock=()=>now+Date.now()-wallStarted;
  const db=env.REVIEW_DB,slot=iso(now).slice(0,13),runId=await sha256(cycle.review_id+slot),stamp=iso(now);
  await S(db,"UPDATE enrichment_runs SET status='failed',finished_at=?,error_code='lease_expired' WHERE status='running' AND lease_until<=?",stamp,stamp).run();
  if(await S(db,"SELECT run_id FROM enrichment_runs WHERE status='running' AND lease_until>?",stamp).first())return{status:'leased'};
  const inserted=await S(db,"INSERT OR IGNORE INTO enrichment_runs(run_id,cycle_id,scheduled_slot,started_at,lease_until,status) VALUES (?,?,?,?,?,'running')",runId,cycle.review_id,slot,stamp,iso(now+10*60000)).run();
  if(!inserted.meta?.changes)return{status:'slot_already_observed'};
  let syncError=null,job=null,target=null,outcome='empty',code=null,token=null;
  try {
    await S(db,"UPDATE enrichment_jobs SET failure_streak=MIN(failure_streak+1,3),status=CASE WHEN failure_streak>=2 THEN 'exhausted' ELSE 'pending' END,due_at=?,lease_until=NULL,lease_token=NULL,error_code='lease_expired',updated_at=? WHERE status='running' AND lease_until<=?",stamp,stamp,stamp).run();
    try{await syncTargets(env,registry||await fetchJSON(REGISTRY,fetcher,now),now);}catch(e){syncError=e.code||'registry_unavailable';}
    job=await S(db,"SELECT j.* FROM enrichment_jobs j JOIN enrichment_targets t USING(target_id) WHERE t.active=1 AND t.cycle_id=? AND t.input_sha256=j.input_sha256 AND j.status IN ('pending','completed') AND j.due_at<=? ORDER BY j.due_at,j.target_id,CASE j.kind WHEN 'metadata' THEN 0 ELSE 1 END LIMIT 1",cycle.review_id,stamp).first();
    if(job){
      token=crypto.randomUUID();
      const claim=await S(db,"UPDATE enrichment_jobs SET status='running',lease_until=?,lease_token=?,attempts_total=attempts_total+1,updated_at=? WHERE job_id=? AND status IN ('pending','completed')",iso(now+10*60000),token,stamp,job.job_id).run();
      if(!claim.meta?.changes)err('lease_lost',409);
      await S(db,'UPDATE enrichment_runs SET selected_job_id=? WHERE run_id=?',job.job_id,runId).run();
      target=await S(db,'SELECT * FROM enrichment_targets WHERE target_id=?',job.target_id).first();
      const operation=job.kind==='metadata'?metadata:job.kind==='citations'?citations:null;if(!operation)err('model_calibration_required',409);
      const result=await operation(env,target,JSON.parse(job.checkpoint_json),now,fetcher,job,token);
      const finish=await S(db,"UPDATE enrichment_jobs SET status=?,failure_streak=0,due_at=?,lease_until=NULL,lease_token=NULL,checkpoint_json=?,error_code=NULL,updated_at=? WHERE job_id=? AND lease_token=? AND lease_until>?",result.complete?'completed':'pending',iso(result.due),canonicalJson(result.checkpoint),iso(clock()),job.job_id,token,iso(clock())).run();
      if(!finish.meta?.changes)err('lease_lost',409);
      outcome=result.complete?'completed':'partial';
      await S(db,'INSERT INTO enrichment_attempts VALUES (?,?,?,?,?,?,?)',token,job.job_id,runId,stamp,iso(clock()),outcome,null).run();
    }
  }catch(e){
    code=e.code||'operation_failed';outcome='failed';
    if(job&&token){
      const blocked=['identity_conflict','identifier_resolution_required','provider_authentication_required','model_calibration_required','provider_record_not_found'].includes(code);
      const streak=Math.min(job.failure_streak+1,3),status=blocked?'blocked':streak>=3?'exhausted':'pending';
      await S(db,'UPDATE enrichment_jobs SET status=?,failure_streak=?,due_at=?,lease_until=NULL,lease_token=NULL,error_code=?,updated_at=? WHERE job_id=? AND lease_token=?',status,streak,status==='pending'?iso(Math.max(now+HOUR*2**(streak-1),e.retryAt||0)):null,code,iso(clock()),job.job_id,token).run();
      await S(db,'INSERT OR IGNORE INTO enrichment_attempts VALUES (?,?,?,?,?,?,?)',token,job.job_id,runId,stamp,iso(clock()),status,code).run();
    }
  }
  const status=syncError?(outcome==='failed'||outcome==='empty'?'failed':'partial'):outcome;
  await S(db,'UPDATE enrichment_runs SET status=?,finished_at=?,error_code=? WHERE run_id=?',status,iso(clock()),code||syncError,runId).run();
  const receipt=await S(db,'SELECT run_id,status,selected_job_id,error_code FROM enrichment_runs WHERE run_id=?',runId).first();
  if(!receipt)err('run_readback_failed',503);
  return receipt;
}

async function sourceContents(env,target,ids) {
  const sources=[];
  for(const id of ids){
    const source=await S(env.REVIEW_DB,'SELECT * FROM enrichment_sources WHERE source_id=? AND target_id=? AND input_sha256=?',id,target.target_id,target.input_sha256).first();
    if(!source)err('invalid_source_scope');
    const object=await env.REVIEW_EVIDENCE.get(source.storage_key);if(!object)err('source_unavailable',503);
    const text=await object.text();if(await sha256(text)!==source.content_sha256)err('source_integrity_failure',409);
    sources.push({...source,text});
  }
  return sources;
}
export async function storeExtraction(env,target,input,now=Date.now()) {
  validateShape(input);
  validateExtraction(input,target,await sourceContents(env,target,input.source_ids));
  const encoded=canonicalJson(input),hash=await sha256(encoded),id=await sha256(target.target_id+target.input_sha256+hash),db=env.REVIEW_DB;
  if(await S(db,'SELECT proposal_id FROM enrichment_proposals WHERE proposal_id=?',id).first())return{proposal_id:id,replayed:true};
  const list=[S(db,`INSERT INTO enrichment_proposals SELECT ?,target_id,input_sha256,?,?,?,?,?,? FROM enrichment_targets WHERE target_id=? AND input_sha256=? AND active=1`,id,ENRICHMENT_PROTOCOL,'1.0.0',hash,encoded,canonicalJson(input.generated_by),iso(now),target.target_id,target.input_sha256)];
  for(const s of input.studies)list.push(S(db,'INSERT INTO enrichment_studies VALUES (?,?,?)',id,s.id,canonicalJson(s)));
  for(const d of input.datasets)list.push(S(db,'INSERT INTO enrichment_datasets VALUES (?,?,?,?)',id,d.study_id,d.id,canonicalJson(d)));
  for(const a of input.analyses)list.push(S(db,'INSERT INTO enrichment_analyses VALUES (?,?,?,?)',id,a.study_id,a.id,canonicalJson(a)));
  for(const v of input.variable_uses)list.push(S(db,'INSERT INTO enrichment_variable_uses VALUES (?,?,?,?)',id,v.analysis_id,v.id,canonicalJson(v)));
  for(const f of input.findings)list.push(S(db,'INSERT INTO enrichment_findings VALUES (?,?,?,?)',id,f.analysis_id,f.id,canonicalJson(f)));
  list.push(S(db,'INSERT INTO enrichment_framework_proposals VALUES (?,?,?,?)',id,input.framework.primary,input.framework.status,canonicalJson(input.framework)));
  // A single atomic D1 transaction. Never split a scientific proposal across batches.
  if(list.length>90)err('proposal_transaction_limit');
  await db.batch(list);
  const receipt=await S(db,'SELECT payload_sha256 FROM enrichment_proposals WHERE proposal_id=?',id).first();if(receipt?.payload_sha256!==hash)err('proposal_readback_failed',503);
  return{proposal_id:id,replayed:false,scientific_status:'proposed'};
}
const json=(value,status=200)=>Response.json(value,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'}});
export async function handlePaperEnrichment(request,env,session) {
  try{
    if(!session||session.login!==env.CURATOR_LOGIN)err('authentication_required',401);
    if(!env.REVIEW_DB||!env.REVIEW_EVIDENCE)return json({enabled:false,status:'blocked',error_code:'private_storage_required'},503);
    const url=new URL(request.url),db=env.REVIEW_DB;
    if(url.pathname.endsWith('/status')&&request.method==='GET')return json({enabled:env.PAPER_ENRICHMENT_ENABLED==='true',protocol:ENRICHMENT_PROTOCOL,scientific_extraction:'blocked_pending_calibration',jobs:await rows(db,'SELECT kind,status,COUNT(*) count FROM enrichment_jobs GROUP BY kind,status'),runs:await rows(db,'SELECT * FROM enrichment_runs ORDER BY started_at DESC LIMIT 24')});
    if(url.pathname.endsWith('/targets')&&request.method==='GET')return json({targets:await rows(db,'SELECT target_id,record_id,record_json,input_sha256 FROM enrichment_targets WHERE cycle_id=? AND active=1 ORDER BY first_seen_at,target_id LIMIT 500',cycle.review_id)});
    const target=await S(db,'SELECT * FROM enrichment_targets WHERE target_id=? AND cycle_id=? AND active=1',url.searchParams.get('id'),cycle.review_id).first();if(!target)err('target_not_found',404);
    if(url.pathname.endsWith('/target')&&request.method==='GET')return json({target,jobs:await rows(db,'SELECT * FROM enrichment_jobs WHERE target_id=? ORDER BY updated_at DESC',target.target_id),sources:await rows(db,'SELECT source_id,provider,source_url,evidence_kind,content_sha256,version_label,observed_at FROM enrichment_sources WHERE target_id=? AND input_sha256=?',target.target_id,target.input_sha256),proposals:await rows(db,'SELECT proposal_id,created_at,payload_json FROM enrichment_proposals WHERE target_id=? ORDER BY created_at DESC LIMIT 20',target.target_id)});
    if(url.pathname.endsWith('/source')&&request.method==='GET')return json((await sourceContents(env,target,[url.searchParams.get('source')]))[0]);
    if(url.pathname.endsWith('/citations')&&request.method==='GET'){
      const offset=Number(url.searchParams.get('offset')||0);if(!Number.isInteger(offset)||offset<0)err('invalid_offset');
      const edges=await rows(db,'SELECT * FROM enrichment_citation_observations WHERE target_id=? ORDER BY observation_id LIMIT 101 OFFSET ?',target.target_id,offset);
      return json({edges:edges.slice(0,100),next_offset:edges.length>100?offset+100:null,coverage:await rows(db,'SELECT * FROM enrichment_citation_coverage WHERE target_id=? ORDER BY observed_at DESC LIMIT 100',target.target_id)});
    }
    if(request.method==='POST'&&url.pathname.endsWith('/source')){
      if(!request.headers.get('Content-Type')?.startsWith('application/json'))err('json_required');
      const raw=await request.text();if(raw.length>2100000)err('payload_too_large',413);
      const data=JSON.parse(raw), fields=['input_sha256','source_url','evidence_kind','text','version_label','language','retention_basis','licence_status'];
      if(!data||typeof data!=='object'||Array.isArray(data)||Object.keys(data).some(k=>!fields.includes(k))||fields.some(k=>!Object.hasOwn(data,k)))err('invalid_source_fields');
      if(data.input_sha256!==target.input_sha256)err('stale_input',409);
      return json({source_id:await saveSource(env,target,{...data,provider:'Curator-supplied source'},Date.now()),scientific_status:'unassessed',access_status:'not_determined'},201);
    }
    if(request.method==='POST'&&url.pathname.endsWith('/proposal')){
      if(!request.headers.get('Content-Type')?.startsWith('application/json'))err('json_required');
      const raw=await request.text();if(raw.length>250000)err('payload_too_large',413);
      return json(await storeExtraction(env,target,JSON.parse(raw)),201);
    }
    return json({error_code:'method_or_route_not_allowed'},405);
  }catch(e){return json({error_code:e.code||'enrichment_request_failed'},e.status||500);}
}
