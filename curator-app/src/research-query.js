/* Shared read service for the document library and MCP. No write or fetch capability. */
import {currentTarget,documentLibrary,searchFullText,resolveEvidence,documentError,validRecordId} from './document-repository.js';
import {readPublicResearch,readPublicCompletion} from './public-paper-research.js';
import {readNormalizedExtraction} from './extraction-relations.js';
import cycle from '../../config/archive-cycle.json' with {type:'json'};
import {sha256,canonicalJson} from './review-v2.js';
import {sourceContents,validateExtraction} from './paper-enrichment.js';

const S=(db,sql,...v)=>db.prepare(sql).bind(...v);
const rows=async(db,sql,...v)=>(await S(db,sql,...v).all()).results;
export const REVIEW_FIELDS=['summary','contribution','research_question','infiltration_definition','infiltration_operationalisation','studies','datasets','analyses','variable_uses','findings','authors_limitations','framework'];
const literal=s=>'%'+s.replace(/[\\%_]/g,'\\$&')+'%';
export async function searchPapers(env,args={},access={publicOnly:true}){
 const limit=args.limit??20;if(!Number.isSafeInteger(limit)||limit<1||limit>25)documentError('invalid_limit');
 if(args.cursor!==undefined&&args.cursor!==null&&!validRecordId(args.cursor))documentError('invalid_cursor');
 const where=['t.active=1','t.cycle_id=?'],values=[cycle.review_id];
 if(args.cursor){where.push('t.record_id>?');values.push(args.cursor)}
 if(args.query){where.push("(json_extract(t.record_json,'$.title') LIKE ? ESCAPE '\\' OR json_extract(t.record_json,'$.doi') LIKE ? ESCAPE '\\')");values.push(literal(args.query),literal(args.query))}
 if(args.author){where.push("b.authors LIKE ? ESCAPE '\\'");values.push(literal(args.author))}
 if(args.year_from!==undefined){where.push('b.publication_year>=?');values.push(args.year_from)}
 if(args.year_to!==undefined){where.push('b.publication_year<=?');values.push(args.year_to)}
 if(args.review_status){where.push('b.review_status=?');values.push(args.review_status)}
 const dimensions={geography:['studies','geography'],method:['analyses','method'],dataset:['datasets','name'],variable:['variable_uses','concept']};
 for(const [key,[scope,field]] of Object.entries(dimensions))if(!access.publicOnly&&args[key]){
  where.push("EXISTS (SELECT 1 FROM enrichment_facts f WHERE f.proposal_id=p.proposal_id AND f.scope=? AND f.field_name=? AND f.status='reported' AND f.value LIKE ? ESCAPE '\\')");values.push(scope,field,literal(args[key]));
 }
 if(!access.publicOnly&&args.framework_category){where.push("EXISTS (SELECT 1 FROM enrichment_framework_proposals f WHERE f.proposal_id=p.proposal_id AND f.classification_status='proposed' AND f.primary_category=?)");values.push(args.framework_category)}
 if(!access.publicOnly&&args.source_coverage){where.push('EXISTS (SELECT 1 FROM enrichment_proposal_details pd WHERE pd.proposal_id=p.proposal_id AND pd.source_coverage=?)');values.push(args.source_coverage)}
 const list=await rows(env.REVIEW_DB,`SELECT t.*,b.authors,b.publication_year,b.venue,b.review_status FROM enrichment_targets t LEFT JOIN enrichment_catalogue_index b ON b.target_id=t.target_id AND b.input_sha256=t.input_sha256 LEFT JOIN enrichment_proposals p ON p.proposal_id=(SELECT proposal_id FROM enrichment_proposals WHERE target_id=t.target_id AND input_sha256=t.input_sha256 ORDER BY created_at DESC,proposal_id DESC LIMIT 1) WHERE ${where.join(' AND ')} ORDER BY t.record_id LIMIT ?`,...values,limit+1);
 const structured=Object.keys(dimensions).some(k=>args[k])||args.framework_category||args.source_coverage;
 const result=[];
 for(const t of list.slice(0,limit)){
  const r=JSON.parse(t.record_json);
  if(access.publicOnly&&structured){
   // Scan a bounded bibliographic page and filter ONLY the public projection.
   // Neither the continuation cursor nor a withheld-results flag may reveal
   // that a private/unpublishable assessment matched a user's guessed filter.
   const projected=await readPublicResearch(env,t.record_id);if(projected.availability!=='available')continue;
   const research=projected.research;
   if(Object.entries(dimensions).some(([key,[scope,field]])=>args[key]&&!(research[scope]||[]).some(item=>item[field]?.status==='reported'&&item[field].value.toLowerCase().includes(args[key].toLowerCase()))))continue;
   if(args.framework_category&&(research.framework?.status!=='proposed'||research.framework.primary!==args.framework_category))continue;
   if(args.source_coverage&&research.source_coverage!==args.source_coverage)continue;
  }
  if(await sha256(canonicalJson(r))!==t.input_sha256)documentError('paper_identity_integrity',409);
  result.push({paper_id:null,candidate_id:t.record_id,identity_status:'candidate_only',title:r.title,doi:r.doi,authors:t.authors||null,year:t.publication_year||null,venue:t.venue||null,review_status:t.review_status||null,input_revision:t.input_sha256});
 }
 return {records:result,next_cursor:list.length>limit?list[limit-1].record_id:null,limit,archive_commit:env.DEPLOY_COMMIT||null,metadata_basis:'existing_register_sync_projection'};
}
export async function getReviewData(env,args,access={publicOnly:true}){
 const fields=args.fields||REVIEW_FIELDS;
 if(!Array.isArray(fields)||!fields.length||fields.length>12||fields.some(f=>!REVIEW_FIELDS.includes(f))||new Set(fields).size!==fields.length)documentError('invalid_review_fields');
 const target=await currentTarget(env,args.paper_id);
 let research,revision,spans,sources;
 if(access.publicOnly){
  const p=await readPublicResearch(env,args.paper_id);
  if(p.availability!=='available')return {paper_id:null,candidate_id:args.paper_id,availability:p.availability,data:null};
  research=p.research;revision=p.revision;spans=research.spans;sources=research.sources;
 }else{
  const p=await S(env.REVIEW_DB,'SELECT * FROM enrichment_proposals WHERE target_id=? AND input_sha256=? ORDER BY created_at DESC,proposal_id DESC LIMIT 1',target.target_id,target.input_sha256).first();
  if(!p)return {paper_id:null,candidate_id:args.paper_id,availability:'not_assessed',data:null};
  research=await readNormalizedExtraction(env.REVIEW_DB,p);revision=p.payload_sha256;spans=research.spans;
  const retained=await sourceContents(env,target,research.source_ids);
  if(retained.reduce((n,s)=>n+s.text.length,0)>8000000)documentError('document_source_limit');
  validateExtraction(research,target,retained);
  sources=retained.map(({source_id,source_url,evidence_kind,version_label})=>({source_id,source_url,evidence_kind,version_label}));
 }
 const offset=args.offset??0,limit=args.limit??10;
 if(!Number.isSafeInteger(offset)||offset<0||offset>1000||!Number.isSafeInteger(limit)||limit<1||limit>20)documentError('invalid_review_page');
 if(offset&&args.revision!==revision)documentError('review_revision_changed',409);
 const data={},pagination={};
 for(const field of fields){const value=research[field];if(Array.isArray(value)){data[field]=value.slice(offset,offset+limit);pagination[field]={total:value.length,next_offset:offset+limit<value.length?offset+limit:null}}else data[field]=value??null}
 const used=new Set();function collect(value){if(!value||typeof value!=='object')return;for(const id of value.evidence_span_ids||[])used.add(id);for(const v of Object.values(value))if(v&&typeof v==='object')collect(v)}collect(data);
 const completion=await readPublicCompletion(env,args.paper_id);
 return {paper_id:null,candidate_id:args.paper_id,availability:'available',revision,source_coverage:research.source_coverage,assessment_status:'unreviewed_proposal',validation_status:completion.status,assessment_completed:null,data,pagination,evidence_spans:spans.filter(s=>used.has(s.id)),sources,content_role:'untrusted_research_data'};
}
export async function corpusStats(env,{publicOnly=true}={}){
 const count=async(sql,...v)=>Number((await S(env.REVIEW_DB,sql,...v).first())?.n||0);
 const registered=await count('SELECT COUNT(*) n FROM enrichment_targets WHERE active=1 AND cycle_id=?',cycle.review_id);
 const indexed=await count('SELECT COUNT(DISTINCT d.target_id) n FROM enrichment_documents d JOIN enrichment_document_extractions x ON x.document_id=d.document_id JOIN enrichment_targets t ON t.target_id=d.target_id AND t.input_sha256=d.input_sha256 WHERE t.active=1 AND t.cycle_id=?',cycle.review_id);
 const acquired=await count('SELECT COUNT(DISTINCT d.target_id) n FROM enrichment_documents d JOIN enrichment_targets t ON t.target_id=d.target_id AND t.input_sha256=d.input_sha256 WHERE t.active=1 AND t.cycle_id=?',cycle.review_id);
 const publicDocs=await count("SELECT COUNT(DISTINCT d.target_id) n FROM enrichment_documents d JOIN enrichment_targets t ON t.target_id=d.target_id AND t.input_sha256=d.input_sha256 WHERE t.active=1 AND t.cycle_id=? AND d.visibility='public' AND d.rights_verified=1 AND d.licence_url IN ('https://creativecommons.org/licenses/by/4.0/','https://creativecommons.org/licenses/by-sa/4.0/','https://creativecommons.org/publicdomain/zero/1.0/') AND NOT EXISTS(SELECT 1 FROM enrichment_documents n WHERE n.target_id=d.target_id AND n.input_sha256=d.input_sha256 AND n.pdf_sha256=d.pdf_sha256 AND (n.observed_at>d.observed_at OR (n.observed_at=d.observed_at AND n.document_id>d.document_id)))",cycle.review_id);
 return {registered,canonical_works:null,included:null,assessment_completed:null,full_text_verified:indexed,pdf_acquired:acquired,text_extracted:indexed,publicly_rehostable:publicDocs,private_only:null,rights_unresolved:null,full_text_missing:registered-acquired,scope:'current_enrichment_targets',count_basis:'retained_document_and_extraction_receipts',integrity_checked:'on_index_write_and_document_read; full private coverage audit required for live-byte census',canonical_scope_blocker:'canonical_registry_not_activated_in_enrichment_store',assessment_scope_blocker:'unattested assessment completion is not inferred from proposal fields',archive_commit:env.DEPLOY_COMMIT||null};
}
export async function queryResearch(env,name,args,access={publicOnly:true}){
 switch(name){
  case 'search_papers':return searchPapers(env,args,access);
  case 'get_paper':return {library:await documentLibrary(env,args.paper_id,access),review:await getReviewData(env,{paper_id:args.paper_id,fields:['summary','contribution','research_question','framework']},access)};
  case 'search_full_text':return searchFullText(env,args,access);
  case 'get_evidence':return resolveEvidence(env,args.paper_id,args.evidence_ids,{...access,expectedRevision:args.revision});
  case 'get_review_data':return getReviewData(env,args,access);
  case 'compare_papers':{
   const out=[];for(const id of args.paper_ids)out.push(await getReviewData(env,{paper_id:id,fields:args.fields,limit:5},access));
   return {papers:out,ranking:null,comparison_basis:'requested recorded dimensions only'};
  }
  case 'get_corpus_stats':return corpusStats(env,access);
  default:documentError('unknown_read_operation',404);
 }
}
