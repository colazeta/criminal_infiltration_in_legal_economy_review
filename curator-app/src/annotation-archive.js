/* Governed ingress, not scientific extraction. Original snapshots remain private;
   candidate-bound reading annotations retain their unreviewed status. */
import contract from '../../ontology/modules/annotation-archive.json' with {type:'json'};
import cycle from '../../config/archive-cycle.json' with {type:'json'};
import {canonicalJson,sha256} from './review-v2.js';
import {safeResearchUrl} from './public-paper-research.js';

export const ANNOTATION_VERSION='CILE-ANNOTATION-ARCHIVE-1';
const REPO='https://github.com/colazeta/criminal_infiltration_in_legal_economy_review';
const S=(db,sql,...args)=>db.prepare(sql).bind(...args);
const rows=async(db,sql,...args)=>(await S(db,sql,...args).all()).results;
const fail=()=>{throw Error('annotation_archive_invalid')};
const idPattern=/^CAND-[A-Za-z0-9-]{1,100}$/;
const CLASSES=['aetiology','diagnosis','screening','therapy','prognosis','prevention'];
const iso=now=>new Date(now).toISOString();
const text=value=>String(value||'').replace(/<!--.*?-->/g,'').replace(/<[^>]*>/g,'').replace(/\[([^\]]+)\]\((https:\/\/[^)]+)\)/g,'$1').replace(/[`*]/g,'').replace(/^\s*(?:[-+]\s+|\d+\.\s+)/,'').trim();
const unsafe=value=>/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/u.test(value)||/\b(sk-(?:proj-)?[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._-]{12,}|-----BEGIN .*PRIVATE KEY-----|source_id|input_sha256|private (?:source|note)|internal note|reviewer (?:name|identity))\b/i.test(value)||/@[A-Za-z0-9_][A-Za-z0-9_-]{2,}/.test(value)||(value.match(/https?:\/\/[^\s<>"']+/g)||[]).some(url=>!safeResearchUrl(url));

function markers(body,kind){
 const re=kind==='issue'?/<!--\s*curator-candidate:([^>]+)\s*-->/gi:/<!--\s*manual-scientific-enrichment:[^>]*:(CAND-[A-Za-z0-9-]{1,100})\s*-->/gi;
 return [...new Set([...String(body||'').matchAll(re)].map(m=>m[1].trim()))];
}
export function parseAnnotation(body){
 const sections=[],classes=[];let current=null,unparsed=0,inCode=false;
 for(const raw of String(body||'').split('\n')){
  if(/^\s*```/.test(raw)){inCode=!inCode;unparsed++;continue}if(inCode){if(raw.trim())unparsed++;continue}
  const heading=raw.match(/^#{2,5}\s+(.+?)\s*$/);
  if(heading){
   const label=text(heading[1]);let scope=null,group='';
   if(/^top[- ]level scientific fields$|^scientific fields$/i.test(label))scope='overview';
   else if(/^clinical-contribution framework\b/i.test(label))scope='framework';
   else if(/^Study\s+([A-Za-z0-9_-]+)(?:\s|$)/i.test(label)){scope='studies';group=label.match(/^Study\s+([A-Za-z0-9_-]+)/i)[1]}
   else if(/^Analysis\s+([A-Za-z0-9_-]+)(?:\s|$)/i.test(label)){scope='methods';group=label.match(/^Analysis\s+([A-Za-z0-9_-]+)/i)[1]}
   else if(/^Datasets?$/i.test(label))scope='datasets';
   else if(/^Key variable uses to encode$|^Variables?$/i.test(label))scope='variables';
   else if(/^Findings to encode$|^Findings$/i.test(label))scope='findings';
   else if(/^(?:Primary (?:scientific )?sources consulted|Sources consulted|Sources,|Source\/version QA|Source and version QA)/i.test(label))scope='sources';
   current=scope?{scope,group_label:group,fields:[]}:null;if(current)sections.push(current);continue;
  }
  if(!raw.trim()||/^\s*<!--/.test(raw))continue;
  if(!current){unparsed++;continue}
  if(current.scope==='sources'){
   const urls=[...new Set(raw.match(/https:\/\/[^\s<>"')]+/g)||[])];
   for(const url of urls)if(safeResearchUrl(url))current.fields.push({field_name:'source_url',value:url});else unparsed++;
   if(!urls.length)unparsed++;continue;
  }
  let value=text(raw);if(!value||unsafe(value)||value.length>12000||/^\s*[>|]/.test(raw)){unparsed++;continue}
  const keys=contract.field_names[current.scope];let field;
  if(keys.includes('annotation_text'))field={field_name:'annotation_text',value};
  else{
   const parsed=value.match(/^([a-z_]+)(?:\s+[—–-]\s+[^:]+)?:\s*(.+)$/i);
   if(!parsed||!keys.includes(parsed[1].toLowerCase())){unparsed++;continue}
   field={field_name:parsed[1].toLowerCase(),value:parsed[2].trim()};
  }
  current.fields.push(field);
  if(current.scope==='framework'&&['primary','secondary','alternative'].includes(field.field_name)){
   // Only an entire explicit list is a class assertion. Rationale mentions and
   // ambiguous free text never silently become a primary/secondary decision.
   const values=field.value.toLowerCase().split(/\s*[,;+]\s*/);
   if(values.length&&values.every(c=>CLASSES.includes(c)))for(const category of new Set(values))classes.push({section:sections.length-1,field:current.fields.length-1,category,role:field.field_name});
  }
 }
 return {sections,classes,unparsed_lines:unparsed};
}

function validateCapture(input){
 if(!input||Object.keys(input).sort().join(',')!=='action,comment,issue'||!['observe','withdraw'].includes(input.action))fail();
 for(const [kind,entity]of [['issue',input.issue],['comment',input.comment]]){
  if(!entity||Object.keys(entity).some(k=>!['id','number','body','created_at','updated_at','html_url','actor','is_pull_request'].includes(k))||!Number.isSafeInteger(entity.id)||entity.id<=0||(entity.body!==null&&typeof entity.body!=='string')||(entity.body?.length||0)>200000||!Number.isFinite(Date.parse(entity.created_at))||!Number.isFinite(Date.parse(entity.updated_at))||Date.parse(entity.updated_at)<Date.parse(entity.created_at))fail();
  if(entity.actor!==null&&(typeof entity.actor!=='string'||entity.actor.length>100))fail();
  if(kind==='issue'&&Object.hasOwn(entity,'is_pull_request')&&typeof entity.is_pull_request!=='boolean'||kind==='comment'&&Object.hasOwn(entity,'is_pull_request'))fail();
  const route=input.issue.is_pull_request?'pull':'issues';
  const url=kind==='issue'?`${REPO}/${route}/${entity.number}`:`${REPO}/${route}/${input.issue.number}#issuecomment-${entity.id}`;
  if(entity.html_url!==url||kind==='issue'&&(!Number.isSafeInteger(entity.number)||entity.number<1)||kind==='comment'&&Object.hasOwn(entity,'number'))fail();
 }
}

async function capture(env,kind,entity,now){
 const encoded=canonicalJson(entity),hash=await sha256(encoded),id=await sha256(canonicalJson([kind,String(entity.id),hash])),key='ingress/'+id;
 const prior=await S(env.REVIEW_DB,'SELECT * FROM enrichment_ingress_snapshots WHERE snapshot_id=?',id).first();
 if(!prior)await env.REVIEW_EVIDENCE.put(key,encoded);const object=await env.REVIEW_EVIDENCE.get(key);
 if(!object||await sha256(await object.text())!==hash)fail();
 if(prior){if(prior.content_sha256!==hash||prior.external_id!==String(entity.id)||prior.storage_key!==key)fail();return prior}
 await S(env.REVIEW_DB,'INSERT OR IGNORE INTO enrichment_ingress_snapshots VALUES (?,?,?,?,?,?,?,?,?)',id,'github_'+kind,String(entity.id),entity.html_url,entity.created_at,entity.updated_at,hash,key,iso(now)).run();
 const row=await S(env.REVIEW_DB,'SELECT * FROM enrichment_ingress_snapshots WHERE snapshot_id=?',id).first();
 if(!row||row.content_sha256!==hash||row.external_id!==String(entity.id))fail();return row;
}

const graphStatements=(db,id)=>[
 S(db,'SELECT section_id,scope,group_label,position FROM enrichment_annotation_sections WHERE annotation_id=? ORDER BY position',id),
 S(db,'SELECT f.* FROM enrichment_annotation_fields f JOIN enrichment_annotation_sections s USING(section_id) WHERE s.annotation_id=? ORDER BY s.position,f.position',id),
 S(db,'SELECT c.* FROM enrichment_annotation_classes c JOIN enrichment_annotation_fields f USING(field_id) JOIN enrichment_annotation_sections s ON s.section_id=f.section_id WHERE c.annotation_id=? ORDER BY s.position,f.position,c.category',id),
 S(db,'SELECT unparsed_lines FROM enrichment_manual_annotations WHERE annotation_id=?',id),
];
function rebuild(results){
 const [sections,fields,classes,annotation]=results.map(r=>r.results);if(annotation.length!==1)fail();
 const out={sections:sections.map(s=>({scope:s.scope,group_label:s.group_label,fields:fields.filter(f=>f.section_id===s.section_id).map(f=>({field_name:f.field_name,value:f.value}))})),classes:[],unparsed_lines:annotation[0].unparsed_lines};
 for(const c of classes){const section=sections.findIndex(s=>s.section_id===fields.find(f=>f.field_id===c.field_id)?.section_id);if(section<0)fail();const field=fields.filter(f=>f.section_id===sections[section].section_id).findIndex(f=>f.field_id===c.field_id);out.classes.push({section,field,category:c.category,role:c.role})}
 return out;
}
function stableGraph(parsed){return {...parsed,classes:[...parsed.classes].sort((a,b)=>a.section-b.section||a.field-b.field||a.category.localeCompare(b.category))}}
export async function readAnnotationGraph(db,id){
 const receipt=await S(db,'SELECT * FROM enrichment_annotation_receipts WHERE annotation_id=?',id).first();if(!receipt)fail();
 const result=[];for(const stmt of graphStatements(db,id))result.push(await stmt.all());const graph=rebuild(result);
 if(await sha256(canonicalJson(graph))!==receipt.parsed_sha256||receipt.rebuilt_sha256!==receipt.parsed_sha256)fail();return graph;
}

async function transition(db,annotation,source,action,now){
 const external=source.external_id,prior=await S(db,'SELECT h.*,s.source_updated_at FROM enrichment_annotation_heads h JOIN enrichment_manual_annotations a USING(annotation_id) JOIN enrichment_ingress_snapshots s ON s.snapshot_id=a.snapshot_id WHERE h.external_id=?',external).first();
 let state='current',kind=prior?'revision':'import',selected=annotation.annotation_id;
 if(action==='withdraw'){state='withdrawn';kind='withdrawal'}
 else if(prior?.state==='withdrawn'){state='withdrawn';kind='retained_after_withdrawal';selected=prior.annotation_id}
 else if(prior?.state==='conflict'&&Date.parse(source.source_updated_at)<=Date.parse(prior.source_updated_at)){state='conflict';kind='conflict';selected=prior.annotation_id}
 else if(prior&&Date.parse(source.source_updated_at)<Date.parse(prior.source_updated_at)){state=prior.state;kind='older_revision';selected=prior.annotation_id}
 else if(prior&&source.source_updated_at===prior.source_updated_at&&prior.annotation_id!==annotation.annotation_id){state='conflict';kind='conflict';selected=prior.annotation_id}
 else if(prior?.annotation_id===annotation.annotation_id&&prior.state==='current')return {statements:[],head:prior,replayed:true};
 if(prior?.state==='withdrawn'&&action==='withdraw')return {statements:[],head:prior,replayed:true};
 const event=await sha256(canonicalJson([external,annotation.annotation_id,prior?.annotation_id||null,kind]));
 if(await S(db,'SELECT event_id FROM enrichment_annotation_events WHERE event_id=?',event).first())return {statements:[],head:prior,replayed:true};
 const head={external_id:external,annotation_id:selected,state,record_version:(prior?.record_version||0)+1,updated_at:iso(now)};
 const statements=[S(db,'INSERT OR IGNORE INTO enrichment_annotation_events VALUES (?,?,?,?,?,?)',event,external,annotation.annotation_id,prior?.annotation_id||null,kind,iso(now))];
 statements.push(prior?S(db,'UPDATE enrichment_annotation_heads SET annotation_id=?,state=?,record_version=?,updated_at=? WHERE external_id=? AND record_version=?',selected,state,head.record_version,head.updated_at,external,prior.record_version):S(db,'INSERT INTO enrichment_annotation_heads VALUES (?,?,?,?,?)',external,selected,state,1,head.updated_at));
 return {statements,head,replayed:false};
}

export async function ingestAnnotation(env,input,now=Date.now()){
 validateCapture(input);const db=env.REVIEW_DB;
 const issue=await capture(env,'issue',input.issue,now),source=await capture(env,'comment',input.comment,now);
 const known=await S(db,'SELECT annotation_id FROM enrichment_annotation_heads WHERE external_id=?',source.external_id).first();
 const recognized=!input.issue.is_pull_request&&(!!known||/manual-scientific-enrichment:|^#{2,5}\s+(?:manual scientific|scientific reading-support|source-based scientific pre-extraction|catalogue-grounded scientific pre-extraction)/im.test(input.comment.body||''));
 if(!recognized)return {contract:ANNOTATION_VERSION,captured:true,annotation:false,snapshot_id:source.snapshot_id};
 const a=markers(input.issue.body,'issue'),b=markers(input.comment.body,'comment');let binding='unresolved',candidate=b.length===1?b[0]:null,target=null;
 if(a.length===1&&b.length===1&&a[0]===b[0]&&idPattern.test(b[0])){
  target=await S(db,'SELECT target_id FROM enrichment_targets WHERE cycle_id=? AND record_namespace=\'candidate\' AND record_id=? AND active=1',cycle.review_id,b[0]).first();binding=target?'candidate_bound':'unregistered';
 }else if(a.length>1||b.length>1||a.length&&b.length&&a[0]!==b[0])binding='conflict';
 const id=await sha256(canonicalJson([source.snapshot_id,ANNOTATION_VERSION])),parsed=stableGraph(parseAnnotation(input.comment.body)),encoded=canonicalJson(parsed),parsedHash=await sha256(encoded);
 if(parsed.sections.length>100||parsed.sections.reduce((n,s)=>n+s.fields.length,0)>2000)fail();
 const annotation={annotation_id:id};
 for(let attempt=0;attempt<3;attempt++){
  const existing=await S(db,'SELECT r.*,a.binding_state FROM enrichment_annotation_receipts r JOIN enrichment_manual_annotations a USING(annotation_id) WHERE annotation_id=?',id).first();
  const change=await transition(db,annotation,source,input.action,now);
  if(existing){await readAnnotationGraph(db,id);if(!change.statements.length)return {contract:ANNOTATION_VERSION,captured:true,annotation:true,annotation_id:id,binding_state:existing.binding_state,replayed:true};}
  const writes=[];
  if(!existing){
   writes.push(S(db,'INSERT INTO enrichment_manual_annotations VALUES (?,?,?,?,?,?,?,?,?,?)',id,source.snapshot_id,issue.snapshot_id,target?.target_id||null,candidate,binding,'unreviewed_manual_support',input.comment.actor&&input.comment.actor===env.CURATOR_LOGIN?1:0,parsed.unparsed_lines,iso(now)));
   const fieldIds=[];
   for(const [index,section]of parsed.sections.entries()){
    const sectionId=await sha256(id+':section:'+index);fieldIds[index]=[];
    writes.push(S(db,'INSERT INTO enrichment_annotation_sections VALUES (?,?,?,?,?)',sectionId,id,section.scope,section.group_label,index+1));
    for(const [position,field]of section.fields.entries()){
     const fieldId=await sha256(sectionId+':field:'+position);fieldIds[index][position]=fieldId;
     writes.push(S(db,'INSERT INTO enrichment_annotation_fields VALUES (?,?,?,?,?)',fieldId,sectionId,field.field_name,field.value,position+1));
    }
   }
   for(const c of parsed.classes){const fieldId=fieldIds[c.section][c.field],assertion=await sha256(fieldId+c.role+c.category);writes.push(S(db,'INSERT INTO enrichment_annotation_classes VALUES (?,?,?,?,?)',assertion,id,fieldId,c.category,c.role))}
  }
  writes.push(...change.statements);const reads=[...graphStatements(db,id),S(db,'SELECT * FROM enrichment_annotation_heads WHERE external_id=?',source.external_id)];
  const receipt=existing?S(db,'SELECT 1'):S(db,'INSERT INTO enrichment_annotation_receipts VALUES (?,?,?,?,?,?,?)',await sha256(id+':receipt'),id,ANNOTATION_VERSION,source.content_sha256,parsedHash,parsedHash,iso(now));
  try{
   await db.batchValidated(writes,reads,result=>canonicalJson(rebuild(result.slice(0,4)))===encoded&&canonicalJson(result.at(-1).results[0])===canonicalJson(change.head),receipt);
   await readAnnotationGraph(db,id);
   return {contract:ANNOTATION_VERSION,captured:true,annotation:true,annotation_id:id,binding_state:existing?.binding_state||binding,replayed:!!existing,visibility:change.head.state};
  }catch(error){if(attempt===2)throw Error('annotation_transaction_failed')}
 }
}

export async function auditAnnotations(env){
 const db=env.REVIEW_DB,snapshots=await rows(db,'SELECT * FROM enrichment_ingress_snapshots');
 if(snapshots.length>30000)fail();
 for(const snapshot of snapshots){const object=await env.REVIEW_EVIDENCE.get(snapshot.storage_key);if(!object||await sha256(await object.text())!==snapshot.content_sha256)fail();}
 const annotations=await rows(db,'SELECT a.*,s.content_sha256,s.storage_key FROM enrichment_manual_annotations a JOIN enrichment_ingress_snapshots s USING(snapshot_id)');
 const bindings={candidate_bound:0,unresolved:0,conflict:0,unregistered:0};
 for(const a of annotations){
  const receipt=await S(db,'SELECT source_sha256 FROM enrichment_annotation_receipts WHERE annotation_id=?',a.annotation_id).first();if(receipt?.source_sha256!==a.content_sha256)fail();
  const graph=await readAnnotationGraph(db,a.annotation_id),original=JSON.parse(await(await env.REVIEW_EVIDENCE.get(a.storage_key)).text());
  if(canonicalJson(graph)!==canonicalJson(stableGraph(parseAnnotation(original.body))))fail();bindings[a.binding_state]++;
 }
 return {snapshots:snapshots.length,annotations:annotations.length,binding_states:bindings,integrity_verified:true};
}

export async function reconcileAnnotationCensus(env,census,now=Date.now()){
 if(!census||Object.keys(census).sort().join(',')!=='comment_ids,observed_before,source_sha256'||!Number.isFinite(Date.parse(census.observed_before))||Date.parse(census.observed_before)>now||!Array.isArray(census.comment_ids)||census.comment_ids.length>30000||!census.comment_ids.every(id=>Number.isSafeInteger(id)&&id>0)||new Set(census.comment_ids).size!==census.comment_ids.length||!/^[a-f0-9]{64}$/.test(census.source_sha256||''))fail();
 const present=new Set(census.comment_ids.map(String)),db=env.REVIEW_DB;let withdrawn=0,deferred=0;
 for(const head of await rows(db,"SELECT * FROM enrichment_annotation_heads WHERE state<>'withdrawn'")){
  if(present.has(head.external_id))continue;
  if(Date.parse(head.updated_at)>Date.parse(census.observed_before)){deferred++;continue}
  const eventId=await sha256(canonicalJson(['complete_github_census',census.source_sha256,head.external_id]));
  await db.batchValidated([
   S(db,'INSERT INTO enrichment_annotation_events VALUES (?,?,?,?,?,?)',eventId,head.external_id,head.annotation_id,head.annotation_id,'withdrawal',iso(now)),
   S(db,"UPDATE enrichment_annotation_heads SET state='withdrawn',record_version=record_version+1,updated_at=? WHERE external_id=? AND record_version=?",iso(now),head.external_id,head.record_version),
  ],[S(db,'SELECT state,record_version FROM enrichment_annotation_heads WHERE external_id=?',head.external_id)],r=>r[0].results[0]?.state==='withdrawn'&&r[0].results[0]?.record_version===head.record_version+1,S(db,'SELECT 1'));
  withdrawn++;
 }
 return {contract:ANNOTATION_VERSION,observed_comments:present.size,withdrawn,deferred,source_sha256:census.source_sha256,history_deleted:false};
}

function redactCredentialText(value){
 let redactions=0;
 const replace=(pattern,label)=>{value=value.replace(pattern,()=>{redactions++;return '[REDACTED_'+label+']'});};
 replace(/sk-(?:proj-)?[A-Za-z0-9_-]{20,}/g,'OPENAI_KEY');
 replace(/gh[pousr]_[A-Za-z0-9]{20,}/g,'GITHUB_TOKEN');
 replace(/Bearer\\s+[A-Za-z0-9._-]{12,}/gi,'BEARER_TOKEN');
 replace(/-----BEGIN [^-]{1,40}PRIVATE KEY-----[\\s\\S]*?-----END [^-]{1,40}PRIVATE KEY-----/g,'PRIVATE_KEY');
 return {value,redactions};
}
async function verifiedSnapshot(env,snapshotId){
 const snapshot=await S(env.REVIEW_DB,'SELECT * FROM enrichment_ingress_snapshots WHERE snapshot_id=?',snapshotId).first();if(!snapshot)fail();
 const object=await env.REVIEW_EVIDENCE.get(snapshot.storage_key);if(!object)fail();
 const raw=await object.text();if(await sha256(raw)!==snapshot.content_sha256)fail();
 let parsed;try{parsed=JSON.parse(raw)}catch{fail()}
 const body=redactCredentialText(String(parsed.body||''));
 return {snapshot:{...snapshot},entity:{...parsed,body:body.value},redactions_applied:body.redactions};
}
export async function listPrivateAnnotations(env,targetId){
 if(typeof targetId!=='string'||!/^[a-f0-9]{64}$/.test(targetId))fail();
 const all=await rows(env.REVIEW_DB,`SELECT a.*,s.source_url,s.source_created_at,s.source_updated_at,s.content_sha256,h.state AS head_state,h.record_version,h.updated_at AS head_updated_at
   FROM enrichment_manual_annotations a
   JOIN enrichment_ingress_snapshots s ON s.snapshot_id=a.snapshot_id
   LEFT JOIN enrichment_annotation_heads h ON h.external_id=s.external_id
   WHERE a.target_id=?
   ORDER BY s.source_created_at,a.annotation_id`,targetId);
 if(all.length>200)fail();
 const annotations=[];
 for(const row of all){
   const receipt=await S(env.REVIEW_DB,'SELECT * FROM enrichment_annotation_receipts WHERE annotation_id=?',row.annotation_id).first();if(!receipt)fail();
   const graph=await readAnnotationGraph(env.REVIEW_DB,row.annotation_id);
   const events=await rows(env.REVIEW_DB,'SELECT * FROM enrichment_annotation_events WHERE external_id=(SELECT external_id FROM enrichment_ingress_snapshots WHERE snapshot_id=?) ORDER BY observed_at,event_id',row.snapshot_id);
   annotations.push({...row,receipt,graph,events});
 }
 return {contract:ANNOTATION_VERSION,target_id:targetId,annotations};
}
async function privateAnnotationDetail(env,annotation){
 const source=await verifiedSnapshot(env,annotation.snapshot_id),issue=await verifiedSnapshot(env,annotation.issue_snapshot_id);
 const receipt=await S(env.REVIEW_DB,'SELECT * FROM enrichment_annotation_receipts WHERE annotation_id=?',annotation.annotation_id).first();if(!receipt)fail();
 const graph=await readAnnotationGraph(env.REVIEW_DB,annotation.annotation_id);
 const external=source.snapshot.external_id;
 const head=await S(env.REVIEW_DB,'SELECT * FROM enrichment_annotation_heads WHERE external_id=?',external).first();
 const events=await rows(env.REVIEW_DB,'SELECT * FROM enrichment_annotation_events WHERE external_id=? ORDER BY observed_at,event_id',external);
 return {contract:ANNOTATION_VERSION,target_id:annotation.target_id||null,annotation,source,issue,head,receipt,graph,events,
   transparency_note:'Credential-shaped strings are redacted from displayed source bodies; hashes and immutable receipts remain available for audit.'};
}
export async function listPrivateAnnotationArchive(env){
 const all=await rows(env.REVIEW_DB,`SELECT a.annotation_id,a.target_id,a.snapshot_id,a.issue_snapshot_id,a.binding_state,a.review_state,a.authorised_display,a.unparsed_lines,a.imported_at,
   s.source_url,s.source_created_at,s.source_updated_at,s.content_sha256,h.state AS head_state,h.record_version,h.updated_at AS head_updated_at,
   t.record_id AS candidate_id
   FROM enrichment_manual_annotations a
   JOIN enrichment_ingress_snapshots s ON s.snapshot_id=a.snapshot_id
   LEFT JOIN enrichment_annotation_heads h ON h.external_id=s.external_id
   LEFT JOIN enrichment_targets t ON t.target_id=a.target_id
   ORDER BY s.source_created_at,a.annotation_id`);
 if(all.length>1000)fail();
 const counts={candidate_bound:0,unresolved:0,conflict:0,unregistered:0};
 for(const row of all){if(Object.hasOwn(counts,row.binding_state))counts[row.binding_state]++}
 return {contract:ANNOTATION_VERSION,total:all.length,counts,annotations:all};
}
export async function readPrivateAnnotationById(env,annotationId){
 if(typeof annotationId!=='string'||!/^[a-f0-9]{64}$/.test(annotationId))fail();
 const annotation=await S(env.REVIEW_DB,'SELECT * FROM enrichment_manual_annotations WHERE annotation_id=?',annotationId).first();if(!annotation)fail();
 return privateAnnotationDetail(env,annotation);
}
export async function readPrivateAnnotation(env,targetId,annotationId){
 if(typeof targetId!=='string'||!/^[a-f0-9]{64}$/.test(targetId)||typeof annotationId!=='string'||!/^[a-f0-9]{64}$/.test(annotationId))fail();
 const annotation=await S(env.REVIEW_DB,'SELECT * FROM enrichment_manual_annotations WHERE annotation_id=? AND target_id=?',annotationId,targetId).first();if(!annotation)fail();
 return privateAnnotationDetail(env,annotation);
}

export async function readPublicAnnotations(env,candidateId){
 if(!idPattern.test(candidateId))fail();
 const db=env.REVIEW_DB,all=await rows(db,`SELECT a.annotation_id,h.state,s.source_url,s.source_updated_at,s.storage_key,s.content_sha256 FROM enrichment_manual_annotations a JOIN enrichment_annotation_heads h USING(annotation_id) JOIN enrichment_ingress_snapshots s ON s.snapshot_id=a.snapshot_id JOIN enrichment_targets t ON t.target_id=a.target_id WHERE t.record_id=? AND t.cycle_id=? AND t.active=1 AND a.binding_state='candidate_bound' AND a.authorised_display=1 ORDER BY s.source_created_at,a.annotation_id`,candidateId,cycle.review_id);
 if(all.length>100)fail();
 const annotations=[];let conflicts=0;
 for(const row of all){if(row.state==='conflict'){conflicts++;continue}if(row.state!=='current')continue;
  const original=await env.REVIEW_EVIDENCE.get(row.storage_key);if(!original||await sha256(await original.text())!==row.content_sha256)fail();
  const graph=await readAnnotationGraph(db,row.annotation_id);for(const section of graph.sections)for(const field of section.fields)if(unsafe(field.value))fail();
  annotations.push({annotation_id:row.annotation_id,assessment_state:'unreviewed_manual_support',source_url:row.source_url,updated_at:row.source_updated_at,sections:graph.sections,classes:graph.classes.map(({category,role})=>({category,role})),unparsed_lines:graph.unparsed_lines});
 }
 const out={schema_version:1,projection_version:'CILE-PUBLIC-ANNOTATIONS-1',candidate_id:candidateId,annotations,conflicts};out.revision=await sha256(canonicalJson(out));return out;
}
