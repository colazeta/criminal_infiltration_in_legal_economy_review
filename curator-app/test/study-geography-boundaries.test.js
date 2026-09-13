import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../../site/study-geography.js',import.meta.url),'utf8');
function api(extra={}){const c=vm.createContext({Intl,AbortController,setTimeout,clearTimeout,...extra});vm.runInContext(source,c);return c.CILEStudyGeography;}
const A=api();
for(const value of ['Northern Ireland','Northern Ireland and Italy','Italy and Northern Ireland','Northern Cyprus'])test('does not reinterpret territorial exception: '+value,()=>assert.equal(A.normaliseGeography(value).kind,'unresolved'));
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.style={};this.textContent='';}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this.children=[...nodes];}
 setAttribute(){}
 addEventListener(){}
 get text(){return this.textContent+this.children.map(x=>x.text||'').join(' ');}
}
test('each missing study keeps its own missingness label',async()=>{
 const host=new Element('div');
 const data={availability:'available',research:{assessment_state:'unreviewed_proposal',source_coverage:'abstract_only',generation_kind:'automated',updated_at:'2026-09-13',studies:[{id:'s1',geography:{status:'reported',value:'Italy',origin:'source',evidence_span_ids:['e1']}},{id:'s2',geography:{status:'not_reported',value:null,origin:'source',evidence_span_ids:[]}}],spans:[{id:'e1',source_id:'source1',locator:'Abstract'}],sources:[{id:'source1',url:'https://example.org/paper'}]}};
 const B=api({document:{createElement:t=>new Element(t)},fetch:async()=>({ok:true,json:async()=>data}),CILEPaperResearch:{safeUrl:u=>u}});
 const records=[{id:'a',title:'Synthetic multi-study'}];B.mount({host,records,selectResearch:x=>x}).setRecords(records);
 await new Promise(r=>setTimeout(r,5));assert.match(host.text,/Studio 2 · Entità geografica: Paese non riportato/);
});
