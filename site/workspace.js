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
  function revealHash() {
    let target;
    try {target=document.getElementById(decodeURIComponent(location.hash.slice(1)));}catch{return;}
    if(!target)return;
    let node=target;
    while(node){if(node.tagName==='DETAILS')node.open=true;node=node.parentElement;}
    if(target.tagName==='DETAILS')target.querySelector('summary')?.focus({preventScroll:true});
    target.scrollIntoView({block:'start'});
  }
  function attach({controls,pager,dialog,getState,applyState,getRecords,openPaper}) {
    let restoring=false,timer=null,activePaper='',printState=[];
    const message=document.createElement('p');message.id='workspace-status';message.setAttribute('role','status');message.hidden=true;
    controls.after(message);
    const notify=text=>{message.textContent=text;message.hidden=!text;};
    function save(method='replaceState',paper=dialog.open?activePaper:'') {
      if(restoring)return;
      const url=viewURL(location.href,{...getState(),paper});
      if(url.href===location.href)return;
      try{history[method]({cilePaper:method==='pushState'&&Boolean(paper)},'',url);}catch{notify('La vista resta consultabile, ma il browser non ha consentito di aggiornare il link.');}
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
      try {
        const view=readView(location.href),ignored=applyState(view);
        if(ignored.length)notify('Alcuni filtri del link non sono disponibili nel registro corrente: '+ignored.join(', ')+'.');
        const record=getRecords().find(row=>row.id===view.paper);
        if(view.paper && record) {
          if(!dialog.open || activePaper!==record.id)openPaper(record);
        } else {
          if(dialog.open)dialog.close();
          activePaper='';
          if(view.paper)notify('Il paper indicato dal link non è presente nel registro corrente. Nessun altro record è stato sostituito.');
        }
      } finally {restoring=false;}
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
      activePaper=record.id;document.body.classList.add('paper-sheet-open');
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
      clearTimeout(timer);
      if(!readView(location.href).paper)save('replaceState','');
      save('pushState',record.id);
    }
    function sheetClosed() {
      document.body.classList.remove('paper-sheet-open');
      if(restoring || !readView(location.href).paper){activePaper='';return;}
      activePaper='';
      // Back closes a user-opened sheet; a direct arrival must never leave the site.
      if(history.state?.cilePaper)history.back();else save('replaceState','');
    }
    window.addEventListener('popstate',restore);
    window.addEventListener('beforeprint',()=>{
      if(!dialog.open)return;
      printState=[...dialog.querySelectorAll('details')].map(node=>[node,node.open]);
      printState.forEach(([node])=>{node.open=true;});
    });
    window.addEventListener('afterprint',()=>{printState.forEach(([node,open])=>{if(node.isConnected)node.open=open;});printState=[];});
    queueMicrotask(restore);
    return {sheetOpened,sheetClosed};
  }
  globalThis.CILEWorkspace={readView,viewURL,paperURL,reference,attach};
  if(typeof window!=='undefined') {
    window.addEventListener('hashchange',revealHash);
    document.addEventListener('click',event=>{
      const anchor=event.target.closest('a[href^="#"]');
      if(anchor && anchor.hash===location.hash)queueMicrotask(revealHash);
    });
    if(location.hash)queueMicrotask(revealHash);
  }
})();
