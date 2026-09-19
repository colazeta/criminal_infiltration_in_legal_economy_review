/* Source-grounded document reads/indexing in the existing private archive.
 * Indexes are derived; source strings, bytes and scientific relations are unchanged. */
import {canonicalJson,sha256} from './review-v2.js';
import {importDocument,publicRightsAllowed,redistributionAllowed} from './enrichment-assets.js';
import {ARCHIVE_TABLES,ARCHIVE_ROW_LIMIT,ARCHIVE_JSON_LIMIT} from './architecture-audit.js';
import {readNormalizedExtraction} from './extraction-relations.js';
import {readPublicResearch,readPublicCompletion,safeResearchUrl} from './public-paper-research.js';
import cycle from '../../config/archive-cycle.json' with {type:'json'};

export const DOCUMENT_PROTOCOL='CILE-DOCUMENT-TEXT-1';
const S=(db,sql,...v)=>db.prepare(sql).bind(...v);
const rows=async(db,sql,...v)=>(await S(db,sql,...v).all()).results;
export const documentError=(code,status=422)=>{throw Object.assign(Error(code),{code,status})};
const fail=documentError;
export const digestBytes=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
export const validRecordId=id=>typeof id==='string'&&/^CAND-[A-Za-z0-9-]{1,100}$/.test(id);
const hashId=id=>typeof id==='string'&&/^[a-f0-9]{64}$/.test(id);
export const lexicalTerms=text=>(text.normalize('NFKC').toLowerCase().match(/[\p{L}\p{N}]{2,64}/gu)||[]);
export async function currentTarget(env,id){
 if(!validRecordId(id))fail('invalid_paper_id');
 const t=await S(env.REVIEW_DB,'SELECT * FROM enrichment_targets WHERE record_id=? AND active=1 AND cycle_id=?',id,cycle.review_id).first();
 if(!t)fail('paper_not_found',404);
 if(await sha256(canonicalJson(JSON.parse(t.record_json)))!==t.input_sha256)fail('paper_identity_integrity',409);
 return t;
}
export async function checkedDocument(env,target,documentId,{publicOnly=false}={}){
 if(!hashId(documentId))fail('invalid_document_id');
 const d=await S(env.REVIEW_DB,'SELECT * FROM enrichment_documents WHERE document_id=? AND target_id=? AND input_sha256=?',documentId,target.target_id,target.input_sha256).first();
 if(!d)fail('document_not_found',404);
 if(publicOnly){
  const latest=await S(env.REVIEW_DB,'SELECT document_id FROM enrichment_documents WHERE target_id=? AND input_sha256=? AND pdf_sha256=? ORDER BY observed_at DESC,document_id DESC LIMIT 1',target.target_id,target.input_sha256,d.pdf_sha256).first();
  if(!publicRightsAllowed(d)||latest?.document_id!==d.document_id)fail('document_not_public',404);
 }
 const bytes=await env.REVIEW_DOCUMENTS.get(d.storage_key);
 if(!bytes||bytes.length!==d.byte_length||await digestBytes(bytes)!==d.pdf_sha256)fail('document_integrity_failure',409);
 const source=await S(env.REVIEW_DB,'SELECT * FROM enrichment_sources WHERE source_id=? AND target_id=? AND input_sha256=?',d.source_id,target.target_id,target.input_sha256).first();
 if(!source||source.evidence_kind!=='full_text'||source.content_sha256!==d.source_text_sha256)fail('document_source_integrity',409);
 const obj=await env.REVIEW_EVIDENCE.get(source.storage_key),text=obj?await obj.text():null;
 if(text===null||await sha256(text)!==source.content_sha256)fail('document_source_integrity',409);
 return {document:d,source,text,bytes};
}
// Partition the exact retained string. Offsets use the existing JS/UTF-16 contract.
export function partitionPages(text){
 const out=[];let start=0;
 for(let i=0;i<text.length;i++)if(text[i]==='\f'){out.push({page_number:out.length+1,start_offset:start,end_offset:i+1});start=i+1}
 if(start<text.length){
  if(out.length&&/^\s*$/.test(text.slice(start)))out.at(-1).end_offset=text.length;
  else out.push({page_number:out.length+1,start_offset:start,end_offset:text.length});
 }
 if(!out.length&&text.length)out.push({page_number:1,start_offset:0,end_offset:text.length});
 return out;
}
export async function indexDocument(env,targetId,documentId,attestation,now=Date.now()){
 const keys=['protocol_version','method','extractor_version','page_count','text_sha256','pdf_sha256','parser_validated'];
 if(!attestation||Object.keys(attestation).sort().join()!==keys.sort().join()||attestation.protocol_version!==DOCUMENT_PROTOCOL||!['native','ocr'].includes(attestation.method)||attestation.parser_validated!==true||typeof attestation.extractor_version!=='string'||!/^[-\w .+():/]{1,160}$/.test(attestation.extractor_version)||!Number.isSafeInteger(attestation.page_count)||attestation.page_count<1||attestation.page_count>500)fail('invalid_extraction_attestation');
 const target=await S(env.REVIEW_DB,'SELECT * FROM enrichment_targets WHERE target_id=? AND active=1 AND cycle_id=?',targetId,cycle.review_id).first();
 if(!target)fail('paper_not_found',404);
 const {document:d,source,text}=await checkedDocument(env,target,documentId);
 if(attestation.pdf_sha256!==d.pdf_sha256||attestation.text_sha256!==source.content_sha256)fail('extraction_hash_mismatch',409);
 const pages=partitionPages(text);
 if(pages.length!==attestation.page_count||text.replace(/\s/g,'').length<100||text.length>4000000)fail('extraction_quality_failure');
 const manifestationId=await sha256(canonicalJson(['CILE-MANIFESTATION-1',targetId,target.input_sha256,d.source_url,d.version_label]));
 const extractionId=await sha256(canonicalJson([documentId,attestation]));
 const old=await S(env.REVIEW_DB,'SELECT extraction_id FROM enrichment_document_extractions WHERE document_id=? AND protocol_version=?',documentId,DOCUMENT_PROTOCOL).first();
 if(old){if(old.extraction_id!==extractionId)fail('extraction_revision_conflict',409);await verifyIndex(env,target,documentId);return {document_id:documentId,manifestation_id:manifestationId,extraction_id:extractionId,replayed:true}}
 const statements=[
  S(env.REVIEW_DB,'INSERT OR IGNORE INTO enrichment_manifestations VALUES (?,?,?,?,?)',manifestationId,targetId,target.input_sha256,d.source_url,d.version_label),
  S(env.REVIEW_DB,'INSERT INTO enrichment_document_bindings VALUES (?,?)',documentId,manifestationId),
  S(env.REVIEW_DB,'INSERT INTO enrichment_document_extractions VALUES (?,?,?,?,?,?,?,?,?,?,?)',extractionId,documentId,source.source_id,source.content_sha256,text.length,pages.length,attestation.method,attestation.extractor_version,'utf16',DOCUMENT_PROTOCOL,new Date(now).toISOString())
 ];let chunks=0,postings=0;
 for(const page of pages){
  statements.push(S(env.REVIEW_DB,'INSERT INTO enrichment_document_pages VALUES (?,?,?,?)',extractionId,page.page_number,page.start_offset,page.end_offset));
  for(let at=page.start_offset;at<page.end_offset;){
   let end=Math.min(at+1800,page.end_offset);
   if(end<page.end_offset){const before=text.slice(at,end),space=Math.max(before.lastIndexOf(' '),before.lastIndexOf('\n'));if(space>1200)end=at+space+1;}
   if(end<page.end_offset&&/[\uDC00-\uDFFF]/.test(text[end]))end--;
   const part=text.slice(at,end),partHash=await sha256(part),chunk=await sha256(canonicalJson([extractionId,page.page_number,at,end,partHash]));
   statements.push(S(env.REVIEW_DB,'INSERT INTO enrichment_document_chunks VALUES (?,?,?,?,?,?)',chunk,extractionId,page.page_number,at,end,partHash));chunks++;
   const terms=new Map();for(const term of lexicalTerms(part))terms.set(term,(terms.get(term)||0)+1);
   for(const [term,n] of terms){statements.push(S(env.REVIEW_DB,'INSERT INTO enrichment_document_terms VALUES (?,?,?)',term,chunk,n));postings++}
   at=end;
  }
 }
 if(chunks>2500||postings>60000)fail('document_index_limit');
 if(!env.REVIEW_DB.batchValidated)fail('document_atomic_index_required',503);
 // Check the actual post-write population inside the existing SQLite transaction.
 // Capacity failure rolls back every index row, preserving the backup gate limits.
 await env.REVIEW_DB.batchValidated(statements,ARCHIVE_TABLES.map(table=>S(env.REVIEW_DB,`SELECT * FROM ${table} LIMIT ${ARCHIVE_ROW_LIMIT+1}`)),readback=>{
  let size=0;for(const {results} of readback){size+=canonicalJson(results).length;if(results.length>ARCHIVE_ROW_LIMIT||size>ARCHIVE_JSON_LIMIT)fail('document_preservation_capacity',409)}return true;
 });
 await verifyIndex(env,target,documentId);
 return {document_id:documentId,manifestation_id:manifestationId,extraction_id:extractionId,page_count:pages.length,chunks,postings,replayed:false};
}
export async function verifyIndex(env,target,documentId,{publicOnly=false}={}){
 const checked=await checkedDocument(env,target,documentId,{publicOnly});
 const x=await S(env.REVIEW_DB,'SELECT x.*,b.manifestation_id FROM enrichment_document_extractions x JOIN enrichment_document_bindings b ON b.document_id=x.document_id WHERE x.document_id=?',documentId).first();
 if(!x)fail('document_extraction_missing',409);
 const pages=await rows(env.REVIEW_DB,'SELECT page_number,start_offset,end_offset FROM enrichment_document_pages WHERE extraction_id=? ORDER BY page_number',x.extraction_id);
 if(x.source_id!==checked.source.source_id||x.text_sha256!==checked.source.content_sha256||x.text_length!==checked.text.length||x.page_count!==pages.length||canonicalJson(pages)!==canonicalJson(partitionPages(checked.text)))fail('document_index_integrity',409);
 return {...checked,extraction:x,pages};
}
export async function retainAndIndex(env,targetId,data,now=Date.now()){
 const {extraction,...document}=data||{};
 const receipt=await importDocument(env,targetId,document,now);
 if(!extraction)return {...receipt,extraction_status:'pending',blocker:'extraction_attestation_required'};
 return {...receipt,extraction:await indexDocument(env,targetId,receipt.document_id,extraction,now),extraction_status:'verified'};
}
export function rightsStatus(d){
 if(redistributionAllowed(d))return 'public_rehost_allowed';
 if(!d.rights_verified)return 'rights_unresolved';
 return 'private_analysis_only';
}
export async function documentLibrary(env,id,{publicOnly=true}={}){
 const target=await currentTarget(env,id),record=JSON.parse(target.record_json);
 const all=await rows(env.REVIEW_DB,'SELECT d.*,b.manifestation_id,x.extraction_id,x.page_count,x.method FROM enrichment_documents d LEFT JOIN enrichment_document_bindings b ON b.document_id=d.document_id LEFT JOIN enrichment_document_extractions x ON x.document_id=d.document_id WHERE d.target_id=? AND d.input_sha256=? ORDER BY d.observed_at DESC,d.document_id DESC LIMIT 101',target.target_id,target.input_sha256);
 const result=[],seen=new Set();
 for(const d of all){
  if(seen.has(d.pdf_sha256))continue;seen.add(d.pdf_sha256);
  // Metadata of private copies never includes private IDs, hashes or storage paths.
  const canServe=publicRightsAllowed(d);
  const item={source_url:safeResearchUrl(d.source_url)?d.source_url:null,version:d.version_label,rights_status:rightsStatus(d),licence_uri:d.licence_url,attribution:d.attribution,public_downloadable:canServe};
  if(!publicOnly||canServe){
   await checkedDocument(env,target,d.document_id,{publicOnly});
   Object.assign(item,{document_id:d.document_id,manifestation_id:d.manifestation_id||null,mime_type:'application/pdf',sha256:d.pdf_sha256,byte_size:d.byte_length,retrieved_at:d.observed_at,extraction_status:d.extraction_id?'indexed':'pending',page_count:d.page_count||null,extraction_method:d.method||null});
  }
  result.push(item);
 }
 const bibliography=await S(env.REVIEW_DB,'SELECT authors,publication_year,venue,review_status FROM enrichment_catalogue_index WHERE target_id=? AND input_sha256=?',target.target_id,target.input_sha256).first();
 return {projection_version:'CILE-DOCUMENT-LIBRARY-1',paper_id:null,candidate_id:id,identity_status:'candidate_only',title:record.title,doi:record.doi,...bibliography,source_urls:record.sourceLinks.filter(safeResearchUrl),documents:result,truncated:all.length>100,blocker:result.length?null:'retained_full_text_missing',archive_commit:env.DEPLOY_COMMIT||null,input_revision:target.input_sha256};
}
export async function readDocumentPage(env,id,documentId,page,{publicOnly=true}={}){
 if(!Number.isSafeInteger(page)||page<1||page>500)fail('invalid_page');
 const target=await currentTarget(env,id),v=await verifyIndex(env,target,documentId,{publicOnly}),p=v.pages[page-1];
 if(!p)fail('page_not_found',404);
 const text=v.text.slice(p.start_offset,p.end_offset);
 if(text.length>32000)fail('page_output_limit');
 return {paper_id:null,candidate_id:id,document_id:documentId,manifestation_id:v.extraction.manifestation_id,page,page_count:v.pages.length,section:null,offset_unit:'utf16',start_offset:p.start_offset,end_offset:p.end_offset,text,content_role:'untrusted_source_data',source_url:v.document.source_url,source_coverage:'full_text',extraction_method:v.extraction.method,licence_uri:v.document.licence_url};
}
export async function searchFullText(env,args,{publicOnly=true}={}){
 const terms=[...new Set(lexicalTerms(args.query||''))];
 if(!terms.length||terms.length>12||String(args.query).length>300)fail('invalid_search_query');
 const top=args.top_k??10;if(!Number.isSafeInteger(top)||top<1||top>20)fail('invalid_top_k');
 const ids=args.paper_ids||[];if(!Array.isArray(ids)||ids.length>20||ids.some(x=>!validRecordId(x)))fail('invalid_paper_ids');
 const conditions=['t.active=1','t.cycle_id=?','d.input_sha256=t.input_sha256',`i.term IN (${terms.map(()=>'?')})`];
 const values=[cycle.review_id,...terms];
 if(ids.length){conditions.push(`t.record_id IN (${ids.map(()=>'?')})`);values.push(...ids)}
 if(publicOnly)conditions.push("d.visibility='public' AND d.rights_verified=1 AND d.licence_url IN ('https://creativecommons.org/licenses/by/4.0/','https://creativecommons.org/licenses/by-sa/4.0/','https://creativecommons.org/publicdomain/zero/1.0/')");
 // Latest rights assertion for these bytes always controls access, including revocations.
 conditions.push('NOT EXISTS (SELECT 1 FROM enrichment_documents newer WHERE newer.target_id=d.target_id AND newer.input_sha256=d.input_sha256 AND newer.pdf_sha256=d.pdf_sha256 AND (newer.observed_at>d.observed_at OR (newer.observed_at=d.observed_at AND newer.document_id>d.document_id)))');
 const hits=await rows(env.REVIEW_DB,`SELECT c.*,d.document_id,t.record_id,SUM(i.occurrences) score FROM enrichment_document_terms i JOIN enrichment_document_chunks c ON c.chunk_id=i.chunk_id JOIN enrichment_document_extractions x ON x.extraction_id=c.extraction_id JOIN enrichment_documents d ON d.document_id=x.document_id JOIN enrichment_targets t ON t.target_id=d.target_id WHERE ${conditions.join(' AND ')} GROUP BY c.chunk_id HAVING COUNT(DISTINCT i.term)=? ORDER BY score DESC,c.chunk_id LIMIT ?`,...values,terms.length,top);
 const out=[];
 for(const hit of hits){
  const target=await currentTarget(env,hit.record_id),v=await verifyIndex(env,target,hit.document_id,{publicOnly});
  const text=v.text.slice(hit.start_offset,hit.end_offset);
  if(await sha256(text)!==hit.text_sha256)fail('document_chunk_integrity',409);

  // Source offsets are calculated on the original string, never on normalised search text.
  const rawMatch=text.toLowerCase().indexOf(terms[0]);let start=rawMatch>=0?Math.max(0,rawMatch-100):0;
  if(/[\uDC00-\uDFFF]/.test(text[start]))start++;
  let end=Math.min(start+500,text.length);if(/[\uDC00-\uDFFF]/.test(text[end]))end--;
  out.push({paper_id:null,candidate_id:hit.record_id,title:JSON.parse(target.record_json).title,document_id:hit.document_id,manifestation_id:v.extraction.manifestation_id,chunk_id:hit.chunk_id,page:hit.page_number,section:null,locator:{offset_unit:'utf16',start_offset:hit.start_offset+start,end_offset:hit.start_offset+end,uri:`cile://papers/${hit.record_id}/fulltext/${hit.document_id}/${hit.page_number}`},passage:text.slice(start,end),score:Number(hit.score),score_method:'exact_token_frequency_all_terms',source_url:v.document.source_url,source_coverage:'full_text',content_role:'untrusted_source_data',assessment_status:'document_only'});
 }
 return {mode:'lexical',terms,hits:out,limit:top,archive_commit:env.DEPLOY_COMMIT||null};
}
export async function resolveEvidence(env,id,evidenceIds,{publicOnly=true,expectedRevision=null}={}){
 if(!Array.isArray(evidenceIds)||!evidenceIds.length||evidenceIds.length>10||evidenceIds.some(x=>typeof x!=='string'||x.length>160))fail('invalid_evidence_ids');
 const target=await currentTarget(env,id),proposal=await S(env.REVIEW_DB,'SELECT * FROM enrichment_proposals WHERE target_id=? AND input_sha256=? ORDER BY created_at DESC,proposal_id DESC LIMIT 1',target.target_id,target.input_sha256).first();
 if(!proposal)return {candidate_id:id,evidence:[],availability:'not_assessed'};
 const input=await readNormalizedExtraction(env.REVIEW_DB,proposal),publicData=publicOnly?await readPublicResearch(env,id):null;
 if(publicOnly&&publicData?.availability!=='available')fail('evidence_not_public',404);
 const revision=publicOnly?publicData.revision:proposal.payload_sha256;
 if(expectedRevision!==revision)fail('evidence_revision_changed',409);
 const selected=[];
 for(const requested of evidenceIds){
  // Public aliases come from the existing projector, in the same preserved order.
  const index=publicOnly?(publicData.research.spans||[]).findIndex(s=>s.id===requested):input.spans.findIndex(s=>s.id===requested);
  const span=input.spans[index];if(!span)fail('evidence_not_found',404);
  const doc=await S(env.REVIEW_DB,'SELECT d.document_id FROM enrichment_documents d JOIN enrichment_document_extractions x ON x.document_id=d.document_id WHERE d.target_id=? AND d.input_sha256=? AND d.source_id=? ORDER BY d.observed_at DESC,d.document_id DESC LIMIT 1',target.target_id,target.input_sha256,span.source_id).first();
  if(!doc){selected.push({evidence_id:requested,source_coverage:input.source_coverage,passage:null,blocker:'retained_indexed_document_missing'});continue}
  let v;try{v=await verifyIndex(env,target,doc.document_id,{publicOnly})}catch(e){if(publicOnly&&e.code==='document_not_public'){selected.push({evidence_id:requested,source_coverage:input.source_coverage,passage:null,blocker:'public_redistribution_not_authorised'});continue}throw e}
  if(span.start_offset<0||span.end_offset>v.text.length||span.end_offset<=span.start_offset)fail('evidence_locator_integrity',409);
  const pages=v.pages.filter(p=>span.start_offset<p.end_offset&&span.end_offset>p.start_offset).map(p=>p.page_number);
  let end=Math.min(span.end_offset,span.start_offset+800);if(/[\uDC00-\uDFFF]/.test(v.text[end]))end--;
  selected.push({evidence_id:requested,candidate_id:id,paper_id:null,document_id:doc.document_id,manifestation_id:v.extraction.manifestation_id,pages,section:null,locator:span.locator,offset_unit:'utf16',start_offset:span.start_offset,end_offset:end,evidence_end_offset:span.end_offset,truncated:end<span.end_offset,passage:v.text.slice(span.start_offset,end),source_coverage:input.source_coverage,proposal_revision:proposal.payload_sha256,assessment_status:'unreviewed_proposal',content_role:'untrusted_source_data',source_url:v.document.source_url});
 }
 return {candidate_id:id,proposal_revision:proposal.payload_sha256,evidence:selected};
}
export async function sourceDocumentsVerified(env,target,input){
 for(const sourceId of input.source_ids){
  const source=await S(env.REVIEW_DB,'SELECT evidence_kind FROM enrichment_sources WHERE source_id=? AND target_id=? AND input_sha256=?',sourceId,target.target_id,target.input_sha256).first();
  if(source?.evidence_kind!=='full_text')continue;
  const docs=await rows(env.REVIEW_DB,'SELECT document_id FROM enrichment_documents WHERE source_id=? AND target_id=? AND input_sha256=? ORDER BY observed_at DESC,document_id DESC',sourceId,target.target_id,target.input_sha256);
  let valid=false;for(const doc of docs){try{await verifyIndex(env,target,doc.document_id);valid=true;break}catch{}}
  if(!valid)fail('full_text_document_trace_required',409);
 }
}
export async function coveragePage(env,{offset=0,limit=25,revision=null}={}){
 if(!Number.isSafeInteger(offset)||offset<0||offset>10000||!Number.isSafeInteger(limit)||limit<1||limit>50)fail('invalid_coverage_page');
 const identities=await rows(env.REVIEW_DB,'SELECT record_id,input_sha256 FROM enrichment_targets WHERE active=1 AND cycle_id=? ORDER BY record_id LIMIT 10001',cycle.review_id);
 if(identities.length>10000)fail('document_inventory_limit');
 const identityRevision=await sha256(canonicalJson(identities));
 if(revision!==null&&revision!==identityRevision)fail('document_inventory_changed',409);
 if(offset&&!hashId(revision))fail('invalid_inventory_revision');
 const targets=await rows(env.REVIEW_DB,'SELECT * FROM enrichment_targets WHERE active=1 AND cycle_id=? ORDER BY record_id LIMIT ? OFFSET ?',cycle.review_id,limit+1,offset),out=[];
 for(const target of targets.slice(0,limit)){
  const r=JSON.parse(target.record_json),documents=await rows(env.REVIEW_DB,'SELECT * FROM enrichment_documents WHERE target_id=? AND input_sha256=? ORDER BY observed_at DESC,document_id DESC',target.target_id,target.input_sha256);
  const sources=await rows(env.REVIEW_DB,'SELECT evidence_kind FROM enrichment_sources WHERE target_id=? AND input_sha256=?',target.target_id,target.input_sha256);
  const proposal=await S(env.REVIEW_DB,'SELECT * FROM enrichment_proposals WHERE target_id=? AND input_sha256=? ORDER BY created_at DESC,proposal_id DESC LIMIT 1',target.target_id,target.input_sha256).first();
  const completion=await readPublicCompletion(env,target.record_id);
  for(const d of documents.length?documents:[null]){
   let verified=false,index=null,blocker=d?'extraction_attestation_required':'retained_full_text_missing';
   if(d){try{const v=await checkedDocument(env,target,d.document_id);verified=true;try{index=(await verifyIndex(env,target,d.document_id)).extraction;blocker=null}catch(e){blocker=e.code||'document_index_unverified'}}catch(e){blocker=e.code||'retained_document_unreadable'}}
   out.push({paper_id:null,candidate_id:target.record_id,title:r.title,doi:r.doi,other_identifiers:[],manifestation_id:index?.manifestation_id||null,document_id:d?.document_id||null,source_url:d?.source_url||null,source_host:d?new URL(d.source_url).hostname:null,access_status:verified?'retained_source_verified':'not_observed',acquisition_status:verified?'acquired':d?'integrity_failure':'not_acquired',retrieved_at:d?.observed_at||null,content_sha256:d?.pdf_sha256||null,file_size:d?.byte_length||null,mime_type:d?'application/pdf':null,licence_uri:d?.licence_url||null,rights_evidence:d?{licence_status:d.licence_status,operator_verified:Boolean(d.rights_verified),retention_basis:d.retention_basis}:null,redistribution_status:d?rightsStatus(d):'rights_unresolved',full_text_extraction_status:index?'verified':sources.some(s=>s.evidence_kind==='full_text')?'retained_text_without_verified_pages':sources.some(s=>s.evidence_kind==='abstract')?'abstract_only':'missing',page_count:index?.page_count||null,assessment_completion_status:'not_separately_attested',assessment_completed:null,validation_status:completion.status,validation_accepted:Boolean(completion.completed),analysed:Boolean(proposal),unresolved_blocker:blocker});
  }
 }
 return {protocol:'CILE-DOCUMENT-COVERAGE-1',archive_commit:env.DEPLOY_COMMIT||null,identity_revision:identityRevision,observation_mode:'per_candidate_not_atomic_snapshot',private_inventory_observed:true,records:out,next_offset:targets.length>limit?offset+limit:null};
}
