import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {indexRow,indexPage} from './index-fixture.js';
import {createDocument} from './frontend-dom-fixture.js';

function setup(fetch) {
  const document=createDocument();
  const context=vm.createContext({document,fetch,AbortController,setTimeout,clearTimeout,URL});
  vm.runInContext(fs.readFileSync(new URL('../../site/paper-register.js',import.meta.url),'utf8'),context);
  const controls=document.createElement('form');
  const filter=context.CILEPaperProcessing.mount({controls,records:[{id:'synthetic',title:'Synthetic',doi:'',sourceLinks:[]}],onChange:()=>{},selectSupport:p=>p,selectResearch:p=>p});
  return {controls,filter,status:()=>controls.following.querySelector('#register-processing-status').textContent};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));

test('pending summary and research states do not assert zero processed papers',async()=>{
  let finish;
  const pending=new Promise(resolve=>{finish=resolve;});
  const view=setup(async()=>{await pending;return {ok:true,json:async()=>({readingAid:{kind:'review_synopsis',synopsis:'Synthetic summary'}})};});
  assert.match(view.status(),/Disponibilità delle sintesi da verificare/);
  assert.match(view.status(),/Verifica delle sintesi in corso/);
  assert.doesNotMatch(view.status(),/0 sintesi disponibili|0 analisi AI/);
  finish();await tick();
  assert.match(view.status(),/1 sintesi disponibili/);
  assert.match(view.status(),/1\/1 stati delle sintesi verificati/);
});

test('complete research responses cannot hide failed synopsis reads in the combined filter',async()=>{
  const view=setup(async url=>{
    if(url.startsWith('./')) throw Error('support offline');
    return {ok:true,json:async()=>indexPage([indexRow({id:'synthetic',title:'Synthetic',doi:'',sourceLinks:[]})])};
  });
  await tick();
  const select=view.controls.querySelector('#register-processing-filter');select.value='content';select.fire('change');await tick();
  assert.match(view.status(),/1\/1 stati analitici verificati/);
  assert.match(view.status(),/sintesi non verificabili/);
  assert.doesNotMatch(view.status(),/0 sintesi disponibili/);
  assert.match(view.filter.emptyMessage(),/non è completa/);
});
