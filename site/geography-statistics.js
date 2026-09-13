/* Country statistics share the exact selected bibliometric population.
   Read-only public projections; no private APIs or persistent parallel store. */
import './paper-sheet-research.js';
(() => {
  'use strict';
  const anchor=document.querySelector('#bibliometric-quality-note');
  if(!anchor)return;
  const host=document.createElement('article');host.id='study-geography';host.className='bibliometric-panel';host.setAttribute('aria-label','Paesi e territori studiati');anchor.after(host);
  const stylesheet=document.createElement('link');stylesheet.rel='stylesheet';stylesheet.href='./geography.css';document.head.append(stylesheet);
  const API='https://criminal-infiltration-curator.colazeta-research.workers.dev/api/public-paper-research';
  const geo=globalThis.CILEPaperGeography, entries=new Map(), signatures=new Map();
  const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n};
  const note=el('p'),progress=el('p'),chart=el('div'),quality=el('div'),refresh=el('button','Aggiorna dati geografici');
  const format=new Intl.NumberFormat('it-IT',{maximumFractionDigits:1});
  const labels={pending:'Da verificare',error:'Errore di lettura o identità non verificabile',not_assessed:'Estrazione non ancora disponibile',not_registered:'Scheda analitica non associata',stale:'Estrazione non aggiornata',withheld:'Estrazione non pubblicabile',no_study:'Nessuno studio strutturato disponibile',not_reported:'Non riportato nella fonte consultata',not_verifiable:'Non verificabile dalla fonte consultata',not_applicable:'Non applicabile',ambiguous:'Geografia ambigua',unverified:'Geografia senza evidenza attribuita alla fonte',unresolved:'Territorio presente, paese non normalizzato',supranational:'Ambito sovranazionale senza elenco di paesi',global:'Ambito globale senza elenco di paesi',missing:'Geografia mancante',country:'Almeno un paese identificato'};
  let selected=[],running=false,failures=0;
  const signature=r=>JSON.stringify([r.id,r.title,r.doi||'', [...(r.sourceLinks||[])].sort()]);
  progress.setAttribute('role','status');progress.setAttribute('aria-live','polite');
  note.className='bibliometric-note';refresh.type='button';
  host.append(el('h3','Paesi e territori studiati'),note,refresh,progress,chart,quality);
  function render(){
    const data=geo.aggregate(selected,entries),checked=selected.filter(r=>entries.has(r.id)).length;
    note.textContent=`Ambito dell’analisi, non affiliazione degli autori. ${data.known} / ${data.total} record nella vista hanno almeno un paese identificabile dalle schede di ricerca correnti. Geografia estratta preliminare, non validata scientificamente. ${data.partial} di questi record hanno anche studi con copertura geografica non completamente normalizzata.`;
    progress.textContent=running?`Verifica delle schede: ${checked} / ${selected.length}. Conteggi provvisori durante il caricamento.`:checked<selected.length?`Verifica incompleta: ${checked} / ${selected.length}. I record non letti non valgono zero; usa “Aggiorna dati geografici” per riprovare.`:`Verificate ${checked} / ${selected.length} schede nella vista. La disponibilità della scheda non implica che il paese sia stato estratto.`;
    refresh.disabled=running||!selected.length;
    chart.replaceChildren();quality.replaceChildren();
    if(!data.rows.length){chart.append(el('p','Nessun paese conteggiabile nelle schede finora verificate. Non significa assenza di studi su quei paesi.'))}
    else{
      const table=el('table'),caption=el('caption','Record per paese o territorio — conteggio multiplo, una volta per record e paese'),head=el('thead'),tr=el('tr'),body=el('tbody');
      for(const text of ['Paese / territorio e paper','Record','Quota con paese noto','Volume relativo']){const th=el('th',text);th.scope='col';tr.append(th)}
      head.append(tr);table.append(caption,head,body);
      const maximum=Math.max(...data.rows.map(r=>r.count));
      for(const row of data.rows){
        const tr=el('tr'),name=el('th'),details=el('details'),list=el('ul');name.scope='row';details.append(el('summary',row.name));
        for(const paper of row.papers){const li=el('li');li.append(el('strong',paper.title));for(const study of paper.studies)li.append(el('p',`Studio ${study.number}: ${study.scope}`));li.append(el('small','Estrazione aggiornata: '+(paper.updatedAt||'non disponibile')));list.append(li)}
        details.append(list);name.append(details);
        const barCell=el('td'),track=el('span'),fill=el('span');track.className='bibliometric-bar-track';fill.className='bibliometric-bar-fill';fill.style.width=(row.count/maximum*100)+'%';track.setAttribute('aria-hidden','true');track.append(fill);barCell.append(track);
        tr.append(name,el('td',String(row.count)),el('td',format.format(row.count/data.known*100)+'%'),barCell);body.append(tr);
      }
      const scroll=el('div');scroll.className='table-scroll';scroll.append(table);chart.append(scroll);
    }
    quality.append(el('p','Ogni record conta una sola volta per ciascun paese, anche se contiene più studi nello stesso paese. La somma delle barre e delle percentuali può superare il totale e il 100%. Denominatore delle quote: record della vista con almeno un paese noto. I candidati restano record provvisori: eventuali duplicati bibliografici non riconciliati non sono fusi automaticamente.'));
    const details=el('details');details.append(el('summary','Copertura geografica e dati mancanti'));
    for(const state of data.states){const label=state.status.split(' / ').map(k=>labels[k]||k).join(' / ');details.append(el('p',`${label}: ${state.count}`))}
    details.append(el('p','Un’area come Europa non viene trasformata nell’elenco di tutti i suoi paesi. Città e regioni restano nella descrizione dello studio; senza un paese esplicito non viene aggiunta automaticamente la relativa giurisdizione. Le frasi ambigue restano visibili ma non alimentano le barre.'));
    quality.append(details);
  }
  async function read(record){
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
    try{
      const response=await fetch(API+'?id='+encodeURIComponent(record.id),{cache:'no-store',credentials:'omit',signal:controller.signal});
      if(!response.ok)throw Error('geography_unavailable');
      return geo.fromResearch(globalThis.CILEPaperResearch.selectRecord(await response.json(),record));
    }finally{clearTimeout(timer)}
  }
  async function scan(){
    if(running||!selected.length)return;
    running=true;failures=0;const claimed=new Set();render();
    async function worker(){
      while(failures<4){
        const record=selected.find(r=>!entries.has(r.id)&&!claimed.has(signature(r)));
        if(!record)return;
        const sig=signature(record);claimed.add(sig);
        let result;
        try{
          if(!/^CAND-[A-Za-z0-9-]{1,100}$/.test(record.id))result={status:'not_registered',countries:[],studies:[]};
          else result=await read(record);
          failures=0;
        }catch{result={status:'error',countries:[],studies:[]};failures++}
        // An old snapshot must never replace the geography of an edited record.
        if(signatures.get(record.id)===sig)entries.set(record.id,result);
        render();
      }
    }
    try{await Promise.all(Array.from({length:4},worker))}finally{running=false;render()}
  }
  function update(records){
    selected=[];const ids=new Set();
    for(const record of records||[]){
      if(!record||typeof record.id!=='string'||ids.has(record.id))continue;
      ids.add(record.id);selected.push(record);
      const sig=signature(record);if(signatures.get(record.id)!==sig)entries.delete(record.id);signatures.set(record.id,sig);
    }
    render();void scan();
  }
  refresh.addEventListener('click',()=>{if(running)return;for(const r of selected)entries.delete(r.id);void scan()});
  globalThis.addEventListener('cile:bibliometric-view',()=>update(globalThis.CILEBibliometricView));
  update(globalThis.CILEBibliometricView||[]);
})();
