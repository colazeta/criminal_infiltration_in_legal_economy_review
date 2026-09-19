import test from 'node:test';
import assert from 'node:assert/strict';
import {documentFixture} from './document-repository.test.js';
import {handleMcp,MCP_TOOLS,serveMcp} from '../src/mcp.js';
import {indexDocument} from '../src/document-repository.js';
import {handleDocumentRead} from '../src/document-http.js';
import {storeExtraction} from '../src/paper-enrichment.js';

const req=(method,params={},extra={})=>new Request('https://cile.example/mcp',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json, text/event-stream','MCP-Protocol-Version':'2025-11-25',...extra},body:JSON.stringify({jsonrpc:'2.0',id:1,method,params})});
const call=async(x,name,args={})=>(await handleMcp(req('tools/call',{name,arguments:args}),x.env)).json();
test('MCP negotiates protocol, lists seven closed read-only tools and resource templates',async()=>{
 const x=await documentFixture();const init=await (await handleMcp(req('initialize',{protocolVersion:'2025-11-25',clientInfo:{name:'synthetic-client',version:'1'},capabilities:{}}),x.env)).json();
 assert.equal(init.result.protocolVersion,'2025-11-25');assert.equal(init.result.serverInfo.name,'cile-read-only');
 const listed=await (await handleMcp(req('tools/list'),x.env)).json();assert.equal(listed.result.tools.length,7);
 for(const t of listed.result.tools){assert.equal(t.annotations.readOnlyHint,true);assert.equal(t.annotations.openWorldHint,false);assert.equal(t.inputSchema.additionalProperties,false)}
 assert.ok((await (await handleMcp(req('resources/templates/list'),x.env)).json()).result.resourceTemplates.length>5);
});
test('MCP and document library resolve the same record, document and page',async()=>{
 const x=await documentFixture({publicDocument:true});await indexDocument(x.env,x.target.target_id,x.receipt.document_id,x.attestation);
 const paper=await call(x,'get_paper',{paper_id:x.record.id});assert.equal(paper.result.structuredContent.library.candidate_id,x.record.id);
 const web=await (await handleDocumentRead(new Request('https://cile.example/api?id='+x.record.id),x.env)).json();
 assert.deepEqual(paper.result.structuredContent.library,web);
 const full=await call(x,'search_full_text',{query:'procurement methods',top_k:3});const hit=full.result.structuredContent.hits[0];
 assert.equal(hit.document_id,web.documents[0].document_id);assert.equal(hit.page,2);
 const resource=await (await handleMcp(req('resources/read',{uri:hit.locator.uri}),x.env)).json();
 assert.equal(JSON.parse(resource.result.contents[0].text).document_id,hit.document_id);
});
test('bibliographic filters use the scoped index without changing scientific input hashes',async()=>{
 const x=await documentFixture();const original=x.target.input_sha256;
 const yes=await call(x,'search_papers',{author:'Test author',year_from:2019,year_to:2021});assert.equal(yes.result.structuredContent.records.length,1);
 const no=await call(x,'search_papers',{year_from:2021});assert.equal(no.result.structuredContent.records.length,0);
 assert.equal(x.db.prepare('SELECT input_sha256 FROM enrichment_targets').get().input_sha256,original);
});
test('request/schema bounds, duplicate IDs and SQL/path/URL injection fail safely',async()=>{
 const x=await documentFixture();
 for(const [name,args] of [['search_papers',{query:'x'.repeat(301)}],['search_papers',{year_from:99999}],['search_full_text',{query:'test',top_k:999}],['compare_papers',{paper_ids:[],fields:['summary']}],['compare_papers',{paper_ids:[x.record.id,x.record.id],fields:['summary']}],['get_paper',{paper_id:'../../secrets'}],['get_paper',{paper_id:'https://example.com'}],['get_paper',{paper_id:x.record.id,url:'https://example.com'}]])assert.equal((await call(x,name,args)).error.code,-32602);
 const sql=await call(x,'search_papers',{query:"' OR 1=1 --"});assert.equal(sql.result.structuredContent.records.length,0);
 const path=await (await handleMcp(req('resources/read',{uri:'cile://papers/../methodology'}),x.env)).json();assert.equal(path.error.code,-32602);
 assert.equal((await call(x,'publish',{paper_id:x.record.id})).error.code,-32602);
});
test('public text stays private and every MCP tool performs zero writes and zero external requests',async()=>{
 const x=await documentFixture();await indexDocument(x.env,x.target.target_id,x.receipt.document_id,x.attestation);
 const before=x.db.prepare('SELECT total_changes() n').get().n,old=globalThis.fetch;
 globalThis.fetch=()=>{throw Error('unexpected network operation')};
 try{
  const args={search_papers:{query:'procurement'},get_paper:{paper_id:x.record.id},search_full_text:{query:'procurement'},get_evidence:{paper_id:x.record.id,evidence_ids:['unavailable'],revision:'0'.repeat(64)},get_review_data:{paper_id:x.record.id,fields:['summary']},compare_papers:{paper_ids:[x.record.id],fields:['summary']},get_corpus_stats:{}};
  for(const tool of MCP_TOOLS){const result=await call(x,tool.name,args[tool.name]);assert.equal(result.error,undefined);assert.ok(!JSON.stringify(result).includes(x.text))}
  assert.equal((await call(x,'search_full_text',{query:'procurement'})).result.structuredContent.hits.length,0);
  assert.equal(x.db.prepare('SELECT total_changes() n').get().n,before);
 }finally{globalThis.fetch=old}
});
test('public evidence aliases are revision-scoped and retain source offsets',async()=>{
 const x=await documentFixture({publicDocument:true});await indexDocument(x.env,x.target.target_id,x.receipt.document_id,x.attestation);
 const missing=()=>({status:'not_reported',value:null,evidence_span_ids:[],origin:'source'});
 const reported=value=>({status:'reported',value,evidence_span_ids:['test-span'],origin:'source'});
 const p={schema_version:1,protocol_version:'CILE-ENRICH-1',codebook_version:'1.0.0',target_id:x.target.target_id,input_sha256:x.target.input_sha256,generated_by:{agent:'synthetic',model:'synthetic-test',prompt_sha256:'1'.repeat(64)},source_ids:[x.input.source_id],source_coverage:'full_text',spans:[{id:'test-span',source_id:x.input.source_id,start_offset:0,end_offset:45,locator:'p. 1'}],summary:reported('Evidence overview'),contribution:missing(),research_question:missing(),infiltration_definition:missing(),infiltration_operationalisation:missing(),authors_limitations:missing(),analyst_limitations:missing(),studies:[],datasets:[],analyses:[],variable_uses:[],findings:[],framework:{status:'insufficient_evidence',primary:null,rationale:missing(),secondary:[],alternative:null}};
 await storeExtraction(x.env,x.target,p,Date.now());
 const review=(await call(x,'get_review_data',{paper_id:x.record.id,fields:['summary']})).result.structuredContent;
 assert.equal(review.availability,'available');const evidenceIds=review.data.summary.evidence_span_ids;
 const resolved=await call(x,'get_evidence',{paper_id:x.record.id,evidence_ids:evidenceIds,revision:review.revision});
 const evidence=resolved.result.structuredContent.evidence[0];assert.equal(evidence.passage,x.text.slice(0,45));assert.deepEqual(evidence.pages,[1]);
 assert.equal(evidence.evidence_id,evidenceIds[0]);assert.ok(!JSON.stringify(review).includes(x.input.source_id));
 const stale=await call(x,'get_evidence',{paper_id:x.record.id,evidence_ids:evidenceIds,revision:'0'.repeat(64)});assert.equal(stale.result.isError,true);
 assert.equal((await call(x,'search_papers',{source_coverage:'full_text'})).result.structuredContent.records.length,1);
 const source=x.db.prepare('SELECT storage_key FROM enrichment_sources').get();x.kv.delete('evidence:'+source.storage_key+':0');
 const hidden=await call(x,'search_papers',{source_coverage:'full_text'}),unmatched=await call(x,'search_papers',{source_coverage:'abstract_only'});
 assert.deepEqual(hidden,unmatched,'Public filters/cursors must not reveal a withheld private match');
 const privateRead=await (await handleMcp(req('tools/call',{name:'get_review_data',arguments:{paper_id:x.record.id,fields:['summary']}}),x.env,{publicOnly:false})).json();
 assert.equal(privateRead.result.isError,true,'Private reads still require intact source text');
});
test('transport rejects untrusted origins, unsupported protocol, oversized bodies and malformed JSON',async()=>{
 const x=await documentFixture();assert.equal((await handleMcp(req('ping',{}, {Origin:'https://evil.invalid'}),x.env)).status,403);
 assert.equal((await handleMcp(req('ping',{}, {'MCP-Protocol-Version':'9999-01-01'}),x.env)).status,400);
 assert.equal((await handleMcp(req('ping',{}, {Accept:'application/json'}),x.env)).status,406);
 assert.equal((await handleMcp(new Request('https://cile.example/mcp'),x.env)).status,405);
 const oversized=new Request('https://cile.example/mcp',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json, text/event-stream'},body:' '.repeat(17000)});
 assert.equal((await handleMcp(oversized,x.env)).status,413);
 assert.equal((await serveMcp(req('ping'),null)).status,503);
});
test('internal failure never exposes SQL, private keys or provider secrets',async()=>{
 const env={REVIEW_DB:{prepare(){throw Error('secret-value SQL PRIVATE KEY /private/notes')}},SESSION_SECRET:'secret-value'};
 const response=await handleMcp(req('tools/call',{name:'get_corpus_stats',arguments:{}}),env);const body=await response.text();
 assert.ok(!body.includes('secret-value'));assert.ok(!body.includes('PRIVATE KEY'));assert.ok(body.includes('research_unavailable'));
});
