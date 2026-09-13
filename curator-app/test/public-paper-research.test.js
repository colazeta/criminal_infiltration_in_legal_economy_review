import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {syncTargets,saveSource,storeExtraction} from '../src/paper-enrichment.js';
import {canonicalJson,sha256} from '../src/review-v2.js';
import {readPublicResearch,projectResearch,publicResearchAudit,servePublicResearch,safeResearchUrl,validatePublicResearch} from '../src/public-paper-research.js';
const now=Date.parse('2026-09-13T17:00:00Z');
export const record={id:'CAND-SYNTHETIC-RESEARCH',title:'Synthetic research fixture',doi:'10.1234/fixture',sourceLinks:['https://example.org/article']};
const missing=()=>({status:'not_verifiable',value:null,origin:'source',evidence_span_ids:[]});
const reported=(value,origin='source')=>({status:'reported',value,origin,evidence_span_ids:['private-span']});
async function setup(){
 const db=new DatabaseSync(':memory:');db.exec('PRAGMA foreign_keys=ON');db.exec(readFileSync(new URL('../migrations/0003_paper_enrichment.sql',import.meta.url),'utf8'));
 const adapter={prepare(sql){let v=[];return{bind(...args){v=args;return this},async first(){return db.prepare(sql).get(...v)||null},async all(){return{results:db.prepare(sql).all(...v)}},async run(){return{meta:{changes:db.prepare(sql).run(...v).changes}}}}},async batch(statements){db.exec('BEGIN');try{const r=[];for(const s of statements)r.push(await s.run());db.exec('COMMIT');return r}catch(e){db.exec('ROLLBACK');throw e}}};
 const kv=new Map(),env={REVIEW_DB:adapter,REVIEW_EVIDENCE:{async put(k,v){kv.set(k,v)},async get(k){return kv.has(k)?{async text(){return kv.get(k)}}:null}}};
 await syncTargets(env,{schemaVersion:1,records:[record]},now);
 const target=db.prepare('SELECT * FROM enrichment_targets').get();
 const text='Synthetic fixture source: the text is preserved privately. It discusses two distinct empirical studies.';
 await saveSource(env,target,{provider:'Synthetic fixture',source_url:'https://example.org/article',evidence_kind:'abstract',text},now);
 const source={...db.prepare('SELECT * FROM enrichment_sources').get(),text};
 const input={schema_version:1,protocol_version:'CILE-ENRICH-1',codebook_version:'1.0.0',target_id:target.target_id,input_sha256:target.input_sha256,generated_by:{agent:'PRIVATE REVIEWER NAME',model:'synthetic-test-model',prompt_sha256:null},source_ids:[source.source_id],source_coverage:'abstract_only',spans:[{id:'private-span',source_id:source.source_id,start_offset:0,end_offset:20,locator:'Abstract, first sentence'}],summary:reported('Brief original paraphrase'),contribution:reported('Comparison of operational definitions'),research_question:reported('Which characteristics distinguish the observations?'),infiltration_definition:missing(),infiltration_operationalisation:missing(),authors_limitations:missing(),analyst_limitations:reported('PRIVATE WORKING NOTES','analyst'),studies:[],datasets:[],analyses:[],variable_uses:[],findings:[],framework:{status:'proposed',primary:'diagnosis',rationale:reported('Describes the observable attributes of affected firms','analyst'),secondary:[{category:'aetiology',rationale:reported('Also evaluates a separate explanation of entry','analyst')}],alternative:'screening'}};
 const persist=async()=>storeExtraction(env,target,input,now);
 return{db,env,kv,target,source,input,persist};
}
export async function projectedFixture(){const x=await setup();await x.persist();return readPublicResearch(x.env,record.id)}
test('public projection is candidate-bound, source-grounded, proposed and strips private metadata',async()=>{
 const x=await setup();await x.persist();const out=await readPublicResearch(x.env,record.id);assert.equal(out.availability,'available');assert.equal(out.research.framework.primary,'diagnosis');assert.equal(out.research.framework.secondary[0].category,'aetiology');assert.equal(out.research.framework.alternative,'screening');assert.equal(out.research.assessment_state,'unreviewed_proposal');assert.equal(out.research.source_coverage,'abstract_only');
 const text=JSON.stringify(out);for(const privateValue of [x.target.target_id,x.source.source_id,x.source.storage_key,'PRIVATE REVIEWER NAME','PRIVATE WORKING NOTES','private-span','payload_json','generated_by','start_offset'])assert.ok(!text.includes(privateValue),privateValue);
 const {revision,...content}=out;assert.equal(revision,await sha256(canonicalJson(content)));
});
test('all six primary classes remain the recorded classes without keyword reclassification',async()=>{for(const primary of ['aetiology','diagnosis','screening','therapy','prognosis','prevention']){const x=await setup();x.input.framework={...x.input.framework,primary,secondary:[],alternative:null};await x.persist();assert.equal((await readPublicResearch(x.env,record.id)).research.framework.primary,primary)}});
test('missing, abstaining, stale and inactive are distinct',async()=>{
 const x=await setup();assert.equal((await readPublicResearch(x.env,record.id)).availability,'not_assessed');
 for(const status of ['insufficient_evidence','outside_framework']){const y=await setup();y.input.framework={status,primary:null,rationale:reported('Scope cannot establish the required contribution','analyst'),secondary:[],alternative:null};await y.persist();const out=await readPublicResearch(y.env,record.id);assert.equal(out.research.framework.status,status);assert.equal(out.research.framework.primary,null)}
 await x.persist();await syncTargets(x.env,{schemaVersion:1,records:[{...record,title:'Changed source identity'}]},now+1);assert.equal((await readPublicResearch(x.env,record.id)).availability,'stale');
 x.db.exec('UPDATE enrichment_targets SET active=0');assert.equal((await readPublicResearch(x.env,record.id)).availability,'not_registered');
});
test('multiple studies, dataset scopes, variable uses, null effects and uncertainty survive',async()=>{
 const x=await setup();const spec=JSON.parse(readFileSync(new URL('../../schema/paper-enrichment.schema.json',import.meta.url)));
 function item(type,id,refs={}){const out={};for(const[k,v]of Object.entries(spec.$defs[type].properties))out[k]=k==='id'?id:Object.hasOwn(refs,k)?refs[k]:missing();return out}
 for(let i=1;i<=2;i++){
  x.input.studies.push(item('study','s'+i));x.input.datasets.push(item('dataset','d'+i,{study_id:'s'+i}));
  x.input.analyses.push(item('analysis','a'+i,{study_id:'s'+i,dataset_ids:['d'+i]}));
  x.input.variable_uses.push(item('variable_use','v'+i,{analysis_id:'a'+i,dataset_ids:['d'+i]}));
  x.input.findings.push({...item('finding','f'+i,{analysis_id:'a'+i,variable_use_ids:['v'+i]}),statement:reported('No measurable difference'),estimate:reported('0'),uncertainty:reported('[-1, 1]')});
 }
 await x.persist();const out=await readPublicResearch(x.env,record.id),r=out.research;assert.equal(r.studies.length,2);assert.equal(r.findings[1].analysis_id,r.analyses[1].id);assert.equal(r.findings[1].variable_use_ids[0],r.variable_uses[1].id);assert.equal(r.findings[0].estimate.value,'0');assert.equal(r.findings[0].uncertainty.value,'[-1, 1]');assert.equal(r.analyses[0].identification.status,'not_verifiable');
});
test('metadata-only evidence never masquerades as a scientific source',async()=>{const x=await setup();await x.persist();const row=x.db.prepare('SELECT * FROM enrichment_proposals').get();const out=await projectResearch(x.target,row,[{...x.source,evidence_kind:'metadata'}]);assert.equal(out.availability,'withheld')});
test('source integrity failure withholds the research instead of serving stale content',async()=>{const x=await setup();await x.persist();x.kv.set(x.source.storage_key,'Modified body');assert.equal((await readPublicResearch(x.env,record.id)).availability,'withheld')});
test('source quotations, credentials and private source locators cannot be published',async()=>{
 const x=await setup();await x.persist();const row=x.db.prepare('SELECT * FROM enrichment_proposals').get();
 for(const value of ['sk-proj-'+'x'.repeat(40),'Bearer '+'x'.repeat(40),'https://example.org?a=1&token=secret',x.source.source_id]){
  const input=structuredClone(x.input);input.summary.value=value;const payload_json=canonicalJson(input);const out=await projectResearch(x.target,{...row,payload_json,payload_sha256:await sha256(payload_json)},[x.source]);assert.equal(out.availability,'withheld',value);
 }
 const quote=Array.from({length:30},(_,i)=>'word'+i).join(' ');const input=structuredClone(x.input);input.summary.value=quote;const payload_json=canonicalJson(input);
 assert.equal((await projectResearch(x.target,{...row,payload_json,payload_sha256:await sha256(payload_json)},[{...x.source,text:quote,content_sha256:await sha256(quote)}])).availability,'withheld');
 for(const url of ['javascript:alert(1)','http://example.org','https://u:p@example.org','https://example.org?X-Amz-Signature=a','https://x.workers.dev/private','https://127.0.0.1/data'])assert.equal(safeResearchUrl(url),false,url);
});
test('same candidate count with changed findings changes the public revision',async()=>{const x=await setup();await x.persist();const before=await readPublicResearch(x.env,record.id);x.input.summary.value='Updated contextualisation';await storeExtraction(x.env,x.target,x.input,now+1000);const after=await readPublicResearch(x.env,record.id);assert.notEqual(before.revision,after.revision);assert.equal(after.research.summary.value,'Updated contextualisation');const audit=await publicResearchAudit(x.env);assert.equal(audit.counts.registered,1);assert.equal(audit.counts.available,1);assert.equal(audit.records[0].revision,after.revision)});
test('unknown public fields and invented confirmation states fail closed',async()=>{const out=await projectedFixture();assert.throws(()=>validatePublicResearch({...out,reviewer:'private'}));out.research.framework.status='confirmed';assert.throws(()=>validatePublicResearch(out))});
test('public transport allows only a bounded public candidate query and forwards no credentials',async()=>{
 let forwarded=null;const out=await projectedFixture();const store={async fetch(r){forwarded=r;return Response.json(out)}};
 const response=await servePublicResearch(new Request('https://worker.example/api/public-paper-research?id='+record.id,{headers:{Cookie:'private-session',Authorization:'Bearer private'}}),store);assert.equal(response.status,200);assert.equal(response.headers.get('Cache-Control'),'no-store');assert.equal(response.headers.get('Access-Control-Allow-Origin'),'https://colazeta.github.io');assert.equal(forwarded.headers.get('Cookie'),null);assert.equal(forwarded.headers.get('Authorization'),null);
 for(const q of ['id=private-target','id='+record.id+'&sql=SELECT','id='+record.id+'&id='+record.id])assert.equal((await servePublicResearch(new Request('https://worker.example/api/public-paper-research?'+q),store)).status,400);
 assert.equal((await servePublicResearch(new Request('https://worker.example/api/public-paper-research?id='+record.id,{method:'POST'}),store)).status,405);
 assert.equal((await servePublicResearch(new Request('https://worker.example/api/public-paper-research?id='+record.id),null)).status,503);
});
