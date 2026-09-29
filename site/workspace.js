/* Read-only navigation and sharing. URL state is presentation, never research data. */
(() => {
  'use strict';
  const DEFAULTS = {query:'',year:'all',author:'all',venue:'all',review:'all',access:'all',sort:'newest',content:'all',category:'all',page:1,size:25,paper:''};
  const PARAMS = {query:'q',year:'year',author:'author',venue:'venue',review:'review',access:'access',sort:'sort',content:'content',category:'category',page:'page',size:'size',paper:'paper'};
  const clean = value => typeof value==='string' && value.length<=600 && !/[\u0000-\u001f\u007f]/.test(value) ? value : '';
  function readView(value) {
    const url=new URL(value), result={...DEFAULTS};
    for(const [key,param] of Object.entries(PARAMS)) {
      if(url.searchParams.getAll(param).length!==1)continue;
      const text=clean(url.searchParams.get(param));
      if(!text)continue;
      if(key==='page') {if(/^[1-9]\d{0,4}$/.test(text))result.page=Number(text);}
      else if(key==='size') {if(['25','50','100'].includes(text))result.size=Number(text);}
      else result[key]=text;
    }
    return result;
  }
  function viewURL(base, view) {
    const url=new URL(base);url.search='';url.hash='';
    for(const [key,param] of Object.entries(PARAMS)) {
      const value=view[key]??DEFAULTS[key];
      if(value!==DEFAULTS[key] && clean(String(value)))url.searchParams.set(param,String(value));
    }
    return url;
  }
  function paperURL(base, id) {return viewURL(new URL('./',base),{paper:id}).href;}
  function reference(record) {
    // Preserve recorded bibliography; do not infer initials, pages, issue or publication type.
    return [record.authors,record.year?`(${record.year})`:null,record.title,record.venue,record.doi?`DOI: ${record.doi}`:null].filter(Boolean).join(' · ');
  }
  const fold = value => String(value || '').normalize('NFKD').replace(/\p{M}/gu,'').toLocaleLowerCase('it').replace(/[’‘]/g,"'");
  function searchMatches(record, query) {
    const text=fold([record.id,record.title,record.authors,record.doi,record.year,record.venue,record.topicCode].join(' '));
    return fold(query).trim().split(/\s+/).every(word=>text.includes(word));
  }
  function neighbours(records,id) {
    const index=records.findIndex(record=>record.id===id);
    return {index,total:records.length,previous:index>0?records[index-1]:null,next:index>=0?records[index+1]||null:null};
  }
  const el=(tag,text)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;return node;};
  function mountFilters(controls) {
    const quick=el('div');quick.className='register-quick-views';quick.setAttribute('role','group');quick.setAttribute('aria-label','Viste rapide del registro');
    quick.append(el('span','Leggi:'));
    const mode=controls.querySelector('#register-processing-filter');
    const buttons=[];
    if(mode)for(const [value,label] of [['all','Tutti i contenuti'],['summary','Con sintesi'],['ai','Con analisi automatica']]) {
      const button=el('button',label);button.type='button';
      button.addEventListener('click',()=>{mode.value=value;mode.dispatchEvent(new Event('change',{bubbles:true}));});
      quick.append(button);buttons.push([button,value]);
    }
    quick.hidden=!mode;
    const active=el('div');active.className='register-filter-summary';active.setAttribute('role','group');active.setAttribute('aria-label','Filtri attivi, seleziona per rimuovere');
    const drawer=controls.querySelector('#register-filter-panel');controls.insertBefore(quick,drawer);controls.append(active);
    let signature='';
    function refresh() {
      buttons.forEach(([button,value])=>button.setAttribute('aria-pressed',String(mode.value===value)));
      const entries=[];
      const search=controls.querySelector('#register-search');
      if(search?.value.trim())entries.push([search,'Ricerca: '+search.value,'']);
      for(const select of controls.querySelectorAll('.register-filter-grid select')) {
        if(select.value==='all')continue;
        const label=select.closest('label')?.querySelector('span')?.textContent||'Filtro';
        const option=[...select.options].find(option=>option.value===select.value);
        entries.push([select,label+': '+(option?.textContent||select.value),'all']);
      }
      const nextSignature=JSON.stringify(entries.map(([,label])=>label));
      if(signature===nextSignature)return;
      signature=nextSignature;active.replaceChildren();active.hidden=!entries.length;
      if(entries.length)active.append(el('span','Filtri attivi:'));
      for(const [control,label,value] of entries) {
        const button=el('button',label+' ×');button.type='button';button.setAttribute('aria-label','Rimuovi filtro '+label);
        button.addEventListener('click',()=>{
          control.value=value;control.dispatchEvent(new Event(control===search?'input':'change',{bubbles:true}));
          search.focus();
        });active.append(button);
      }
    }
    refresh();return refresh;
  }
  function contents(dialog) {
    const body=dialog.querySelector('.paper-sheet-body'),layout=el('div');layout.className='sheet-layout';
    const nav=el('nav');nav.className='sheet-contents';nav.setAttribute('aria-label','Indice della scheda');
    nav.append(el('strong','In questa scheda'));
    const select=el('select');select.setAttribute('aria-label','Vai a una sezione della scheda');
    const list=el('ol');nav.append(select,list);
    body.parentNode.insertBefore(layout,body);layout.append(nav,body);
    let targets=[],nextId=0;
    function go(node) {
      if(!node || !dialog.open)return;
      if(node.tagName==='DETAILS')node.open=true;
      const target=node.tagName==='DETAILS'?node.querySelector('summary'):node;
      target.tabIndex=-1;target.focus({preventScroll:true});node.scrollIntoView({block:'start'});
    }
    select.addEventListener('change',()=>go(targets.find(item=>item.node.id===select.value)?.node));
    function refresh() {
      targets=[{node:body.querySelector('#paper-sheet-title'),label:'Titolo e riferimento'}];
      for(const [selector,label] of [['.paper-support','Abstract e sintesi'],['.paper-research','Contesto della ricerca']]) {
        const node=body.querySelector(selector);if(!node)continue;
        targets.push({node,label});
        for(const child of node.children)if(child.tagName==='DETAILS'&&!child.hidden)targets.push({node:child,label:child.querySelector('summary')?.textContent||label});
      }
      targets.push({node:body.querySelector('.sheet-provenance'),label:'Identità e fonti del registro'});
      targets=targets.filter(item=>item.node);
      const selected=select.value;list.replaceChildren();select.replaceChildren();
      const placeholder=el('option','Vai alla sezione…');placeholder.value='';select.append(placeholder);
      targets.forEach(({node,label})=>{
        if(!node.id)node.id='sheet-section-'+(++nextId);
        const item=el('li'),button=el('button',label);button.type='button';button.setAttribute('aria-controls',node.id);
        button.addEventListener('click',()=>go(node));item.append(button);list.append(item);
        const option=el('option',label);option.value=node.id;select.append(option);
      });
      select.value=targets.some(item=>item.node.id===selected)?selected:'';
    }
    refresh();return refresh;
  }
  function revealHash() {
    let target;
    try {target=document.getElementById(decodeURIComponent(location.hash.slice(1)));}catch{return;}
    if(!target)return;
    let node=target;
    while(node){if(node.tagName==='DETAILS')node.open=true;node=node.parentElement;}
    if(target.tagName==='DETAILS')target.querySelector('summary')?.focus({preventScroll:true});
    target.scrollIntoView({block:'start'});
  }
  function attach({controls,pager,dialog,getState,applyState,getRecords,getResults=getRecords,openPaper,revealPaper=()=>{},resultScope=()=>''}) {
    let restoring=false,timer=null,activePaper='',pendingReturn='',printState=[],refreshContents=()=>{},refreshNavigation=()=>{};
    const refreshFilters=mountFilters(controls);
    const message=document.createElement('p');message.id='workspace-status';message.setAttribute('role','status');message.hidden=true;
    controls.after(message);
    const notify=text=>{message.textContent=text;message.hidden=!text;};
    function save(method='replaceState',paper=dialog.open?activePaper:'') {
      if(restoring)return;
      const url=viewURL(location.href,{...getState(),paper});
      if(url.href===location.href)return;
      const cilePaper=Boolean(paper)&&(method==='pushState'||Boolean(history.state?.cilePaper));
      try{history[method]({cilePaper},'',url);}catch{notify('La vista resta consultabile, ma il browser non ha consentito di aggiornare il link.');}
    }
    function changed(event) {
      if(restoring)return;
      clearTimeout(timer);
      // Wait for existing filter/reset handlers; never add one history entry per key.
      timer=setTimeout(()=>save(event.type==='input'?'replaceState':'pushState'),event.type==='input'?160:0);
    }
    controls.addEventListener('input',changed);controls.addEventListener('change',changed);controls.addEventListener('reset',changed);
    pager.addEventListener('click',event=>{if(event.target.closest('button'))changed(event);});
    pager.addEventListener('change',changed);
    function restore() {
      clearTimeout(timer);restoring=true;notify('');
      let returned=false;
      try {
        const view=readView(location.href),ignored=applyState(view);
        if(ignored.length)notify('Alcuni filtri del link non sono disponibili nel registro corrente: '+ignored.join(', ')+'.');
        const record=getRecords().find(row=>row.id===view.paper);
        if(view.paper && record) {
          if(!dialog.open || activePaper!==record.id)openPaper(record);
        } else {
          const returnId=activePaper||pendingReturn;activePaper='';pendingReturn='';
          if(dialog.open)dialog.close();
          if(returnId){revealPaper(returnId);returned=true;}
          if(view.paper)notify('Il paper indicato dal link non è presente nel registro corrente. Nessun altro record è stato sostituito.');
        }
      } finally {restoring=false;}
      if(returned)save('replaceState','');
    }
    async function copy(value,feedback,container) {
      const current=activePaper;
      try {
        if(!navigator.clipboard?.writeText)throw Error('clipboard_unavailable');
        await navigator.clipboard.writeText(value);
        if(dialog.open && activePaper===current)feedback.textContent='Copiato negli appunti.';
      } catch {
        if(!dialog.open || activePaper!==current)return;
        feedback.textContent='Copia automatica non disponibile. Seleziona e copia il testo nel riquadro.';
        let field=container.querySelector('textarea');
        if(!field){field=document.createElement('textarea');field.readOnly=true;field.rows=3;field.setAttribute('aria-label','Testo da copiare');container.append(field);}
        field.value=value;field.focus();field.select();
      }
    }
    function sheetOpened(record) {
      const continuing=Boolean(activePaper);
      activePaper=record.id;document.body.classList.add('paper-sheet-open');
      const nav=el('div');nav.className='sheet-result-navigation';nav.setAttribute('role','group');nav.setAttribute('aria-label','Naviga nei risultati');
      const position=el('span');position.setAttribute('role','status');
      const move=direction=>{
        const target=neighbours(getResults(),record.id)[direction];
        if(!target)return;
        openPaper(target);
        const button=dialog.querySelector('.sheet-'+direction);
        if(button&&!button.disabled)button.focus();else dialog.querySelector('#paper-sheet-title')?.focus();
      };
      const directions=[];
      for(const [direction,label] of [['previous','← Precedente'],['next','Successivo →']]) {
        const button=el('button',label);button.type='button';button.className='sheet-'+direction;
        button.setAttribute('aria-label',direction==='previous'?'Paper precedente':'Paper successivo');
        button.addEventListener('click',()=>move(direction));nav.append(button);directions.push([button,direction]);
      }
      refreshNavigation=()=>{
        const sequence=neighbours(getResults(),record.id);
        position.textContent=sequence.index<0?'Fuori dai risultati correnti':`${sequence.index+1} di ${sequence.total} risultati${resultScope()}`;
        for(const [button,direction] of directions){const target=sequence[direction];button.disabled=!target;button.title=target?.title||'';}
      };
      refreshNavigation();
      nav.insertBefore(position,nav.firstChild);
      const bar=dialog.querySelector('.paper-sheet-bar');bar.insertBefore(nav,bar.lastChild);
      const body=dialog.querySelector('.paper-sheet-body'),tools=document.createElement('div');tools.className='research-tools sheet-actions';
      const feedback=document.createElement('p');feedback.className='sheet-action-feedback';feedback.setAttribute('role','status');
      const link=document.createElement('a');link.href=paperURL(location.href,record.id);link.textContent='Link diretto alla scheda';tools.append(link);
      for(const [label,value] of [['Copia link',link.href],['Copia riferimento',reference(record)]]) {
        const button=document.createElement('button');button.type='button';button.textContent=label;
        button.addEventListener('click',()=>copy(value,feedback,tools));tools.append(button);
      }
      const print=document.createElement('button');print.type='button';print.textContent='Stampa scheda';print.addEventListener('click',()=>window.print());tools.append(print);
      const note=document.createElement('p');note.className='sheet-action-note';note.textContent='Il riferimento riproduce i metadati del registro: non è una verifica bibliografica.';
      const before=body.querySelector('.paper-support');body.insertBefore(tools,before);body.insertBefore(note,before);body.insertBefore(feedback,before);
      refreshContents=contents(dialog);
      clearTimeout(timer);
      if(!readView(location.href).paper)save('replaceState','');
      save(continuing?'replaceState':'pushState',record.id);
    }
    function sheetClosed() {
      document.body.classList.remove('paper-sheet-open');
      if(restoring || !readView(location.href).paper){activePaper='';return;}
      const returnId=activePaper;activePaper='';
      // Back closes a user-opened sheet; a direct arrival must never leave the site.
      if(history.state?.cilePaper){pendingReturn=returnId;history.back();}
      else {revealPaper(returnId);save('replaceState','');}
    }
    window.addEventListener('popstate',restore);
    window.addEventListener('beforeprint',()=>{
      if(!dialog.open)return;
      printState=[...dialog.querySelectorAll('details')].map(node=>[node,node.open]);
      printState.forEach(([node])=>{node.open=true;});
    });
    window.addEventListener('afterprint',()=>{printState.forEach(([node,open])=>{if(node.isConnected)node.open=open;});printState=[];});
    queueMicrotask(restore);
    return {sheetOpened,sheetClosed,refreshFilters,refreshResults:()=>{if(dialog.open)refreshNavigation();},sheetUpdated:()=>refreshContents()};
  }
  globalThis.CILEWorkspace={readView,viewURL,paperURL,reference,searchMatches,neighbours,mountFilters,contents,attach};
  if(typeof window!=='undefined') {
    window.addEventListener('hashchange',revealHash);
    document.addEventListener('click',event=>{
      const anchor=event.target.closest('a[href^="#"]');
      if(anchor && anchor.hash===location.hash)queueMicrotask(revealHash);
    });
    if(location.hash)queueMicrotask(revealHash);
  }
})();
