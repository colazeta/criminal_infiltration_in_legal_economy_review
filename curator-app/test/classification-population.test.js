/* Entire candidate-sized synthetic population; no scientific corpus records. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import {summarizeContributions} from '../src/public-paper-research.js';
import {indexRow} from './index-fixture.js';
const context=vm.createContext({document:{querySelector:()=>null},URL,AbortController,setTimeout,clearTimeout,Intl});
for(const file of ['paper-register.js','categorisation-statistics.js'])vm.runInContext(fs.readFileSync(new URL('../../site/'+file,import.meta.url),'utf8'),context);
const P=context.CILEPaperProcessing,C=context.CILECategorisationStatistics;
const classes=['aetiology','diagnosis','screening','therapy','prognosis','prevention'];
test('all 294 candidates have identical candidate-level class membership in filters and statistics',()=>{
 const records=[],rows=new Map(),filterRows=new Map();
 for(let i=0;i<294;i++){
  const record={id:'CAND-POPULATION-'+i,title:'Synthetic '+i,doi:'',sourceLinks:[],year:2000+i%20};records.push(record);
  const proposals=i%7===0?[]:[{classes:[{category:classes[i%6],role:'primary'},{category:classes[(i+1)%6],role:'secondary'},{category:classes[(i+2)%6],role:'alternative'},...(i%9===0?[{category:classes[(i+3)%6],role:'primary'}]:[])]}];
  const row=indexRow(record);row.annotation_summary.count=proposals.length;row.classification=summarizeContributions(null,{annotations:proposals,conflicts:0});rows.set(record.id,C.validateIndexRow(row));filterRows.set(record.id,P.indexState(row,record));
 }
 const stats=C.aggregate(records,rows),index={rows:filterRows,progress:{total:294,checked:294,errors:0,scanned:true,running:false}},summary=P.analysisSummary(index);
 assert.equal(summary.counts.classified,stats.classified);assert.equal(summary.counts.completed,0);assert.equal(summary.counts.analyses,0);assert.equal(summary.counts.annotated,stats.classified);
 for(const category of stats.categories)assert.equal(records.filter(r=>P.matches(filterRows.get(r.id),'all',category.key)).length,category.any);
 assert.equal(stats.states.reduce((n,s)=>n+s.count,0),294);assert.equal(stats.states.find(s=>s.state==='conflict').count,summary.counts.classificationConflicts);
});
test('alternative proposals never enter class filters and incompatible roles remain conflicts',()=>{
 const record={id:'CAND-ALTERNATIVE',title:'Synthetic',doi:'',sourceLinks:[]},row=indexRow(record);
 row.classification=summarizeContributions(null,{annotations:[{classes:[{category:'therapy',role:'alternative'}]}],conflicts:0});
 assert.equal(P.matches(P.indexState(row,record),'all','therapy'),false);
 row.classification=summarizeContributions(null,{annotations:[{classes:[{category:'therapy',role:'primary'},{category:'therapy',role:'secondary'}]}],conflicts:0});
 const result=C.aggregate([record],new Map([[record.id,C.validateIndexRow(row)]]));assert.equal(result.categories.find(c=>c.key==='therapy').any,1);assert.equal(row.classification.has_conflict,true);
});
