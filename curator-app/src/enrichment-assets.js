/* Candidate-bound original bytes and finite bibliography; no scientific acceptance. */
import publicSchema from '../../schema/public-enrichment-assets.schema.json' with {type:'json'};
import cycle from '../../config/archive-cycle.json' with {type:'json'};
import documentSchema from '../../schema/document-import.schema.json' with {type:'json'};
import bibliographySchema from '../../schema/bibliography-import.schema.json' with {type:'json'};
import {validateShape,normalDoi} from './paper-enrichment.js';
import {canonicalJson,sha256} from './review-v2.js';
const S=(db,sql,...v)=>db.prepare(sql).bind(...v);
const rows=async(db,sql,...v)=>(await S(db,sql,...v).all()).results;
const fail=(message,status=422)=>{throw Object.assign(Error(message),{code:message,status})};
const digest=bytes=>crypto.subtle.digest('SHA-256',bytes).then(b=>Array.from(new Uint8Array(b),x=>x.toString(16).padStart(2,'0')).join(''));
const MAX=4194304;
const safeUrl=value=>{try{if(typeof value!=='string'||value.length>2000||/[\u0000-\u0020\u007f]/.test(value))return false;const u=new URL(value);return !/(token|secret|signature|session|authorization)=/i.test(u.hash)&&u.protocol==='https:'&&!u.username&&!u.password&&!/(^|\.)(localhost|internal|workers\.dev|r2\.dev)$/i.test(u.hostname)&&!/^\d+(\.\d+){3}$/.test(u.hostname)&&!u.hostname.includes(':')&&![...u.searchParams.keys()].some(k=>/token|secret|signature|session|api.?key|authorization|^sig$|^key$|x-amz|x-goog/i.test(k))}catch{return false}};
function safeMetadata(value){if(value===null)return;if(typeof value==='string'&&(/[\u0000-\u001f\u007f]/.test(value)||/\b(?:Bearer\s+|gh[pousr]_|sk-proj-)|-----BEGIN .*PRIVATE KEY/i.test(value)))fail('unsafe_bibliographic_metadata');if(value&&typeof value==='object')for(const v of Object.values(value))safeMetadata(v)}
export function privateBinaryStore(storage){
 return{
  async put(key,bytes){
   if(!/^[a-f0-9]{64}$/.test(key)||!(bytes instanceof Uint8Array)||!bytes.length||bytes.length>MAX||await digest(bytes)!==key)fail('invalid_document_bytes');
   const root='document:'+key,parts=[];for(let i=0;i<bytes.length;i+=65536)parts.push(bytes.slice(i,i+65536));
   await storage.transaction(async tx=>{const old=await tx.get(root);if(old&&(old.digest!==key||old.length!==bytes.length))fail('immutable_document_conflict',409);const values={[root]:{digest:key,length:bytes.length,count:parts.length}};parts.forEach((b,i)=>values[root+':'+i]=b);await tx.put(values)});
  },
  async get(key){
   if(!/^[a-f0-9]{64}$/.test(key))fail('invalid_document_key');const root='document:'+key,meta=await storage.get(root);if(!meta)return null;
   if(meta.digest!==key||!Number.isInteger(meta.length)||meta.length<1||meta.length>MAX||meta.count!==Math.ceil(meta.length/65536))fail('document_integrity_failure',409);
   const keys=Array.from({length:meta.count},(_,i)=>root+':'+i),parts=await storage.get(keys),bytes=new Uint8Array(meta.length);let at=0;
   for(const k of keys){const part=parts.get(k);if(!(part instanceof Uint8Array)||part.length!==Math.min(65536,meta.length-at))fail('document_integrity_failure',409);bytes.set(part,at);at+=part.length}
   if(await digest(bytes)!==key)fail('document_integrity_failure',409);return bytes;
  }
 };
}
async function current(env,targetId,inputHash){
 const target=await S(env.REVIEW_DB,'SELECT * FROM enrichment_targets WHERE target_id=? AND active=1 AND cycle_id=?',targetId,cycle.review_id).first();
 if(!target)fail('target_not_found',404);if(inputHash!==undefined&&inputHash!==target.input_sha256)fail('stale_input',409);return target;
}
async function retainedSource(env,target,sourceId){
 const source=await S(env.REVIEW_DB,'SELECT * FROM enrichment_sources WHERE source_id=? AND target_id=? AND input_sha256=?',sourceId,target.target_id,target.input_sha256).first();
 if(!source)fail('invalid_source_scope');const object=await env.REVIEW_EVIDENCE.get(source.storage_key);if(!object||await sha256(await object.text())!==source.content_sha256)fail('source_integrity_failure',409);return source;
}
export async function importDocument(env,targetId,data,now=Date.now()){
 validateShape(data,documentSchema,'$',documentSchema);const target=await current(env,targetId,data.input_sha256),source=await retainedSource(env,target,data.source_id);
 if(source.evidence_kind!=='full_text'||source.content_sha256!==data.source_text_sha256||!safeUrl(source.source_url))fail('full_text_source_binding_required');
 if(!data.retention_basis.trim()||!data.licence_status.trim()||!data.attribution.trim())fail('document_rights_basis_required');
 if(data.licence_url!==null&&!safeUrl(data.licence_url))fail('document_licence_url_invalid');
 if(data.visibility==='public'&&(!data.rights_verified||!/^https:\/\/creativecommons\.org\/(?:licenses\/(?:by|by-sa)\/4\.0|publicdomain\/zero\/1\.0)\/$/.test(data.licence_url||'')))fail('public_redistribution_authorisation_required');
 if(!data.bytes_base64.length||data.bytes_base64.length%4||!/^[A-Za-z0-9+/]*={0,2}$/.test(data.bytes_base64))fail('invalid_pdf_encoding');
 let bytes;try{bytes=Uint8Array.from(atob(data.bytes_base64),c=>c.charCodeAt(0))}catch{fail('invalid_pdf_encoding')}
 if(!bytes.length||bytes.length>MAX||new TextDecoder().decode(bytes.slice(0,8)).match(/^%PDF-\d\.\d/)==null||!new TextDecoder().decode(bytes.slice(-2048)).includes('%%EOF'))fail('invalid_pdf_bytes');
 if(await digest(bytes)!==data.pdf_sha256)fail('pdf_hash_mismatch',409);
 const {bytes_base64,...metadata}=data;safeMetadata(metadata);const id=await sha256(canonicalJson([targetId,metadata]));
 const old=await S(env.REVIEW_DB,'SELECT document_id FROM enrichment_documents WHERE document_id=?',id).first();
 if(old){const original=await env.REVIEW_DOCUMENTS.get(data.pdf_sha256);if(!original||await digest(original)!==data.pdf_sha256)fail('document_readback_failed',503);return{document_id:id,replayed:true,pdf_sha256:data.pdf_sha256,byte_length:original.length,visibility:data.visibility}}
 await env.REVIEW_DOCUMENTS.put(data.pdf_sha256,bytes);const original=await env.REVIEW_DOCUMENTS.get(data.pdf_sha256);
 if(!original||await digest(original)!==data.pdf_sha256)fail('document_readback_failed',503);
 await current(env,targetId,data.input_sha256);
 await S(env.REVIEW_DB,'INSERT INTO enrichment_documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',id,targetId,data.input_sha256,data.source_id,source.source_url,data.pdf_sha256,data.source_text_sha256,bytes.length,data.pdf_sha256,source.version_label,data.retention_basis,data.licence_status,data.licence_url,data.attribution,data.visibility,data.rights_verified?1:0,new Date(now).toISOString()).run();
 if(!await S(env.REVIEW_DB,'SELECT document_id FROM enrichment_documents WHERE document_id=?',id).first())fail('document_receipt_readback_failed',503);
 return{document_id:id,replayed:false,pdf_sha256:data.pdf_sha256,byte_length:bytes.length,visibility:data.visibility};
}
export async function listDocuments(env,targetId){const target=await current(env,targetId);return rows(env.REVIEW_DB,'SELECT document_id,source_url,pdf_sha256,byte_length,version_label,licence_status,licence_url,attribution,visibility,observed_at FROM enrichment_documents WHERE target_id=? AND input_sha256=? ORDER BY observed_at DESC,document_id DESC',targetId,target.input_sha256)}
export async function documentResponse(env,targetId,documentId,request,{publicOnly=false}={}){
 const target=await current(env,targetId);const doc=await S(env.REVIEW_DB,'SELECT * FROM enrichment_documents WHERE target_id=? AND input_sha256=? AND document_id=?',targetId,target.input_sha256,documentId).first();if(!doc)fail('document_not_found',404);
 if(publicOnly){const latest=await S(env.REVIEW_DB,'SELECT * FROM enrichment_documents WHERE target_id=? AND input_sha256=? AND pdf_sha256=? ORDER BY observed_at DESC,document_id DESC LIMIT 1',targetId,target.input_sha256,doc.pdf_sha256).first();if(doc.visibility!=='public'||!doc.rights_verified||latest.document_id!==doc.document_id)fail('document_not_public',404)}
 const bytes=await env.REVIEW_DOCUMENTS.get(doc.storage_key);if(!bytes||bytes.length!==doc.byte_length||await digest(bytes)!==doc.pdf_sha256)fail('document_integrity_failure',409);
 const h={'Content-Type':'application/pdf','Content-Disposition':'inline; filename="paper.pdf"','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Accept-Ranges':'bytes','Content-Security-Policy':"sandbox; default-src 'none'",ETag:'"'+doc.pdf_sha256+'"'};
 const range=request.headers.get('Range');let start=0,end=bytes.length-1;
 if(range){const m=/^bytes=(\d*)-(\d*)$/.exec(range);if(!m||(!m[1]&&!m[2]))return new Response(null,{status:416,headers:{...h,'Content-Range':'bytes */'+bytes.length}});
  if(!m[1])start=Math.max(0,bytes.length-Number(m[2]));else{start=Number(m[1]);if(m[2])end=Math.min(end,Number(m[2]))}
  if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start>end||start>=bytes.length)return new Response(null,{status:416,headers:{...h,'Content-Range':'bytes */'+bytes.length}});
  h['Content-Range']=`bytes ${start}-${end}/${bytes.length}`;
 }
 h['Content-Length']=String(end-start+1);return new Response(request.method==='HEAD'?null:bytes.slice(start,end+1),{status:range?206:200,headers:h});
}
export async function importBibliography(env,targetId,data,now=Date.now()){
 validateShape(data,bibliographySchema,'$',bibliographySchema);const target=await current(env,targetId,data.input_sha256),source=await retainedSource(env,target,data.source_id);safeMetadata(data.entries);
 if(data.scope==='paper_bibliography'&&source.evidence_kind!=='full_text')fail('bibliography_full_text_required');
 if(data.scope==='provider_references'&&source.evidence_kind!=='metadata')fail('bibliography_metadata_source_required');
 if(data.declared_count!==null&&data.declared_count<data.entries.length)fail('bibliography_count_conflict');
 if(data.coverage==='source_complete'&&(data.declared_count===null||data.declared_count!==data.entries.length))fail('bibliography_completeness_not_attested');
 if(data.coverage==='not_reported'&&(data.entries.length||data.declared_count!==null||data.scope!=='paper_bibliography'))fail('bibliography_missingness_conflict');
 const seen=new Set();for(const e of data.entries){if(!Number.isSafeInteger(e.position)||e.position<1||seen.has(e.position)||!e.source_locator.trim())fail('bibliography_entry_identity');seen.add(e.position);if(e.year!==null&&(e.year>new Date(now).getUTCFullYear()+1||e.year<1000))fail('bibliography_year_invalid');if(e.url!==null&&!safeUrl(e.url))fail('bibliography_url_invalid');if(e.doi!==null&&(normalDoi(e.doi)!==e.doi||!/^10\.\d{4,9}\/\S+$/i.test(e.doi)))fail('bibliography_doi_invalid');if(!e.title&&!e.doi&&!e.url&&!e.unresolved_identity)fail('bibliography_unresolved_required')}
 const payload=canonicalJson(data),hash=await sha256(payload),id=await sha256(canonicalJson([targetId,hash]));
 const old=await S(env.REVIEW_DB,'SELECT bibliography_id FROM enrichment_bibliography_snapshots WHERE bibliography_id=?',id).first();if(old)return{bibliography_id:id,replayed:true};
 await current(env,targetId,data.input_sha256);
 await S(env.REVIEW_DB,'INSERT INTO enrichment_bibliography_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?)',id,targetId,data.input_sha256,data.source_id,data.scope,data.coverage,data.declared_count,data.entries.length,payload,hash,new Date(now).toISOString()).run();
 if(!await S(env.REVIEW_DB,'SELECT bibliography_id FROM enrichment_bibliography_snapshots WHERE bibliography_id=?',id).first())fail('bibliography_receipt_readback_failed',503);
 return{bibliography_id:id,replayed:false};
}
export async function publicAssets(env,candidateId,offset=0,revision=null){
 if(!Number.isSafeInteger(offset)||offset<0||offset>1000)fail('invalid_offset');
 const target=await S(env.REVIEW_DB,'SELECT * FROM enrichment_targets WHERE record_id=? AND active=1 AND cycle_id=?',candidateId,cycle.review_id).first();
 const raw=target?JSON.parse(target.record_json):null,candidate=raw?{id:raw.id,title:raw.title,doi:normalDoi(raw.doi),sourceLinks:raw.sourceLinks}:null;
 const empty={schema_version:1,projection_version:'CILE-PUBLIC-ASSETS-1',candidate_id:candidateId,candidate,documents:[],bibliography:null};if(!target)return{...empty,availability:'not_registered'};
 safeMetadata(candidate);if(candidate.id!==candidateId||!Array.isArray(candidate.sourceLinks)||candidate.sourceLinks.some(u=>!safeUrl(u))||await sha256(canonicalJson(raw))!==target.input_sha256)fail('asset_identity_integrity',409);
 const docs=await listDocuments(env,target.target_id);const seen=new Set();
 for(const d of docs){if(seen.has(d.pdf_sha256))continue;seen.add(d.pdf_sha256);if(d.visibility!=='public')continue;
  const request=new Request('https://enrichment.internal/document',{method:'HEAD'});await documentResponse(env,target.target_id,d.document_id,request,{publicOnly:true});
  empty.documents.push({document_id:d.document_id,source_url:d.source_url,version_label:d.version_label,pdf_sha256:d.pdf_sha256,byte_length:d.byte_length,licence_url:d.licence_url,attribution:d.attribution,observed_at:d.observed_at});
 }
 const row=await S(env.REVIEW_DB,"SELECT * FROM enrichment_bibliography_snapshots WHERE target_id=? AND input_sha256=? ORDER BY CASE scope WHEN 'paper_bibliography' THEN 0 ELSE 1 END,observed_at DESC,bibliography_id DESC LIMIT 1",target.target_id,target.input_sha256).first();
 if(offset>0&&(!row||row.payload_sha256!==revision))fail('bibliography_snapshot_changed',409);
 if(row){if(await sha256(row.payload_json)!==row.payload_sha256)fail('bibliography_integrity_failure',409);const data=JSON.parse(row.payload_json);validateShape(data,bibliographySchema,'$',bibliographySchema);const source=await retainedSource(env,target,row.source_id);if(!safeUrl(source.source_url))fail('bibliography_source_url');safeMetadata(data.entries);empty.bibliography={scope:row.scope,coverage:row.coverage,declared_count:row.declared_count,entries_count:row.entries_count,source_url:source.source_url,version_label:source.version_label,observed_at:row.observed_at,revision:row.payload_sha256,entries:data.entries.slice(offset,offset+100).map(({source_locator,...e})=>e),next_offset:offset+100<data.entries.length?offset+100:null,assessment_state:'unreviewed_proposal'}}
 await current(env,target.target_id,target.input_sha256);const out={...empty,availability:'registered'};validateShape(out,publicSchema,'$',publicSchema);return out;
}
export async function servePublicAssets(request,store){
 const url=new URL(request.url),id=url.searchParams.get('id');const headers={'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Access-Control-Allow-Origin':'https://colazeta.github.io','Vary':'Origin'};
 const bad=(error,status)=>Response.json({error},{status,headers});
 if(request.method==='OPTIONS')return new Response(null,{status:204,headers:{...headers,'Access-Control-Allow-Methods':'GET, HEAD','Access-Control-Max-Age':'300'}});
 if(!['GET','HEAD'].includes(request.method)||!/^CAND-[A-Za-z0-9-]{1,100}$/.test(id||'')||[...url.searchParams.keys()].some(k=>!['id','document','offset','revision'].includes(k))||[...url.searchParams.keys()].some(k=>url.searchParams.getAll(k).length!==1))return bad('invalid_request',400);
 const revision=url.searchParams.get('revision');if(revision!==null&&!/^[a-f0-9]{64}$/.test(revision))return bad('invalid_request',400);
 const doc=url.searchParams.get('document'),offset=url.searchParams.get('offset')||'0';if((doc&&!/^[a-f0-9]{64}$/.test(doc))||!/^\d{1,4}$/.test(offset)||Number(offset)>1000||(doc&&url.searchParams.has('offset')))return bad('invalid_request',400);
 if(!store)return bad('assets_temporarily_unavailable',503);
 try{const h={};if(request.headers.has('Range'))h.Range=request.headers.get('Range');const r=await store.fetch(new Request('https://enrichment.internal/public-assets?'+url.searchParams,{method:request.method,headers:h}));
  if(doc&&(r.ok||r.status===416)){const hh=new Headers(r.headers);hh.set('Access-Control-Allow-Origin','https://colazeta.github.io');hh.set('Vary','Origin');return new Response(r.body,{status:r.status,headers:hh})}
  if(!r.ok)return bad(r.status===404?'document_not_public':'assets_temporarily_unavailable',[404,409,416].includes(r.status)?r.status:503);
  const data=await r.json();validateShape(data,publicSchema,'$',publicSchema);if(data.candidate_id!==id||(data.candidate&&data.candidate.id!==id))throw Error('identity_mismatch');return new Response(request.method==='HEAD'?null:JSON.stringify(data),{status:200,headers});
 }catch{return bad('assets_temporarily_unavailable',503)}
}

// Materialise bibliographic fields from an already retained provider response.
// Exhausting this finite list never certifies the actual-paper bibliography.
export async function retainProviderBibliography(env,targetId,now=Date.now()) {
 const target=await current(env,targetId),source=await S(env.REVIEW_DB,"SELECT * FROM enrichment_sources WHERE target_id=? AND input_sha256=? AND provider='Crossref' AND evidence_kind='metadata' ORDER BY observed_at DESC,source_id DESC LIMIT 1",targetId,target.input_sha256).first();
 if(!source)return{status:'source_not_available',scope:'provider_references'};
 await retainedSource(env,target,source.source_id);const message=JSON.parse(await(await env.REVIEW_EVIDENCE.get(source.storage_key)).text());
 const record=JSON.parse(target.record_json);if(!record.doi||normalDoi(message.DOI)!==normalDoi(record.doi))fail('provider_bibliography_identity_conflict');
 if(!Array.isArray(message.reference))return{status:'references_not_returned',scope:'provider_references'};
 if(message.reference.length>1000)fail('provider_bibliography_limit');
 const value=(v,max)=>typeof v==='string'&&v.trim()&&v.length<=max?v:null;
 const entries=message.reference.map((r,i)=>{
  if(!r||typeof r!=='object'||Array.isArray(r))fail('provider_bibliography_entry_invalid');
  const d=normalDoi(r.DOI),doi=/^10\.\d{4,9}\/\S+$/i.test(d)&&d.length<=500?d:null;
  const title=value(r['article-title'],1000)||value(r['volume-title'],1000);
  return{position:i+1,title,authors:value(r.author,200)?[r.author]:[],year:/^\d{4}$/.test(String(r.year))?Number(r.year):null,venue:value(r['journal-title'],500),doi,url:typeof r.URL==='string'&&safeUrl(r.URL)?r.URL:null,source_locator:'Crossref reference['+i+']',unresolved_identity:!doi};
 });
 const declared=Number.isSafeInteger(message['reference-count'])&&message['reference-count']>=0?message['reference-count']:null;
 if(declared!==null&&declared<entries.length)fail('provider_bibliography_count_conflict');
 const receipt=await importBibliography(env,targetId,{input_sha256:target.input_sha256,source_id:source.source_id,scope:'provider_references',coverage:declared===entries.length?'source_complete':'partial',declared_count:declared,entries},now);
 return{status:'provider_snapshot_retained',scope:'provider_references',entries_count:entries.length,declared_count:declared,replayed:receipt.replayed};
}
