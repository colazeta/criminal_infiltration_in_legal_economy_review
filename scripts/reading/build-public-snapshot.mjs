/* Compile existing public content. No model, source-text retrieval or scientific write. */
import fs from 'node:fs/promises';
import path from 'node:path';
import vm from 'node:vm';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const REPO='colazeta/criminal_infiltration_in_legal_economy_review';
const API='https://criminal-infiltration-curator.colazeta-research.workers.dev/api/public-paper-research';
const OWNER='colazeta';
const HASH=value=>crypto.createHash('sha256').update(typeof value==='string'?value:canonical(value)).digest('hex');
const canonical=value=>JSON.stringify(ordered(value));
function ordered(v){return Array.isArray(v)?v.map(ordered):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,ordered(v[k])])):v;}
const assert=(condition,code)=>{if(!condition)throw Error(code);};
const plain=value=>String(value||'').replace(/\[([^\]]+)\]\([^)]*\)/g,'$1').replace(/[`*]/g,'').trim();
const normal=value=>String(value||'').trim();
export function issueIdentity(issue,record){
  if(issue?.pull_request||!['colazeta','github-actions[bot]'].includes(issue?.user?.login))return false;
  const body=String(issue.body||'');
  const markers=[...body.matchAll(/<!--\s*curator-candidate:([^\s>]+)\s*-->/g)].map(m=>m[1]);
  if(markers.length!==1||markers[0]!==record.id)return false;
  const fields={};for(const line of body.split('\n')){const m=line.match(/^\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|$/);if(m)fields[m[1].trim()]=plain(m[2]);}
  for(const [key,column]of [['id','Candidate ID'],['title','Title'],['authors','Authors'],['year','Year'],['venue','Venue'],['doi','DOI']]){
    const v=fields[column]==='Not recorded'?'':fields[column];if(normal(v)!==normal(record[key]))return false;
  }
  const links=[...body.matchAll(/^- Source link \d+:\s*<(https:\/\/[^>]+)>/gm)].map(m=>m[1]).sort();
  return canonical(links)===canonical([...(record.sourceLinks||[])].sort());
}
const CLASSES=['aetiology','diagnosis','screening','therapy','prognosis','prevention'];
function roles(structured){
  const rows=structured.framework||[],keys=name=>rows.filter(r=>r[0]===name).map(r=>normal(r[1]).replace(/`/g,'').toLowerCase());
  const get=value=>CLASSES.find(k=>new RegExp('^'+k+'(?:$|[\\s(;,:—-])').test(value))||null;
  const primaries=[...new Set(keys('primary').map(get).filter(Boolean))];
  if(keys('status').some(s=>/outside_framework|insufficient_evidence/.test(s)))return {primary:null,secondary:[]};
  const primary=primaries.length===1?primaries[0]:null;
  const secondary=primary?[...new Set(keys('secondary').flatMap(s=>s.split(/;|,|\band\b/).map(x=>get(x.trim())).filter(k=>k&&k!==primary)))]:[];
  return {primary,secondary};
}
function safeManualText(value){
  if(typeof value==='string'){
    assert(!/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(value),'manual_control_text');
    assert(!/\b(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]{12,})|-----BEGIN .*PRIVATE KEY-----|\/api\/paper-enrichment|storage_key|input_sha256|analyst_limitations|source_text|reviewer_identity/i.test(value),'manual_publication_boundary');
  }else if(value&&typeof value==='object')for(const child of Object.values(value))safeManualText(child);
}
export function compileManual(comments,record,issue,parse){
  const marker=new RegExp('<!--\\s*manual-scientific-enrichment:[^>]*:'+record.id+'\\s*-->');
  const all=comments.filter(c=>marker.test(String(c.body||'')));
  if(!all.length)return {status:'absent',value:null};
  // The latest annotation is authoritative for this source; never resurrect an older rejected one.
  all.sort((a,b)=>String(a.updated_at).localeCompare(String(b.updated_at))||a.id-b.id);
  const latest=all.at(-1);
  if(latest.user?.login!==OWNER)return {status:'withheld',value:null};
  try{
    assert(Number.isSafeInteger(latest.id)&&Number.isFinite(Date.parse(latest.updated_at)),'manual_provenance');
    assert(latest.html_url===`https://github.com/${REPO}/issues/${issue.number}#issuecomment-${latest.id}`,'manual_comment_url');
    assert(String(latest.body).length<=100000,'manual_limit');
    // The already-authorised parser omits working notes. Also omit code/quotation blocks.
    let code=false;const cleaned=latest.body.split('\n').filter(line=>{
      if(/^\s*```/.test(line)){code=!code;return false;}return !code&&!/^\s*>/.test(line);
    }).join('\n');
    const output=parse({...latest,body:cleaned,_issue_number:issue.number},record.id,true);
    assert(output.sections.every(s=>s.items.length<100),'manual_truncation');
    assert(Object.values(output.structured).some(v=>v.length),'manual_no_public_fields');
    safeManualText(output.structured);
    // Only explicitly recorded primary/secondary roles are used by filters/statistics.
    // Keyword mentions, alternatives and analyst notes cannot create assignments.
    const role=roles(output.structured);
    const value={schema_version:1,assessment_state:'unreviewed_manual_support',candidate_id:record.id,
      issue_number:issue.number,comment_url:latest.html_url,updated_at:latest.updated_at,
      classes:role.primary?[role.primary,...role.secondary]:[],structured:output.structured,roles:role,
      provenance:{sha256:HASH(latest.body),comment_id:latest.id,identity_basis:'candidate_marker_and_current_issue_bibliography'}};
    return {status:'available',value};
  }catch{return {status:'withheld',value:null};}
}
export async function bounded(items,operation,limit=4){
  const result=new Array(items.length);let i=0;
  await Promise.all(Array.from({length:Math.min(limit,items.length)},async()=>{while(i<items.length){const n=i++;result[n]=await operation(items[n],n);}}));return result;
}
async function transport(url){
  const u=new URL(url),github=u.origin==='https://api.github.com';
  assert(github&&u.pathname.startsWith(`/repos/${REPO}/`)||u.origin===new URL(API).origin&&u.pathname===new URL(API).pathname,'reader_origin');
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),20000);
  try{
    const headers={Accept:'application/vnd.github+json','User-Agent':'cile-public-reading-builder'};
    if(github&&process.env.GITHUB_TOKEN)headers.Authorization='Bearer '+process.env.GITHUB_TOKEN;
    const response=await fetch(url,{headers,redirect:'error',signal:controller.signal});
    if(!response.ok)throw Object.assign(Error('source_http_'+response.status),{status:response.status});
    const raw=await response.text();assert(raw.length<=8000000,'source_limit');return JSON.parse(raw);
  }finally{clearTimeout(timer);}
}
async function paginate(url,read,max=100){
  const out=[],seen=new Set();
  for(let page=1;page<=max;page++){
    const data=await read(url+(url.includes('?')?'&':'?')+`per_page=100&page=${page}`);assert(Array.isArray(data)&&data.length<=100,'source_page');
    for(const row of data){assert(Number.isSafeInteger(row.id)&&!seen.has(row.id),'source_duplicate');seen.add(row.id);out.push(row);}
    if(data.length<100)return out;
  }throw Error('source_pagination_incomplete');
}
async function publicIndex(read,validators){
  let cursor=0,revision=null,total=null;const rows=new Map();
  do{
    const page=validators.validatePublicIndex(await read(API+'?view=index&cursor='+cursor+(revision?'&revision='+revision:'')));
    assert(revision===null||page.index_revision===revision,'index_revision_changed');
    assert(total===null||total===page.total,'index_total_changed');revision=page.index_revision;total=page.total;
    assert(page.next_cursor===null?cursor+page.records.length===total:page.next_cursor===cursor+page.records.length&&page.next_cursor>cursor,'index_cursor');
    for(const row of page.records){assert(!rows.has(row.candidate.id),'index_duplicate');rows.set(row.candidate.id,row);}
    cursor=page.next_cursor;
  }while(cursor!==null);
  return {rows,revision};
}
function matchPublic(c,record){return c&&c.id===record.id&&c.title===record.title&&String(c.doi||'').toLowerCase()===String(record.doi||'').toLowerCase()&&canonical([...(c.sourceLinks||[])].sort())===canonical([...record.sourceLinks].sort());}
export async function build({register,support,sourceCommit,generatedAt,read=transport,validators,parseManual,snapshotAPI}){
  assert(register.schemaVersion===1&&Array.isArray(register.records)&&support.schemaVersion===1&&Array.isArray(support.records),'input_schema');
  const supportRows=new Map(support.records.map(r=>[r.id,r]));assert(supportRows.size===support.records.length,'support_duplicate');
  let issueList=null,index=null;
  try{issueList=await paginate(`https://api.github.com/repos/${REPO}/issues?state=all&labels=curation%3Aqueue&sort=created&direction=asc`,read);}catch{}
  try{index=await publicIndex(read,validators);}catch{}
  const issues=new Map();
  for(const issue of issueList||[]){if(issue.pull_request)continue;const match=String(issue.body).match(/<!--\s*curator-candidate:([^\s>]+)\s*-->/);if(match){const list=issues.get(match[1])||[];list.push(issue);issues.set(match[1],list);}}
  const records=await bounded(register.records,async candidate=>{
    const row={candidate,support:supportRows.get(candidate.id)||null,manualStatus:issueList?'absent':'unavailable',manual:null,researchStatus:'unavailable',research:null,validationStatus:'unavailable',validation:null};
    const matches=issues.get(candidate.id)||[];
    if(matches.length>1)row.manualStatus='identity_mismatch';
    else if(matches.length===1){
      const issue=matches[0];
      if(!issueIdentity(issue,candidate))row.manualStatus='identity_mismatch';
      else try{
        const comments=await paginate(`https://api.github.com/repos/${REPO}/issues/${issue.number}/comments`,read,20);
        assert(comments.length>=Number(issue.comments||0),'comment_count_incomplete');
        const manual=compileManual(comments,candidate,issue,parseManual);row.manualStatus=manual.status;row.manual=manual.value;
      }catch{row.manualStatus='unavailable';}
    }
    if(index){
      const item=index.rows.get(candidate.id);
      if(!item){row.researchStatus='absent';row.validationStatus='absent';}
      else if(!matchPublic(item.candidate,candidate)){row.researchStatus='identity_mismatch';row.validationStatus='identity_mismatch';}
      else try{
        // Full research is read only when the service reports an available public projection.
        if(item.availability==='available'){
          const payload=validators.validatePublicResearch(await read(API+'?id='+encodeURIComponent(candidate.id)));
          assert(matchPublic(payload.candidate,candidate)&&payload.revision===item.research_revision,'research_revision_changed');
          assert(payload.availability==='available','research_state_changed');row.research=payload;row.researchStatus='available';
        }else row.researchStatus=item.availability==='withheld'?'withheld':'absent';
        const value=validators.validatePublicCompletion(await read(API+'?view=completion&id='+encodeURIComponent(candidate.id)));
        assert(value.candidate_id===candidate.id,'completion_identity');
        if(value.completed)assert(row.researchStatus==='available'&&value.research_revision===row.research.revision,'completion_revision');
        assert(value.revision===item.completion.revision,'completion_changed');row.validation=value;row.validationStatus='available';
      }catch{row.validationStatus='unavailable';if(!row.research)row.researchStatus='unavailable';}
    }
    return row;
  });
  // Refuse a mixed index edition if sources changed during export.
  if(index){try{const check=validators.validatePublicIndex(await read(API+'?view=index&cursor=0&revision='+index.revision));assert(check.index_revision===index.revision,'index_changed');}
    catch{for(const row of records){row.research=null;row.validation=null;row.researchStatus=row.validationStatus='unavailable';}}}
  const body={schemaVersion:1,projectionVersion:'CILE-READING-SNAPSHOT-1',generatedAt,sourceCommit,records};
  const snapshot={...body,digest:HASH(body)};snapshotAPI.validate(snapshot);
  return snapshot;
}
export function audit(snapshot,api){
  const counts=api.summary(snapshot),states={};
  for(const field of ['manualStatus','researchStatus','validationStatus']){states[field]={};for(const row of snapshot.records)states[field][row[field]]=(states[field][row[field]]||0)+1;}
  return {projection:snapshot.projectionVersion,sourceCommit:snapshot.sourceCommit,generatedAt:snapshot.generatedAt,digest:snapshot.digest,counts,states,
    annotations:snapshot.records.filter(r=>r.manual).map(r=>({id:r.candidate.id,source:r.manual.comment_url,sha256:r.manual.provenance.sha256,primary:r.manual.roles.primary})),
    exceptions:snapshot.records.filter(r=>[r.manualStatus,r.researchStatus,r.validationStatus].some(s=>['unavailable','identity_mismatch','withheld'].includes(s))).map(r=>({id:r.candidate.id,annotation:r.manualStatus,research:r.researchStatus,validation:r.validationStatus})),
    assessmentCompletion:'not_exported_by_current_sources',validation:'legacy_accepted_receipt_only',scientificDecisionsChanged:false};
}
async function main(){
  const output=process.argv[2]||path.join(ROOT,'site/reading-snapshot.json');
  const ctx=vm.createContext({URL,TextEncoder,crypto:crypto.webcrypto});
  for(const file of ['paper-sheet-manual.js','reading-snapshot.js'])vm.runInContext(await fs.readFile(path.join(ROOT,'site',file),'utf8'),ctx);
  const validators=await import(path.join(ROOT,'curator-app/src/public-paper-research.js'));
  const register=JSON.parse(await fs.readFile(path.join(ROOT,'site/data/paper-register.json'),'utf8'));
  const support=JSON.parse(await fs.readFile(path.join(ROOT,'site/paper-support.json'),'utf8'));
  const snapshot=await build({register,support,sourceCommit:process.env.GITHUB_SHA,generatedAt:new Date().toISOString(),validators,parseManual:(comment,id)=>{const out=ctx.CILEManualResearch.parseComment(comment,id);out.structured=ctx.CILEManualResearch.deriveStructured(out.sections,[]);return out;},snapshotAPI:ctx.CILEArchiveSnapshot});
  const report=audit(snapshot,ctx.CILEArchiveSnapshot);
  const raw=JSON.stringify(snapshot)+'\n';assert(raw.length<=30000000,'snapshot_limit');
  await fs.mkdir(path.dirname(output),{recursive:true});await fs.writeFile(output+'.tmp',raw);await fs.rename(output+'.tmp',output);
  await fs.writeFile(output+'.audit.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({counts:report.counts,states:report.states,digest:report.digest},null,2));
  if(snapshot.records.length&&report.counts.unknown===snapshot.records.length&&report.counts.researchContent===0)throw Error('no_research_source_readable');
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(error=>{console.error('Public reading export failed:',error.message);process.exitCode=1;});
