/* Entire pinned repository population -> real archive writer -> relational
   readback -> encrypted backup -> independent restored store and integrity audit.
   Source rows/ledgers stay private. No network or production writes. */
import {readFileSync,writeFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {isolatedStore,captureBackup} from './private-backup.mjs';
import {archiveBackupPage} from '../../curator-app/src/archive-preservation.js';
import {ingestCandidateObservation,exportCandidateObservations,auditCandidateArchive} from '../../curator-app/src/candidate-archive.js';
import {canonicalJson,sha256} from '../../curator-app/src/review-v2.js';
import contract from '../../ontology/modules/candidate-archive.json' with {type:'json'};
import {syncTargets} from '../../curator-app/src/paper-enrichment.js';
import {readPublicIndex} from '../../curator-app/src/public-paper-research.js';

export async function preflightCandidates(source,{restore=true}={}){
 const check=value=>{if(!value)throw Error('candidate_preflight_failed')};
 check(/^[a-f0-9]{40}$/.test(source.commit)&&Object.keys(source.domains).sort().join(',')===Object.keys(contract.domains).sort().join(','));
 const x=isolatedStore('isolated-candidate-rehearsal-key-not-production','f'.repeat(40));await x.core.requireReady();const env=await x.core.environment();
 try{
  const ledger=[],counts={},projected={};
  for(const domain of Object.keys(contract.domains)){
   const spec=contract.domains[domain],rows=source.domains[domain];check(Array.isArray(rows)&&rows.length>0&&new Set(rows.map(r=>r.candidate_id)).size===rows.length);
   for(const row of rows){
    const input={contract:contract.contract,action:'initialise',domain,source_commit:source.commit,expected_version:0,row};
    const first=await ingestCandidateObservation(env,input),replay=await ingestCandidateObservation(env,input);
    check(first.receipt_id===replay.receipt_id&&replay.replayed);
    ledger.push({source_commit:source.commit,source_path:spec.path,source_file_sha256:source.file_sha256[domain],candidate_id:row.candidate_id,domain,transformation:'typed-scalars-and-ordered-semicolon-relations-v1',outcome:'persisted_and_replayed_in_isolation',...first});
   }
   const exported=await exportCandidateObservations(env,domain);check(exported.records.length===rows.length);
   const originals=new Map(rows.map(r=>[r.candidate_id,r]));
   for(const r of exported.records){
    const expected={...originals.get(r.row.candidate_id)};
    for(const f of spec.repeated)expected[f]=expected[f].split(';').map(v=>v.trim()).filter(Boolean).join('; ');
    check(canonicalJson(expected)===canonicalJson(r.row));check(r.unresolved_revision_ids.length===0);
   }
   counts[domain]=rows.length;projected[domain]=exported.records.map(r=>r.row);
  }
  const identities=projected.bibliography.map(r=>r.candidate_id).sort();
  for(const rows of Object.values(projected))check(canonicalJson(rows.map(r=>r.candidate_id).sort())===canonicalJson(identities));
  // The existing target writer accepts the archive's bibliography directly. This
  // proves compatibility without using Pages as the source or enabling cutover.
  const register={schemaVersion:1,records:projected.bibliography.map(r=>({id:r.candidate_id,title:r.title,doi:r.doi,sourceLinks:r.source_links.split(';').map(v=>v.trim()).filter(Boolean)}))};
  await syncTargets(env,register,Date.now());
  let cursor=0,revision=null,visible=[];
  do{const page=await readPublicIndex(env,cursor,revision);revision=page.index_revision;visible.push(...page.records);cursor=page.next_cursor}while(cursor!==null);
  check(canonicalJson(visible.map(r=>r.candidate.id).sort())===canonicalJson(identities));
  const audit=await auditCandidateArchive(env);
  const backup=restore?(await captureBackup(request=>archiveBackupPage(env,x.storage,request),'isolated-candidate-rehearsal-key-not-production','f'.repeat(40))).receipt:null;
  return {report:{contract:'CILE-CANDIDATE-PREFLIGHT-1',scope:'isolated_repository_population',source_commit:source.commit,source_file_sha256:source.file_sha256,counts,relations_verified:true,source_integrity:audit,idempotency_verified:true,registered_public_targets:visible.length,isolated_restore:backup,production_migrated:false,authority_cutover:false,scientific_decisions_changed:false},ledger};
 }finally{x.db.close()}
}

if(process.argv[1]===fileURLToPath(import.meta.url)){
 try{
  if(process.argv.length!==3)throw Error('private_ledger_path_required');
  const root=fileURLToPath(new URL('../../',import.meta.url));
  const collect=spawnSync('python3',['-c',`
import csv,hashlib,io,json,subprocess
from pathlib import Path
root=Path('.')
domains=json.loads((root/'ontology/modules/candidate-archive.json').read_text())['domains']
commit=subprocess.check_output(['git','rev-parse','origin/main'],text=True).strip()
result={'commit':commit,'domains':{},'file_sha256':{}}
for domain,spec in domains.items():
 path=spec['path']; raw=(root/path).read_bytes()
 assert raw==subprocess.check_output(['git','show',commit+':'+path]), 'source_is_not_pinned_main'
 result['domains'][domain]=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
 result['file_sha256'][domain]=hashlib.sha256(raw).hexdigest()
print(json.dumps(result))
`],{cwd:root,encoding:'utf8',maxBuffer:16000000});
  if(collect.status!==0)throw Error('source_capture_failed');
  const result=await preflightCandidates(JSON.parse(collect.stdout));
  writeFileSync(process.argv[2],JSON.stringify({contract:'CILE-CANDIDATE-MIGRATION-LEDGER-1',scope:result.report.scope,entries:result.ledger}),{mode:0o600,flag:'wx'});
  process.stdout.write(JSON.stringify(result.report,null,2)+'\n');
 }catch(error){process.stderr.write((error.code||error.message||'candidate_preflight_failed')+'\n');process.exitCode=1}
}
