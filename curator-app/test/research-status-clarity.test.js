import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const site=new URL('../../site/',import.meta.url);
const source=fs.readFileSync(new URL('paper-register.js',site),'utf8');
const context=vm.createContext({document:{querySelector:()=>null},URL,AbortController,setTimeout,clearTimeout});
vm.runInContext(source,context);
const P=context.CILEPaperProcessing;
const record={id:'CAND-SOFTWARE-TEST',title:'Synthetic test record',doi:'',sourceLinks:[]};
function row(overrides={}){return {support:'checked',summary:false,research:'not_assessed',classes:[],coverage:null,completionVerified:true,
  researchRevision:'a'.repeat(64),referenceCoverage:[],completion:{status:'not_attested',completed:false,revision:'c'.repeat(64),research_revision:'a'.repeat(64),completed_at:null,protocol_version:null,codebook_version:null},...overrides};}
function index(rows,overrides={}){return {rows:new Map(rows.map((r,i)=>['test'+i,r])),progress:{running:false,scanned:true,checked:rows.length,errors:0,total:rows.length,...overrides}};}
for(const [name,progress,records] of [
  ['initial loading has not been requested',{scanned:false,checked:0},[row({completionVerified:false,research:'pending'})]],
  ['loading clears previous positives',{running:true},[row({research:'available',coverage:'full_text',classes:['diagnosis']})]],
  ['partial reading does not publish final zeros',{checked:1},[row(),row({completionVerified:false,research:'pending'})]],
  ['total failure does not imply no research',{errors:1,checked:0},[row({completionVerified:false,research:'pending'})]],
  ['an integrity error with all rows still withholds totals',{errors:1},[row()]],
])test(name,()=>{const view=P.overview(index(records,progress));assert.equal(view.ready,false);for(const k of ['analyses','fullText','categories','references','validated','assessmentComplete'])assert.equal(view[k],null,k);assert.equal(P.overviewBreakdown(view),'');});
test('genuine zeros are allowed after a full, successful read',()=>{const view=P.overview(index([row()]));assert.equal(view.ready,true);assert.equal(view.analyses,0);assert.equal(view.validated,0);assert.match(P.overviewBreakdown(view),/consultabili: 0/);assert.equal(view.assessmentComplete,null);});
test('summary availability is independent of research loading',()=>{const view=P.overview(index([row({summary:true,research:'pending',completionVerified:false}),row({research:'pending',completionVerified:false})],{scanned:false,checked:0}));assert.equal(view.summaries,1);assert.equal(view.analyses,null);assert.match(view.summaryText,/1 sintesi disponibili/);});
test('failed summary reads do not become zero summaries',()=>{const view=P.overview(index([row({support:'error'})]));assert.equal(view.summaries,null);assert.equal(view.analyses,0);assert.doesNotMatch(view.summaryText,/0 sintesi/);});
test('accepted legacy validation never supplies F5 assessment completion',()=>{const r=row({research:'available',coverage:'full_text',classes:['diagnosis'],completion:{status:'accepted',completed:true,revision:'c'.repeat(64),research_revision:'a'.repeat(64),completed_at:'2026-09-17T12:00:00Z',protocol_version:'CILE-ENRICH-1',codebook_version:'1.0.0'}});const v=P.overview(index([r]));assert.equal(v.validated,1);assert.equal(v.assessmentComplete,null);assert.equal(P.matches(r,'completed'),true,'legacy URL filter remains compatible');assert.equal(P.hasRecordedValidation(r),true);});
test('receipt revision mismatch cannot create validation',()=>{const r=row({research:'available',completion:{status:'accepted',completed:true,revision:'c'.repeat(64),research_revision:'b'.repeat(64),completed_at:'2026-09-17T12:00:00Z',protocol_version:'CILE-ENRICH-1',codebook_version:'1.0.0'}});assert.equal(P.hasRecordedValidation(r),false);});
test('absent reference coverage is unknown, not zero',()=>{assert.equal(P.overview(index([row({referenceCoverage:undefined})])).references,null);assert.equal(P.overview(index([row({referenceCoverage:[]})])).references,0);});
test('empty register does not create a completion percentage',()=>{const view=P.overview(index([]));assert.equal(view.phase,'empty');assert.equal(view.ready,false);assert.equal(view.validated,null);assert.equal(P.overviewBreakdown(view),'');});
test('statistics can read analysis without pretending to verify summaries',async()=>{
 const urls=[];const idx=P.createIndex([record],{loadSummaries:false,read:async url=>{urls.push(url);return {schema_version:1,projection_version:'CILE-PUBLIC-INDEX-1',index_revision:'b'.repeat(64),total:1,next_cursor:null,records:[{candidate:record,availability:'not_assessed',research_revision:'a'.repeat(64),classes:[],generation_kind:null,source_coverage:null,framework_status:null,reference_coverage:[],completion:row().completion}]};}});
 await idx.scan();assert.equal(urls.length,1);assert.equal(idx.rows.get(record.id).support,'pending');assert.equal(P.overview(idx).ready,true);assert.equal(P.overview(idx).summaries,null);
});
test('public copy labels the legacy filter as validation, not completion',()=>{assert.match(source,/\['completed', 'Con validazione finale registrata'\]/);assert.doesNotMatch(source,/Completati e validati \(end-to-end\)|Percentuale finale non attestabile|Completamenti verificati finora/);});
const sheetContext=vm.createContext({URL});vm.runInContext(fs.readFileSync(new URL('paper-sheet-research.js',site),'utf8'),sheetContext);
for(const [state,pattern] of [[null,/non disponibile/],['not_attested',/non registrata/],['stale',/precedente/],['withheld',/non è consultabile/],['not_registered',/non è presente/]])test('validation state is distinct: '+state,()=>{
 const text=sheetContext.CILEPaperResearch.validationLabel(state?{status:state}:null,false);assert.match(text,pattern);assert.doesNotMatch(text,/non completat|Completed/);
});
test('accepted validation display is explicit',()=>{assert.match(sheetContext.CILEPaperResearch.validationLabel({status:'accepted'},true),/Validazione finale registrata/);});
test('manual reading still fills the same existing sections',()=>{for(const name of ['paper-sheet-manual.js','paper-sheet-research.js'])assert.ok(fs.readFileSync(new URL(name,site),'utf8').includes('Fonti consultate e informazioni sulla scheda'));});
test('missing bibliography arrays are rejected, never replaced with a zero population',()=>{const code=fs.readFileSync(new URL('bibliometrics.js',site),'utf8');assert.match(code,/invalid_bibliometric_data/);assert.doesNotMatch(code,/Array\.isArray\((archive|register)\.records\) \? .* : \[\]/);assert.match(code,/ui\.toggle\.disabled=true/);});
test('private source no longer asserts an extraction never ran from an empty list',()=>{const code=fs.readFileSync(new URL('enrichment.js',site),'utf8');assert.doesNotMatch(code,/non è stata eseguita un’estrazione scientifica|Estrazione scientifica automatica non attiva/);assert.match(code,/if\(!Array\.isArray\(rows\)\)/);assert.match(code,/not_applicable:'Non applicabile'/);});
