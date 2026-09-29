import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {Element} from './frontend-dom-fixture.js';

const source=fs.readFileSync(new URL('../../site/workspace.js',import.meta.url),'utf8');
const base='https://example.test/project/';

// Browser event/history semantics needed by the reader; no network or research state.
function setup(initial=base) {
  let document;
  class Node extends Element {
    constructor(tag){super(tag);this.tagName=tag.toUpperCase();this.classList={add(){},remove(){}};}
    get firstChild(){return this.children[0]||null;}
    get lastChild(){return this.children.at(-1)||null;}
    get options(){return this.children;}
    matches(selector){return selector==='*'||super.matches(selector);}
    querySelectorAll(selector){
      const parts=selector.split(' ');
      if(parts.length===1)return super.querySelectorAll(selector);
      return this.querySelectorAll(parts[0]).flatMap(node=>node.querySelectorAll(parts.slice(1).join(' ')));
    }
    closest(selector){return this.matches(selector)?this:this.parentNode?.closest(selector)||null;}
    dispatchEvent(event){event.target??=this;for(const fn of this.listeners[event.type]||[])fn(event);if(event.bubbles)this.parentNode?.dispatchEvent(event);}
    fire(type){this.dispatchEvent({type,target:this,preventDefault(){},bubbles:true});}
    focus(){document.activeElement=this;}
    scrollIntoView(){this.scrolled=true;}
    close(){this.open=false;queueMicrotask(()=>this.fire('close'));}
  }
  document={createElement:tag=>new Node(tag),addEventListener(){},body:new Node('body'),activeElement:null};
  const events={},location={href:initial,hash:''};
  const stack=[{url:initial,state:null}];let cursor=0;
  const window={addEventListener:(event,fn)=>events[event]=fn,print(){}};
  const history={
    get state(){return stack[cursor].state;},
    pushState(state,_,url){stack.splice(++cursor);stack.push({state,url:String(url)});location.href=String(url);},
    replaceState(state,_,url){stack[cursor]={state,url:String(url)};location.href=String(url);},
    back(){if(cursor){location.href=stack[--cursor].url;events.popstate();}},
    forward(){if(cursor+1<stack.length){location.href=stack[++cursor].url;events.popstate();}},
  };
  const context=vm.createContext({document,window,location,history,URL,queueMicrotask,setTimeout,clearTimeout,navigator:{},Event:class{constructor(type,options){this.type=type;Object.assign(this,options)}}});
  vm.runInContext(source,context);
  const api=context.CILEWorkspace,make=(tag,text,id)=>{const n=document.createElement(tag);if(text)n.textContent=text;if(id)n.id=id;return n;};
  const controls=make('form'),search=make('input','','register-search'),drawer=make('details','','register-filter-panel'),grid=make('div');grid.className='register-filter-grid';drawer.append(grid);controls.append(search,drawer);
  function select(id,label,values){const wrapper=make('label'),s=make('select','',id);wrapper.append(make('span',label),s);for(const[value,text]of values){const o=make('option',text);o.value=value;s.append(o);}grid.append(wrapper);return s;}
  const mode=select('register-processing-filter','Contenuto',[['all','Tutti'],['summary','Con sintesi'],['ai','Con analisi automatica']]);
  const year=select('register-year-filter','Anno',[['all','Tutti'],['2025','2025']]);
  const dialog=make('dialog'),pager=make('div');document.body.append(controls,pager,dialog);
  const records=Array.from({length:30},(_,i)=>({id:'CAND-'+i,title:'Title '+i}));
  let view={...api.readView(initial)},reader,revealed=null,filtered=records;
  function openPaper(record){
    const bar=make('div'),body=make('div'),title=make('h2',record.title,'paper-sheet-title');
    bar.className='paper-sheet-bar';bar.append(make('span','Archivio'),make('button','Chiudi'));
    body.className='paper-sheet-body';
    for(const className of ['paper-support','paper-research','sheet-provenance']){const section=make(className==='sheet-provenance'?'details':'section');section.className=className;body.append(section);}
    body.insertBefore(title,body.firstChild);dialog.replaceChildren(bar,body);dialog.open=true;reader.sheetOpened(record);
  }
  reader=api.attach({controls,pager,dialog,getState:()=>view,applyState:state=>{view={...state};return[];},getRecords:()=>records,getResults:()=>filtered,openPaper,
    revealPaper:id=>{revealed=id;const i=filtered.findIndex(r=>r.id===id);if(i>=0)view.page=Math.floor(i/25)+1;}});
  dialog.addEventListener('close',()=>reader.sheetClosed());
  return {api,document,dialog,controls,search,mode,year,records,reader,history,location,stack,openPaper,make,
    get revealed(){return revealed;},get view(){return view;},setResults:rows=>filtered=rows};
}
const tick=()=>new Promise(resolve=>setTimeout(resolve,0));

test('search combines words across recorded fields and handles accents, apostrophes and candidate IDs',()=>{
  const {api}=setup();const record=Object.freeze({id:'CAND-2025-A',title:'Économie légale',authors:'D’Ámico',year:2025,doi:'10.1234/test'});
  for(const query of ['legale economIE',"d'amico economie",'CAND-2025-A','2025 10.1234/test',''])assert.equal(api.searchMatches(record,query),true,query);
  assert.equal(api.searchMatches(record,'economie missing'),false);
});

test('navigation respects filtered order, excludes lookalikes, and never wraps at either end',()=>{
  const {api,records}=setup();const results=[records[5],records[2],records[20]];
  assert.equal(api.neighbours(results,'CAND-2').previous.id,'CAND-5');
  assert.equal(api.neighbours(results,'CAND-2').next.id,'CAND-20');
  assert.equal(api.neighbours(results,'CAND-5').previous,null);
  assert.equal(api.neighbours(results,'CAND-20').next,null);
  const outside=api.neighbours(results,'CAND-200');assert.equal(outside.index,-1);assert.equal(outside.next,null);assert.equal(outside.previous,null);
});

test('sequential reading is one history entry and closing reveals the last paper across pages',async()=>{
  const t=setup();await tick();t.openPaper(t.records[24]);
  t.dialog.querySelector('.sheet-next').fire('click');
  assert.equal(new URL(t.location.href).searchParams.get('paper'),'CAND-25');
  assert.equal(t.stack.length,2);assert.equal(t.history.state.cilePaper,true);
  t.dialog.close();await tick();
  assert.equal(t.revealed,'CAND-25');assert.equal(t.view.page,2);
  assert.equal(new URL(t.location.href).searchParams.get('paper'),null);
  assert.equal(new URL(t.location.href).searchParams.get('page'),'2');
  t.history.forward();assert.equal(t.dialog.open,true);assert.equal(t.dialog.querySelector('#paper-sheet-title').textContent,'Title 25');
});

test('browser Back closes and Forward restores the selected paper without a close-event race',async()=>{
  const t=setup();await tick();t.openPaper(t.records[4]);t.dialog.querySelector('.sheet-next').fire('click');
  t.history.back();await tick();assert.equal(t.dialog.open,false);assert.equal(t.revealed,'CAND-5');
  t.history.forward();await tick();assert.equal(t.dialog.open,true);assert.equal(t.stack.length,2);
  assert.equal(new URL(t.location.href).searchParams.get('paper'),'CAND-5');
});

test('a direct paper link can navigate and close without leaving the site',async()=>{
  const t=setup(base+'?paper=CAND-5');await tick();assert.equal(t.dialog.open,true);
  t.dialog.querySelector('.sheet-next').fire('click');assert.equal(t.history.state.cilePaper,false);
  t.dialog.close();await tick();assert.equal(t.stack.length,1);assert.equal(t.location.href,base);assert.equal(t.revealed,'CAND-6');
});

test('an outside-filter record stays readable without substituting a matching paper',async()=>{
  const t=setup(base+'?paper=CAND-5');t.setResults([t.records[1]]);await tick();
  assert.match(t.dialog.textContent,/Fuori dai risultati correnti/);
  assert.equal(t.dialog.querySelector('.sheet-next').disabled,true);assert.equal(t.dialog.querySelector('.sheet-previous').disabled,true);
  assert.equal(t.dialog.querySelector('#paper-sheet-title').textContent,'Title 5');
});

test('unknown deep links never open a nearest-match candidate',async()=>{
  const t=setup(base+'?paper=CAND-500');await tick();assert.notEqual(t.dialog.open,true);
  assert.match(t.controls.following.textContent,/non è presente nel registro/);
});

test('section navigation opens and focuses a disclosure; async additions keep unique stable IDs',async()=>{
  const t=setup();await tick();t.openPaper(t.records[0]);
  const research=t.dialog.querySelector('.paper-research'),support=t.dialog.querySelector('.paper-support');
  const researchId=research.id;
  const disclosure=t.make('details'),summary=t.make('summary','Metodi e dati');disclosure.append(summary);research.append(disclosure);
  const hidden=t.make('details');hidden.hidden=true;hidden.append(t.make('summary','Unavailable placeholder'));research.append(hidden);
  const source=t.make('details');source.append(t.make('summary','Accesso al testo'));support.append(source);
  t.reader.sheetUpdated();
  const nav=t.dialog.querySelector('.sheet-contents');
  const button=nav.querySelectorAll('button').find(n=>n.textContent==='Metodi e dati');button.fire('click');
  assert.equal(disclosure.open,true);assert.equal(t.document.activeElement,summary);assert.equal(disclosure.scrolled,true);
  assert.doesNotMatch(nav.textContent,/Unavailable placeholder/);assert.equal(research.id,researchId);
  const ids=t.dialog.querySelectorAll('*').map(n=>n.id).filter(Boolean);assert.equal(new Set(ids).size,ids.length);
  const mobile=nav.querySelector('select');mobile.value=source.id;mobile.fire('change');assert.equal(source.open,true);
});

test('quick views reuse the governed selector and removing one filter preserves the rest',async()=>{
  const t=setup();await tick();let changes=0;t.mode.addEventListener('change',()=>changes++);
  const quick=t.controls.querySelector('.register-quick-views');quick.querySelectorAll('button')[1].fire('click');
  assert.equal(t.mode.value,'summary');assert.equal(changes,1);
  t.year.value='2025';t.search.value='<script> mafia';t.reader.refreshFilters();
  const active=t.controls.querySelector('.register-filter-summary'),buttons=active.querySelectorAll('button');
  assert.equal(buttons.length,3);assert.equal(active.querySelector('script'),null);
  t.reader.refreshFilters();assert.equal(active.querySelectorAll('button')[0],buttons[0],'background refresh retains focused controls');
  buttons.find(n=>n.textContent.startsWith('Anno:')).fire('click');
  assert.equal(t.year.value,'all');assert.equal(t.mode.value,'summary');assert.equal(t.search.value,'<script> mafia');assert.equal(t.document.activeElement,t.search);
});

test('last-result navigation stays bounded and focus moves to the new title',async()=>{
  const t=setup();await tick();t.setResults([t.records[1],t.records[8]]);t.openPaper(t.records[1]);
  t.dialog.querySelector('.sheet-next').fire('click');
  assert.equal(t.dialog.querySelector('.sheet-next').disabled,true);
  assert.equal(t.document.activeElement,t.dialog.querySelector('#paper-sheet-title'));
});

test('late index updates change navigation without opening a stale neighbouring result',async()=>{
  const t=setup();await tick();t.openPaper(t.records[1]);
  t.setResults([t.records[1],t.records[20]]);t.reader.refreshResults();
  t.dialog.querySelector('.sheet-next').fire('click');
  assert.equal(t.dialog.querySelector('#paper-sheet-title').textContent,'Title 20');
  t.setResults([]);t.reader.refreshResults();
  assert.equal(t.dialog.querySelector('.sheet-previous').disabled,true);
  assert.match(t.dialog.textContent,/Fuori dai risultati correnti/);
});
