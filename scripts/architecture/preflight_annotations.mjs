/* Reproduce a captured-source migration in isolated SQLite. No remote calls,
   production writes, invented reconciliation or scientific decisions. */
import {readFileSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';
import {isolatedStore,captureBackup} from './private-backup.mjs';
import {archiveBackupPage} from '../../curator-app/src/archive-preservation.js';
import {syncTargets} from '../../curator-app/src/paper-enrichment.js';
import {ingestAnnotation,auditAnnotations,readPublicAnnotations} from '../../curator-app/src/annotation-archive.js';
import {readPublicIndex} from '../../curator-app/src/public-paper-research.js';
import {sha256} from '../../curator-app/src/review-v2.js';

export async function preflight(data,register,{restore=false}={}){
 const assert=value=>{if(!value)throw Error('annotation_preflight_failed')};
 assert(data.repository==='colazeta/criminal_infiltration_in_legal_economy_review'&&Array.isArray(data.issues)&&Array.isArray(data.comments));
 const issues=new Map(data.issues.map(i=>[i.number,i]));assert(issues.size===data.issues.length&&new Set(data.comments.map(c=>c.id)).size===data.comments.length);
 const x=isolatedStore('synthetic-local-preflight-key-not-production','f'.repeat(40));await x.core.requireReady();const env=await x.core.environment();env.CURATOR_LOGIN='colazeta';
 try{
  await syncTargets(env,register,Date.now());
  const entity=(row,isIssue=false)=>({...Object.fromEntries(['id','body','created_at','updated_at','html_url'].map(k=>[k,row[k]])),actor:row.user?.login||null,...(isIssue?{number:row.number,is_pull_request:!!row.pull_request}:{})});
  const ledger=[];
  for(const comment of data.comments){
   const issue=issues.get(Number(comment.issue_url.split('/').at(-1)));assert(issue);
   const input={action:'observe',issue:entity(issue,true),comment:entity(comment)};
   const receipt=await ingestAnnotation(env,input);const replay=await ingestAnnotation(env,input);
   assert(!receipt.annotation||replay.replayed===true);
   ledger.push({source_issue_id:issue.id,source_comment_id:comment.id,source_updated_at:comment.updated_at,receipt});
  }
  const audit=await auditAnnotations(env),rows=[];let cursor=0,revision=null;
  do{const page=await readPublicIndex(env,cursor,revision);revision=page.index_revision;rows.push(...page.records);cursor=page.next_cursor;}while(cursor!==null);
  assert(rows.length===register.records.length);
  const context=vm.createContext({document:{querySelector:()=>null},URL,AbortController,setTimeout,clearTimeout,Intl});
  for(const file of ['paper-register.js','categorisation-statistics.js'])vm.runInContext(readFileSync(new URL('../../site/'+file,import.meta.url),'utf8'),context);
  const P=context.CILEPaperProcessing,C=context.CILECategorisationStatistics,states=new Map(),classification=new Map();
  for(const row of rows){
   const record=register.records.find(r=>r.id===row.candidate.id);assert(record);
   const sheet=await readPublicAnnotations(env,record.id);assert(sheet.revision===row.annotation_summary.revision&&sheet.annotations.length===row.annotation_summary.count);
   states.set(record.id,P.indexState(row,record));classification.set(record.id,C.validateIndexRow(row));
  }
  const summary=P.analysisSummary({rows:states,progress:{total:rows.length,checked:rows.length,scanned:true,running:false,errors:0}}),stats=C.aggregate(register.records,classification);
  assert(summary.counts.classified===stats.classified);
  for(const category of stats.categories)assert(category.any===register.records.filter(r=>P.matches(states.get(r.id),'all',category.key)).length);
  const backup=restore?(await captureBackup(request=>archiveBackupPage(env,x.storage,request),'synthetic-local-preflight-key-not-production','f'.repeat(40))).receipt:null;
  return {report:{contract:'CILE-ANNOTATION-PREFLIGHT-1',scope:'isolated_captured_inputs',source_captured_at:data.captured_at,
   source_issues:issues.size,source_comments:data.comments.length,candidates_checked:rows.length,audit,
   public_counts:summary.counts,class_counts:stats.categories,filter_statistics_agree:true,idempotency_verified:true,isolated_restore:backup,production_migrated:false,scientific_decisions_changed:false},ledger};
 }finally{x.db.close()}
}

if(process.argv[1]===fileURLToPath(import.meta.url)){
 try{
  const args=process.argv.slice(2),restore=args.at(-1)==='--restore-check';if(restore)args.pop();
  if(args.length<1||args.length>2)throw Error('usage');
  const bytes=readFileSync(args[0],'utf8'),data=JSON.parse(bytes),register=JSON.parse(readFileSync(new URL('../../site/data/paper-register.json',import.meta.url)));
  const {report,ledger}=await preflight(data,register,{restore});report.source_sha256=await sha256(bytes);
  if(args[1])writeFileSync(args[1],JSON.stringify({contract:'CILE-ANNOTATION-MIGRATION-LEDGER-1',scope:report.scope,source_sha256:report.source_sha256,entries:ledger}),{mode:0o600,flag:'wx'});
  process.stdout.write(JSON.stringify(report,null,2)+'\n');
 }catch{process.stderr.write('annotation_preflight_failed\n');process.exitCode=1}
}
