import test from 'node:test';
import assert from 'node:assert/strict';
import {setup} from './enrichment-store.test.js';
import {syncTargets,saveSource} from '../src/paper-enrichment.js';
import {sha256} from '../src/review-v2.js';
import {importDocument} from '../src/enrichment-assets.js';
import {digestBytes,indexDocument,documentLibrary,readDocumentPage,searchFullText,coveragePage,sourceDocumentsVerified,verifyIndex} from '../src/document-repository.js';

// Synthetic transport bytes only. Real PDF parsing is tested by test_document_text.py.
export async function documentFixture({publicDocument=false,id='CAND-DOCUMENT-TEST'}={}){
 const x=setup();await x.core.ready;const env=await x.core.environment();
 const record={id,title:'Synthetic procurement study',doi:'10.1234/synthetic',sourceLinks:['https://docs.iza.org/synthetic.pdf'],authors:'Test author',year:2020,venue:'Test journal',reviewStatus:'pending'};
 await syncTargets(env,{schemaVersion:1,records:[record]},Date.now());
 const target=x.db.prepare('SELECT * FROM enrichment_targets').get();
 const text='First page 😀. '+('Company data support a synthetic procurement analysis. '.repeat(10))+'\f'+'Second page. '+('Procurement methods and results are source reported. '.repeat(12))+'\f';
 const source=await saveSource(env,target,{provider:'Synthetic',source_url:record.sourceLinks[0],evidence_kind:'full_text',text},Date.now());
 const bytes=new TextEncoder().encode('%PDF-1.7\nSynthetic test fixture only.\n%%EOF');
 const input={input_sha256:target.input_sha256,source_id:source,pdf_sha256:await digestBytes(bytes),source_text_sha256:await sha256(text),bytes_base64:Buffer.from(bytes).toString('base64'),retention_basis:'Synthetic private research fixture',licence_status:'Synthetic licence observation',licence_url:publicDocument?'https://creativecommons.org/licenses/by/4.0/':null,attribution:'Synthetic test author',visibility:publicDocument?'public':'private',rights_verified:publicDocument};
 const receipt=await importDocument(env,target.target_id,input,Date.now());
 const attestation={protocol_version:'CILE-DOCUMENT-TEXT-1',method:'native',extractor_version:'synthetic-test-only 1.0',page_count:2,text_sha256:input.source_text_sha256,pdf_sha256:input.pdf_sha256,parser_validated:true};
 return {...x,env,record,target,text,bytes,input,receipt,attestation};
}
test('page/chunk indexing preserves original Unicode offsets and replays without new rows',async()=>{
 const x=await documentFixture();const first=await indexDocument(x.env,x.target.target_id,x.receipt.document_id,x.attestation);
 const before=x.db.prepare('SELECT count(*) n FROM enrichment_document_terms').get().n;
 const second=await indexDocument(x.env,x.target.target_id,x.receipt.document_id,x.attestation);
 assert.equal(second.replayed,true);assert.equal(first.extraction_id,second.extraction_id);
 assert.equal(x.db.prepare('SELECT count(*) n FROM enrichment_document_terms').get().n,before);
 const page=await readDocumentPage(x.env,x.record.id,x.receipt.document_id,2,{publicOnly:false});
 assert.equal(page.start_offset,x.text.indexOf('Second page'));assert.equal(page.text,x.text.slice(page.start_offset));
 assert.equal(page.offset_unit,'utf16');assert.equal(page.paper_id,null);assert.equal(page.candidate_id,x.record.id);
});
test('public text and document IDs require independently verified current rights',async()=>{
 const x=await documentFixture();await indexDocument(x.env,x.target.target_id,x.receipt.document_id,x.attestation);
 const library=await documentLibrary(x.env,x.record.id);assert.equal(library.documents[0].document_id,undefined);
 assert.equal(library.documents[0].public_downloadable,false);
 assert.equal((await searchFullText(x.env,{query:'procurement'})).hits.length,0);
 await assert.rejects(readDocumentPage(x.env,x.record.id,x.receipt.document_id,1),/document_not_public/);
 assert.equal((await searchFullText(x.env,{query:'procurement'},{publicOnly:false})).hits.length,2);
});
test('public full-text results resolve exact passages and rights withdrawal hides every access path',async()=>{
 const x=await documentFixture({publicDocument:true});await indexDocument(x.env,x.target.target_id,x.receipt.document_id,x.attestation);
 const hits=(await searchFullText(x.env,{query:'procurement methods'})).hits;assert.equal(hits.length,1);
 const h=hits[0];assert.equal(h.page,2);assert.equal(h.passage,x.text.slice(h.locator.start_offset,h.locator.end_offset));
 assert.equal(h.document_id,x.receipt.document_id);assert.equal((await documentLibrary(x.env,x.record.id)).documents[0].manifestation_id,h.manifestation_id);
 await importDocument(x.env,x.target.target_id,{...x.input,visibility:'private',rights_verified:false,licence_url:null,retention_basis:'Synthetic rights revocation'},Date.now()+1000);
 assert.equal((await searchFullText(x.env,{query:'procurement'})).hits.length,0);
 await assert.rejects(readDocumentPage(x.env,x.record.id,x.receipt.document_id,1),/not_public/);
});
test('completion needs the retained document and verified page extraction; a URL/full_text flag is insufficient',async()=>{
 const x=await documentFixture();const input={source_ids:[x.input.source_id],source_coverage:'full_text'};
 await assert.rejects(sourceDocumentsVerified(x.env,x.target,input),/document_trace_required/);
 await indexDocument(x.env,x.target.target_id,x.receipt.document_id,x.attestation);await sourceDocumentsVerified(x.env,x.target,input);
 x.kv.delete('document:'+x.input.pdf_sha256+':0');await assert.rejects(sourceDocumentsVerified(x.env,x.target,input),/document_trace_required/);
});
test('wrong text/page/hash/method attestation cannot create an extraction receipt',async()=>{
 const x=await documentFixture();
 for(const change of [{text_sha256:'0'.repeat(64)},{page_count:3},{method:'guessed'},{parser_validated:false}])await assert.rejects(indexDocument(x.env,x.target.target_id,x.receipt.document_id,{...x.attestation,...change}));
 assert.equal(x.db.prepare('SELECT count(*) n FROM enrichment_document_extractions').get().n,0);
});
test('database rejects foreign manifestation/page relationships and protects retained history',async()=>{
 const x=await documentFixture();const result=await indexDocument(x.env,x.target.target_id,x.receipt.document_id,x.attestation);
 assert.throws(()=>x.db.prepare('UPDATE enrichment_document_pages SET end_offset=1').run(),/immutable/);
 assert.throws(()=>x.db.prepare('INSERT INTO enrichment_document_chunks VALUES (?,?,?,?,?,?)').run('x',result.extraction_id,99,0,5,'0'.repeat(64)),/chunk outside page|FOREIGN KEY/);
 const v=await verifyIndex(x.env,x.target,x.receipt.document_id);assert.equal(v.extraction.source_id,x.input.source_id);
});
test('bounded private coverage keeps missingness distinct and verifies actual stored bytes',async()=>{
 const x=await documentFixture();const before=await coveragePage(x.env);assert.equal(before.records[0].unresolved_blocker,'document_extraction_missing');
 assert.equal(before.records[0].assessment_completed,null);assert.equal(before.records[0].acquisition_status,'acquired');
 await indexDocument(x.env,x.target.target_id,x.receipt.document_id,x.attestation);const after=await coveragePage(x.env);
 assert.equal(after.records[0].page_count,2);assert.equal(after.records[0].unresolved_blocker,null);
 await assert.rejects(coveragePage(x.env,{limit:1000}));
});
test('query/identity/page bounds reject injection and never trigger network requests',async()=>{
 const x=await documentFixture();const old=globalThis.fetch;globalThis.fetch=()=>{throw Error('unexpected external request')};
 try{for(const args of [{query:'test',top_k:1000},{query:'test',paper_ids:['../../secret']},{query:'a '.repeat(1000)}])await assert.rejects(searchFullText(x.env,args));
  await assert.rejects(documentLibrary(x.env,'https://example.com'));
  await assert.rejects(readDocumentPage(x.env,x.record.id,'../object',1));
  assert.equal((await searchFullText(x.env,{query:"x' OR 1=1 --"})).hits.length,0);
 }finally{globalThis.fetch=old}
});
test('index admission rolls back atomically when the existing preservation budget would be exceeded',async()=>{
 const x=await documentFixture();
 x.db.prepare('UPDATE enrichment_catalogue_index SET authors=?').run('x'.repeat(16000000));
 await assert.rejects(indexDocument(x.env,x.target.target_id,x.receipt.document_id,x.attestation),/document_preservation_capacity/);
 for(const table of ['enrichment_manifestations','enrichment_document_bindings','enrichment_document_extractions','enrichment_document_chunks','enrichment_document_terms'])assert.equal(x.db.prepare(`SELECT COUNT(*) n FROM ${table}`).get().n,0);
 assert.equal(x.db.prepare('SELECT COUNT(*) n FROM enrichment_documents').get().n,1);
});
