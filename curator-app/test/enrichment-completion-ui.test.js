import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {Element, createDocument} from './frontend-dom-fixture.js';

// Synthetic software fixtures: never registered works or calibration evidence.
const sheetSource=fs.readFileSync(new URL('../../site/paper-sheet-research.js',import.meta.url),'utf8');
const registerSource=fs.readFileSync(new URL('../../site/paper-register.js',import.meta.url),'utf8');
function setup(fetcher=async()=>{throw Error('offline');}) {
  const document=createDocument();
  const context=vm.createContext({document,URL,AbortController,setTimeout,clearTimeout,fetch:fetcher});
  vm.runInContext(sheetSource,context);vm.runInContext(registerSource,context);
  return {sheet:context.CILEPaperResearch,processing:context.CILEPaperProcessing};
}
const candidate={id:'CAND-COMPLETION-SOFTWARE-FIXTURE',title:'Synthetic',doi:'10.1234/test',sourceLinks:['https://example.org/paper']};
const fact=(value='Source-grounded paraphrase',status='reported')=>({value,status,evidence_span_ids:status==='reported'?['e1']:[],origin:'source'});
function fixture(coverage='full_text') {
  const research={assessment_state:'unreviewed_proposal',source_coverage:coverage,generation_kind:'automated',
    framework:{status:'proposed',primary:'screening',secondary:[],alternative:null,rationale:fact()},
    sources:[{id:'s1',kind:coverage==='full_text'?'full_text':'abstract',url:'https://example.org/paper',version:'Synthetic',checked_at:'2026-09-14T09:00:00Z'}],
    spans:[{id:'e1',source_id:'s1',locator:'evidence segment 1'}],updated_at:'2026-09-14T09:00:00Z',protocol_version:'CILE-ENRICH-1',codebook_version:'1.0.0',
    studies:[],datasets:[],analyses:[],variable_uses:[],findings:[]};
  for(const key of ['summary','contribution','research_question','infiltration_definition','infiltration_operationalisation','authors_limitations'])research[key]=fact();
  return {schema_version:1,projection_version:'CILE-PUBLIC-RESEARCH-1',candidate,availability:'available',research,revision:'a'.repeat(64)};
}

test('current proposal, class, full text and injected flags never imply completion',()=>{
  const {sheet,processing}=setup();const data=fixture();
  const p=sheet.progress(data);assert.equal(p.extraction,true);assert.equal(p.evidence,true);assert.equal(p.classification,true);
  assert.equal(p.completed,false);assert.equal(p.references,null);assert.equal(p.adjudication,null);
  const row={...processing.researchState(data),summary:true,completed:true,approved:true};
  assert.equal(processing.matches(row,'completed'),false);assert.equal(processing.matches(row,'ai_full_text'),true);
  data.research.assessment_state='confirmed';assert.throws(()=>sheet.progress(data));assert.throws(()=>sheet.selectRecord(data,candidate));
});

test('field diagnostics preserve unresolved facts and do not certify empty groups',()=>{
  const {sheet}=setup();const data=fixture();data.research.summary=fact(null,'not_verifiable');
  data.research.contribution=fact(null,'not_applicable');data.research.authors_limitations=fact(null,'not_reported');
  const p=sheet.progress(data);assert.equal(p.fields,6);assert.equal(p.unresolved,1);assert.equal(p.resolved,5);assert.equal(p.completed,false);
  data.research.source_coverage='abstract_only';data.research.sources[0].kind='abstract';
  assert.equal(sheet.progress(data).unresolved,3);
  data.research.research_question.evidence_span_ids=['missing'];assert.equal(sheet.progress(data).unresolved,4);
});

for(const availability of ['not_assessed','not_registered','stale','withheld']) {
  test(`${availability}: empty scientific sections remain available to the fallback without repetitive visible placeholders`,()=>{
    const {sheet}=setup();const data={...fixture(),availability,research:null};
    const parent=new Element('section');sheet.render(parent,data);
    assert.equal(sheet.progress(data).completed,false);assert.equal(sheet.progress(data).references,null);
    assert.match(parent.textContent,/Stato del completamento non disponibile/);
    assert.match(parent.textContent,/References e citazioni/);
    assert.match(parent.textContent,/Decisione scientifica separata/);
    assert.doesNotMatch(parent.textContent,/QA e adjudication|end-to-end/);
    assert.ok(parent.querySelectorAll('details').length>=9);
    assert.equal(parent.querySelectorAll('details').filter(d=>d.hidden).length,8);
    const buttons=parent.querySelectorAll('button');buttons.find(b=>b.textContent==='Mostra tutti i campi').fire('click');
    assert.ok(parent.querySelectorAll('details').every(d=>d.open===true));
    buttons.find(b=>b.textContent==='Richiudi le sezioni').fire('click');assert.ok(parent.querySelectorAll('details').every(d=>d.open===false));
  });
}

test('all-field expansion reaches nested datasets, methods, variables, findings and provenance',()=>{
  const {sheet}=setup();const data=fixture(),r=data.research;
  r.studies=[{id:'study1',geography:fact('Italy'),sample_size:fact('50'),population:fact('Firms')}];
  r.datasets=[{id:'dataset1',study_id:'study1',name:fact('Synthetic dataset'),provider:fact('Institution')}];
  r.analyses=[{id:'analysis1',study_id:'study1',dataset_ids:['dataset1'],method:fact('Panel analysis'),identification:fact('Comparison design'),robustness:fact('Alternative model')}];
  r.variable_uses=[{id:'variable1',analysis_id:'analysis1',dataset_ids:['dataset1'],original_name:fact('Exposure'),operationalisation:fact('Recorded risk'),role:fact('Predictor')}];
  r.findings=[{id:'finding1',analysis_id:'analysis1',variable_use_ids:['variable1'],statement:fact('Null finding'),estimate:fact('0'),uncertainty:fact('[-1,1]')}];
  const parent=new Element('section');sheet.render(parent,data);
  parent.querySelectorAll('button').find(b=>b.textContent==='Mostra tutti i campi').fire('click');
  assert.ok(parent.querySelectorAll('details').every(d=>d.open));
  for(const text of ['Italy','50','Synthetic dataset','Panel analysis','Comparison design','Alternative model','Exposure','Recorded risk','Null finding','[-1,1]','References e citazioni','Fonti consultate e versioni'])assert.ok(parent.textContent.includes(text),text);
  assert.match(parent.textContent,/Impossibile caricare bibliografia/);assert.match(parent.textContent,/non validata scientificamente/);
});

test('Completed control gives no false percentage or positive result and composes with reset',async()=>{
  const {sheet,processing}=setup(async url=>({ok:true,json:async()=>String(url).startsWith('./')?{records:{}}:fixture()}));
  const controls=new Element('form');
  const filter=processing.mount({controls,records:[candidate],onChange:()=>{},selectSupport:()=>({readingAid:null}),selectResearch:sheet.selectRecord});
  const mode=controls.querySelector('#register-processing-filter');assert.ok(mode.children.some(o=>o.value==='completed'));
  mode.value='completed';mode.fire('change');await new Promise(resolve=>setImmediate(resolve));
  assert.equal(filter.matches(candidate),false);assert.match(filter.emptyMessage(),/dati delle analisi non sono stati caricati/);
  const completion=controls.following.querySelector('#register-completion-status');
  assert.equal(completion.hidden,true);assert.equal(completion.textContent,'');
  assert.doesNotMatch(controls.following.textContent,/\d+%|Completamento registrato: 0/);
  controls.fire('reset');assert.equal(filter.matches(candidate),true);
});

test('transport failure stays unknown rather than a zero-reference or completed paper',async()=>{
  const {sheet}=setup();const parent=new Element('section');await sheet.load(parent,candidate);
  assert.match(parent.textContent,/non significa che l’analisi sia assente/);
  assert.doesNotMatch(parent.textContent,/Completed.*Sì|0 references/);
});
