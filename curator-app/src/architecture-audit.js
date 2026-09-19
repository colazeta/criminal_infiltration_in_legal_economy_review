/* Read-only full-population preflight. Counts and closed diagnostics only leave
   the private store; evidence, identities, payloads and raw errors never do. */
import {canonicalJson,sha256} from './review-v2.js';
import {validateExtraction,validateRegistry} from './paper-enrichment.js';
import {readPublicResearch,readPublicCompletion} from './public-paper-research.js';
import base from './enrichment-migration.json' with {type:'json'};
import schedule from './enrichment-schedule-migration.json' with {type:'json'};
import adjudication from './enrichment-adjudication-migration.json' with {type:'json'};
import delivery from './enrichment-delivery-migration.json' with {type:'json'};
import cycle from '../../config/archive-cycle.json' with {type:'json'};
import logical from '../../ontology/modules/review-v2.json' with {type:'json'};

const LIMIT=100000;
const EXPECTED=[base,schedule,adjudication,delivery].flatMap(m=>[...m.sql.matchAll(/CREATE TABLE(?: IF NOT EXISTS)? (\w+)/g)].map(x=>x[1])).sort();
const CHILDREN={studies:['study_id'],datasets:['dataset_id','study_id'],analyses:['analysis_id','study_id'],variable_uses:['variable_use_id','analysis_id'],findings:['finding_id','analysis_id']};
const S=(db,sql,...values)=>db.prepare(sql).bind(...values);
const rows=async(db,sql,...values)=>(await S(db,sql,...values).all()).results;
const stableRows=values=>[...values].sort((a,b)=>canonicalJson(a).localeCompare(canonicalJson(b),'en'));

// Diagnostic names come only from the public ontology/migration allowlist.
// An unexpected private table name is represented by a digest, never returned.
export async function architectureSchema(env){
  const schema=await rows(env.REVIEW_DB,"SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT GLOB 'sqlite_*' ORDER BY type,name");
  const names=schema.filter(r=>r.type==='table').map(r=>r.name).sort();
  const platform=['__cf_kv','_cf_KV','_cf_EXTERNALS'];
  const known=new Set([...Object.keys(logical.tables),...EXPECTED,...platform]);
  return {contract:'CILE-ARCHITECTURE-SCHEMA-1',commit:env.DEPLOY_COMMIT,
    expected_present:EXPECTED.filter(n=>names.includes(n)),expected_missing:EXPECTED.filter(n=>!names.includes(n)),
    other_mapped_present:names.filter(n=>known.has(n)&&!EXPECTED.includes(n)&&!platform.includes(n)),
    platform_present:platform.filter(n=>names.includes(n)),
    unknown_table_sha256:await Promise.all(names.filter(n=>!known.has(n)).map(n=>sha256(n))),
    schema_sha256:await sha256(canonicalJson(schema)),private_content_exported:false};
}

async function databaseSnapshot(db){
  // Cloudflare's documented __cf_kv and workerd's _cf_KV/_cf_EXTERNALS are
  // platform tables. Their bodies must be read through the KV API, never SQL.
  // No wildcard excludes application tables from the completeness check.
  const schema=await rows(db,"SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT GLOB 'sqlite_*' AND name NOT IN ('__cf_kv','_cf_KV','_cf_EXTERNALS') ORDER BY type,name");
  const tables=schema.filter(r=>r.type==='table').map(r=>r.name).sort();
  if(canonicalJson(tables)!==canonicalJson(EXPECTED))throw Error('architecture_schema_set_mismatch');
  const data={},counts={},digests={};let bytes=0;
  for(const table of tables){
    const values=await rows(db,`SELECT * FROM ${table} LIMIT ${LIMIT+1}`);
    if(values.length>LIMIT)throw Error('architecture_population_limit');
    const encoded=canonicalJson(stableRows(values));bytes+=encoded.length;
    if(bytes>16000000)throw Error('architecture_population_limit');
    data[table]=values;counts[table]=values.length;
    digests[table]=await sha256(encoded);
  }
  return {data,counts,schema_sha256:await sha256(canonicalJson(schema)),state_sha256:await sha256(canonicalJson(digests))};
}

export async function auditArchitecture(env){
  const db=env.REVIEW_DB;
  if(!db||!env.REVIEW_EVIDENCE||!env.REVIEW_DOCUMENTS)throw Error('private_storage_required');
  const before=await databaseSnapshot(db),issues={};
  const flag=(code,n=1)=>{if(n)issues[code]=(issues[code]||0)+n};
  const fk=await S(db,'PRAGMA foreign_keys').first();
  if(Number(fk?.foreign_keys)!==1)flag('foreign_keys_disabled');
  flag('foreign_key_violation',(await rows(db,'PRAGMA foreign_key_check')).length);
  const integrity=await rows(db,'PRAGMA quick_check');
  if(!integrity.length||integrity.some(r=>Object.values(r)[0]!=='ok'))flag('sqlite_integrity_failure');
  const d=before.data,targets=new Map(d.enrichment_targets.map(t=>[t.target_id,t]));
  const inputs=new Map(d.enrichment_inputs.map(i=>[i.target_id+':'+i.input_sha256,i]));
  const sources=new Map(d.enrichment_sources.map(s=>[s.source_id,s]));
  const intactSources=new Set();
  for(const t of targets.values()){
    try{
      const record=JSON.parse(t.record_json);validateRegistry({schemaVersion:1,records:[record]});
      if(record.id!==t.record_id||await sha256(canonicalJson(record))!==t.input_sha256)flag('target_identity_hash_mismatch');
      const input=inputs.get(t.target_id+':'+t.input_sha256);
      if(!input||canonicalJson(JSON.parse(input.record_json))!==canonicalJson(record))flag('target_input_missing_or_different');
    }catch{flag('target_record_invalid')}
  }
  for(const input of inputs.values()){
    try{if(await sha256(canonicalJson(JSON.parse(input.record_json)))!==input.input_sha256)flag('input_hash_mismatch')}catch{flag('input_record_invalid')}
  }
  // Check every retained source, including historical inputs, not only visible rows.
  for(const source of sources.values()){
    if(!inputs.has(source.target_id+':'+source.input_sha256))flag('source_input_missing');
    try{
      const object=await env.REVIEW_EVIDENCE.get(source.storage_key);
      if(!object){flag('source_object_missing');continue}
      const text=await object.text();
      if(await sha256(text)!==source.content_sha256){flag('source_hash_mismatch');continue}
      intactSources.add(source.source_id);
    }catch{flag('source_object_unreadable')}
  }
  for(const p of d.enrichment_proposals){
    try{
      const payload=JSON.parse(p.payload_json);
      if(await sha256(canonicalJson(payload))!==p.payload_sha256)flag('proposal_hash_mismatch');
      const target=targets.get(p.target_id),input=inputs.get(p.target_id+':'+p.input_sha256);
      if(!target||!input){flag('proposal_input_missing');continue}
      const scoped={...target,input_sha256:p.input_sha256,record_json:input.record_json};
      const selected=[];let size=0;
      for(const id of payload.source_ids||[]){
        if(!intactSources.has(id))continue;
        const source=sources.get(id),object=await env.REVIEW_EVIDENCE.get(source.storage_key);
        if(!object)continue;
        const text=await object.text();size+=text.length;
        if(size>8000000)throw Error('architecture_population_limit');
        selected.push({...source,text});
      }
      if(selected.length!==(payload.source_ids||[]).length)flag('proposal_source_unreadable');
      else {try{validateExtraction(payload,scoped,selected)}catch{flag('proposal_contract_invalid')}}
      for(const [group,[id,parent]] of Object.entries(CHILDREN)){
        const persisted=d['enrichment_'+group].filter(r=>r.proposal_id===p.proposal_id);
        const expected=payload[group]||[];
        if(persisted.length!==expected.length)flag('proposal_child_count_mismatch');
        for(const row of persisted){
          const item=expected.find(x=>x.id===row[id]);
          if(!item||parent&&row[parent]!==item[parent]||canonicalJson(item)!==canonicalJson(JSON.parse(row.payload_json)))flag('proposal_child_content_mismatch');
        }
      }
      const f=d.enrichment_framework_proposals.find(f=>f.proposal_id===p.proposal_id);
      if(!f||f.primary_category!==payload.framework.primary||f.classification_status!==payload.framework.status||canonicalJson(JSON.parse(f.payload_json))!==canonicalJson(payload.framework))flag('framework_projection_mismatch');
    }catch(error){if(error.message==='architecture_population_limit')throw error;flag('proposal_record_invalid')}
  }
  for(const doc of d.enrichment_documents){
    const source=sources.get(doc.source_id);
    if(!source||source.target_id!==doc.target_id||source.input_sha256!==doc.input_sha256||source.content_sha256!==doc.source_text_sha256)flag('document_source_scope_mismatch');
    if(doc.visibility==='public'&&(!doc.rights_verified||!/^https:\/\/creativecommons\.org\/(?:licenses\/(?:by|by-sa)\/4\.0|publicdomain\/zero\/1\.0)\/$/.test(doc.licence_url||'')))flag('public_document_rights_invalid');
    try{
      const bytes=await env.REVIEW_DOCUMENTS.get(doc.storage_key);
      if(!bytes){flag('document_object_missing');continue}
      const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
      if(bytes.length!==doc.byte_length||digest!==doc.pdf_sha256)flag('document_hash_mismatch');
    }catch{flag('document_object_unreadable')}
  }
  for(const b of d.enrichment_bibliography_snapshots){
    const source=sources.get(b.source_id);
    if(!source||source.target_id!==b.target_id||source.input_sha256!==b.input_sha256)flag('bibliography_source_scope_mismatch');
    try{if(await sha256(canonicalJson(JSON.parse(b.payload_json)))!==b.payload_sha256)flag('bibliography_hash_mismatch')}catch{flag('bibliography_record_invalid')}
  }
  const publicStates={},completionStates={};let checked=0;
  for(const target of targets.values()){
    if(!target.active||target.cycle_id!==cycle.review_id)continue;
    try{
      const research=await readPublicResearch(env,target.record_id),completion=await readPublicCompletion(env,target.record_id,research);
      publicStates[research.availability]=(publicStates[research.availability]||0)+1;
      completionStates[completion.status]=(completionStates[completion.status]||0)+1;
      checked++;
    }catch{flag('public_projection_invalid')}
  }
  const after=await databaseSnapshot(db);
  if(before.state_sha256!==after.state_sha256||before.schema_sha256!==after.schema_sha256)throw Error('architecture_state_changed');
  return {contract:'CILE-ARCHITECTURE-AUDIT-1',commit:env.DEPLOY_COMMIT,
    backend:'durable_object_sqlite',scope:'entire_enrichment_store',complete:true,
    counts:before.counts,schema_sha256:before.schema_sha256,state_sha256:before.state_sha256,
    checked_public_targets:checked,public_states:publicStates,completion_states:completionStates,
    issues,integrity_verified:Object.keys(issues).length===0,
    private_content_exported:false,scientific_decisions_changed:false,cutover_ready:false};
}
