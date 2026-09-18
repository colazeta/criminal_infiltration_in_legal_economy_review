/* Synthetic software fixtures only; no research or completion evidence. */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../../site/paper-register.js',import.meta.url),'utf8');
const context=vm.createContext({document:{querySelector:()=>null},URL,AbortController,setTimeout,clearTimeout});
vm.runInContext(source,context);
const P=context.CILEPaperProcessing;
const revision='a'.repeat(64);
function row({available=true,accepted=false}={}) {
  return {research:available?'available':'not_assessed',coverage:available?'full_text':null,classes:available?['screening']:[],
    completionVerified:true,researchRevision:revision,referenceCoverage:[],
    completion:{status:accepted?'accepted':'not_attested',completed:accepted,revision:'b'.repeat(64),research_revision:revision,
      completed_at:accepted?'2026-09-17T09:00:00Z':null,protocol_version:accepted?'CILE-ENRICH-1':null,codebook_version:accepted?'1.0.0':null}};
}
function index(rows=[],changes={}) {
  return {rows:new Map(rows.map((r,i)=>['fixture-'+i,r])),progress:{total:3,checked:0,errors:0,running:false,scanned:false,...changes}};
}
for(const [name,progress,phase] of [
  ['not loaded',{},'idle'],['loading',{running:true},'loading'],
  ['failure',{scanned:true,errors:1},'error'],['index does not cover the register',{scanned:true},'error']
])test(name+': no zero completion count or percentage',()=>{
  const s=P.analysisSummary(index([],progress));assert.equal(s.phase,phase);assert.equal(s.counts,null);assert.equal(s.percentage,null);
  assert.doesNotMatch(s.text,/0\s*(?:\/|su)|0%|completamenti.*0/i);
});
test('partial results use only their loaded denominator and no global percentage',()=>{
  const s=P.analysisSummary(index([row({accepted:true})],{checked:1,scanned:true,errors:1}));
  assert.equal(s.phase,'partial');assert.equal(s.denominator,1);assert.equal(s.counts.completed,1);assert.equal(s.percentage,null);
  assert.match(s.text,/1 di 3/);assert.match(s.text,/soltanto questi 1/);
});
test('successful complete reads may show an actual zero',()=>{
  const s=P.analysisSummary(index([row({available:false}),row({available:false}),row({available:false})],{checked:3,scanned:true}));
  assert.equal(s.phase,'ready');assert.equal(s.counts.analyses,0);assert.equal(s.counts.completed,0);assert.equal(s.percentage,0);
});
test('completion still requires the exact validated receipt revision',()=>{
  const r=row({accepted:true});r.completion.research_revision='c'.repeat(64);
  const s=P.analysisSummary(index([r],{total:1,checked:1,scanned:true}));assert.equal(s.counts.completed,0);
});
test('full text and classification alone do not imply completion',()=>{
  const s=P.analysisSummary(index([row()],{total:1,checked:1,scanned:true}));
  assert.equal(s.counts.analyses,1);assert.equal(s.counts.fullText,1);assert.equal(s.counts.classified,1);assert.equal(s.counts.completed,0);
});
test('refresh removes previous counts while new data are loading',()=>{
  const s=P.analysisSummary(index([row({accepted:true})],{total:1,checked:1,running:true}));assert.equal(s.counts,null);assert.equal(s.percentage,null);
});
test('empty register has no undefined 0/0 percentage',()=>{
  const s=P.analysisSummary(index([],{total:0,scanned:true}));assert.equal(s.phase,'empty');assert.equal(s.percentage,null);assert.equal(s.counts,null);
});
class Element {
  constructor(tag){this.tag=tag;this.children=[];this.attributes={};this._text='';}
  set textContent(v){this._text=String(v??'');this.children=[];}
  get textContent(){return this._text+this.children.map(n=>n.textContent).join(' ');}
  append(...n){this.children.push(...n);}
  replaceChildren(...n){this._text='';this.children=n;}
  setAttribute(k,v){this.attributes[k]=v;}
  getAttribute(k){return this.attributes[k]??null;}
}
const document={createElement:t=>new Element(t)};
const sheetContext=vm.createContext({document,URL,CILEPaperProcessing:P});
vm.runInContext(fs.readFileSync(new URL('../../site/paper-sheet-research.js',import.meta.url),'utf8'),sheetContext);
const sheet=sheetContext.CILEPaperResearch;
test('missing completion response is unknown, not a negative finding',()=>{
  const parent=new Element('section');sheet.renderProgress(parent,{availability:'not_assessed',research:null});
  assert.match(parent.textContent,/Stato del completamento non disponibile/);assert.doesNotMatch(parent.textContent,/Completamento non registrato|Completed|end-to-end/);
});
test('an observed negative completion receipt differs from an unavailable response',()=>{
  const parent=new Element('section');sheet.renderProgress(parent,{availability:'not_assessed',research:null},row().completion);
  assert.match(parent.textContent,/Completamento non registrato/);assert.doesNotMatch(parent.textContent,/QA e adjudication/);
});
test('manual annotations never overwrite a current structured public analysis',()=>{
  vm.runInContext(fs.readFileSync(new URL('../../site/paper-sheet-manual.js',import.meta.url),'utf8'),sheetContext);
  const parent=new Element('section');parent.setAttribute('data-research-availability','available');parent.textContent='Existing current research';
  assert.equal(sheetContext.CILEManualResearch.hydratePresetFields(parent,{}),false);assert.equal(parent.textContent,'Existing current research');
});
test('register and enrichment statistics share their display-state calculation',()=>{
  const stats=fs.readFileSync(new URL('../../site/enrichment-statistics.js',import.meta.url),'utf8');
  assert.match(stats,/P\.analysisSummary\(index\)/);assert.match(stats,/counts\.hidden=!view\.counts/);
  assert.doesNotMatch(source,/attestazione backend valida|Completamenti verificati finora|stati analitici verificati/);
});
test('geographic read errors are not counted as successfully loaded papers',()=>{
  const geo=fs.readFileSync(new URL('../../site/geography-statistics.js',import.meta.url),'utf8');
  assert.match(geo,/entries\.get\(r\.id\)\.status!=='error'/);assert.doesNotMatch(geo,/Verificate.*schede nella vista/);
});
test('category refresh clears stale metrics before showing loading or errors',()=>{
  const cat=fs.readFileSync(new URL('../../site/categorisation-statistics.js',import.meta.url),'utf8');
  const clear=cat.indexOf("for(const node of Object.values(metricNodes))node.textContent='—'");
  assert.ok(clear>0&&clear<cat.indexOf('if(running){status.textContent='));
});
test('shared definition explicitly separates loading, completion and inclusion',()=>{
  const method=fs.readFileSync(new URL('../../site/method.html',import.meta.url),'utf8');
  assert.match(method,/id="reading-status"/);assert.match(method,/Il caricamento non avvia nuove analisi/i);assert.match(method,/Inclusione nel corpus/);
});
