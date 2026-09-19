import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../../site/paper-sheet-manual.js',import.meta.url),'utf8');
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.textContent='';}
 append(...nodes){this.children.push(...nodes);}
}
const candidate='CAND-ANNOTATION-TEST';
const annotation=(id)=>({annotation_id:id.repeat(64),assessment_state:'unreviewed_manual_support',source_url:'https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/1#issuecomment-2',updated_at:'2026-09-19T00:00:00Z',sections:[{scope:'studies',group_label:'S1',fields:[{field_name:'population',value:'Declared population'}]}],classes:[],unparsed_lines:0});
const payload=()=>({schema_version:1,projection_version:'CILE-PUBLIC-ANNOTATIONS-1',candidate_id:candidate,annotations:[annotation('a'),annotation('b')],conflicts:0,revision:'c'.repeat(64)});
function setup(fetcher){const c=vm.createContext({document:{createElement:tag=>new Element(tag)},URL,AbortController,setTimeout,clearTimeout,fetch:fetcher});vm.runInContext(source,c);return c.CILEManualResearch;}
test('ordinary reading loads one identity-bound archive projection, without GitHub search or comments',async()=>{
 const calls=[];const api=setup(async(url,options)=>{calls.push({url,options});return {ok:true,json:async()=>payload()};});
 assert.equal((await api.fetchAnnotation({id:candidate})).annotations.length,2);
 assert.equal(calls.length,1);assert.ok(calls[0].url.endsWith('?view=annotations&id='+candidate));assert.equal(calls[0].options.credentials,'omit');assert.equal(calls[0].options.cache,'no-store');assert.doesNotMatch(source,/api\.github\.com|parseComment|deriveStructured/);
});
test('separate annotations retain their declared study groups without overwriting structured research',()=>{
 const api=setup(),parent=new Element('section'),existing=new Element('article');parent.append(existing);api.render(parent,api.validate(payload(),{id:candidate}));
 assert.equal(parent.children[0],existing);const papers=parent.children[1].children.filter(n=>n.tag==='article');assert.equal(papers.length,2);assert.deepEqual(papers.map(p=>p.dataset.annotationId),['a'.repeat(64),'b'.repeat(64)]);for(const p of papers)assert.ok(p.children.find(n=>n.tag==='details').children[0].textContent.endsWith(' · S1'));
});
test('foreign identities, duplicated annotations and invented review states cannot render',()=>{
 const api=setup();assert.throws(()=>api.validate(payload(),{id:'CAND-OTHER'}));const duplicate=payload();duplicate.annotations[1]=duplicate.annotations[0];assert.throws(()=>api.validate(duplicate,{id:candidate}));const approved=payload();approved.annotations[0].assessment_state='accepted';assert.throws(()=>api.validate(approved,{id:candidate}));
});
