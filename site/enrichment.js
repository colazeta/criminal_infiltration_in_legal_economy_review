"use strict";
(() => {
  const $ = id => document.getElementById(id);
  let targets = [], generation = 0, documentUrl = null;
  function clearDocument(){if(documentUrl){URL.revokeObjectURL(documentUrl);documentUrl=null}}
  const el = (tag,text) => { const n=document.createElement(tag); if(text!==undefined)n.textContent=String(text);return n; };
  function message(text) { $("enrich-status").textContent=text; }
  async function api(path) {
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
    try {
      const response=await fetch('/api/paper-enrichment/'+path,{signal:controller.signal,headers:{Authorization:'Bearer '+(sessionStorage.getItem('criminal-infiltration-curator-session')||'')}});
      const data=await response.json();if(!response.ok)throw Error(data.error_code||data.error?.code||'HTTP '+response.status);return data;
    }finally{clearTimeout(timer);}
  }
  function table(parent,rows,fields) {
    if(!rows.length){parent.append(el('p','Nessun elemento registrato.'));return;}
    const t=el('table'),head=el('tr');for(const f of fields)head.append(el('th',f));t.append(head);
    for(const row of rows){const tr=el('tr');for(const f of fields)tr.append(el('td',row[f]??'—'));t.append(tr);}parent.append(t);
  }
  function fieldsFor(rows){
    const out=[];for(const row of rows||[]){if(!row||typeof row!=='object'||Array.isArray(row))continue;for(const key of Object.keys(row)){if(!out.includes(key))out.push(key);if(out.length>=16)return out;}}return out;
  }
  function dynamicTable(parent,rows,label) {
    const wrap=el('details'),summary=el('summary',label+' · '+(rows?.length||0));wrap.append(summary);
    if(!rows?.length){wrap.append(el('p','Nessuna riga conservata.'));parent.append(wrap);return;}
    const fields=fieldsFor(rows),t=el('table'),head=el('tr');for(const f of fields)head.append(el('th',f));t.append(head);
    for(const row of rows){const tr=el('tr');for(const f of fields){const value=row[f];tr.append(el('td',value&&typeof value==='object'?JSON.stringify(value):value??'—'));}t.append(tr);}wrap.append(t);parent.append(wrap);
  }
  function rawDetails(parent,label,value) {
    const d=el('details'),h=el('summary',label),pre=el('pre',JSON.stringify(value,null,2));d.append(h,pre);parent.append(d);return d;
  }
  async function renderPrivateProvenance(pane,id,serial) {
    const section=el('section');section.className='full-provenance';section.append(el('h2','Trasparenza completa · archivio privato'));
    section.append(el('p','Vista autenticata e read-only di ciò che il sistema ha conservato o eseguito per questo CandidateRecord. Nessun elemento in questa sezione equivale a una decisione scientifica.'));
    const status=el('p','Caricamento della provenienza privata…');section.append(status);pane.append(section);
    try{
      const data=await api('provenance?id='+encodeURIComponent(id));if(serial!==generation)return;
      status.textContent='Provenienza privata caricata. Le assenze restano assenze registrate, non zeri.';
      rawDetails(section,'Target corrente',data.target);
      dynamicTable(section,data.inputs,'Input/versioni osservate');
      dynamicTable(section,data.jobs,'Job pianificati o eseguiti');
      dynamicTable(section,data.attempts,'Tentativi effettivi');
      dynamicTable(section,data.runs,'Run collegate');
      dynamicTable(section,data.sources,'Fonti conservate · metadati e storage');
      dynamicTable(section,data.proposals,'Proposte di estrazione · payload originali');
      dynamicTable(section,data.citation_coverage,'Copertura citazioni');
      dynamicTable(section,data.citation_counts,'Conteggi citazioni');
      dynamicTable(section,data.documents,'Documenti conservati');
      dynamicTable(section,data.bibliography,'Snapshot bibliografici');
      dynamicTable(section,data.adjudication,'Receipt di adjudication');
      dynamicTable(section,data.calibration,'Receipt di calibrazione');
      const annotations=el('details'),annotationSummary=el('summary','Annotazioni private · '+(data.annotations?.length||0));annotations.append(annotationSummary);
      if(!data.annotations?.length)annotations.append(el('p','Nessuna annotazione privata candidate-bound è conservata per questo paper.'));
      for(const a of data.annotations||[]){
        const card=el('section');card.append(el('h3','Annotazione · '+a.annotation_id),el('p','binding='+a.binding_state+' · head='+String(a.head_state||'—')+' · versione='+String(a.record_version||'—')+' · importata '+a.imported_at));
        rawDetails(card,'Grafo parsato',a.graph);dynamicTable(card,a.events,'Eventi di revisione');rawDetails(card,'Receipt di integrità',a.receipt);
        const original=el('div'),button=el('button','Apri originale conservato');button.type='button';
        button.addEventListener('click',async()=>{button.disabled=true;try{const detail=await api('annotation?id='+encodeURIComponent(id)+'&annotation='+encodeURIComponent(a.annotation_id));if(serial!==generation)return;original.replaceChildren();rawDetails(original,'Commento originale conservato',detail.source);rawDetails(original,'Issue padre conservata',detail.issue);rawDetails(original,'Head corrente',detail.head);dynamicTable(original,detail.events,'Storia eventi');original.append(el('p',detail.transparency_note||''));}catch(e){message(e.message)}finally{button.disabled=false}});
        card.append(button,original);annotations.append(card);
      }
      section.append(annotations);
      rawDetails(section,'Envelope completo restituito dal backend',data);
    }catch(e){status.textContent='Provenienza privata non verificabile: '+e.message;}
  }
  function list() {
    const query=$("enrich-filter").value.toLowerCase();
    $("enrich-candidates").replaceChildren(...targets.filter(t=>t.record.title.toLowerCase().includes(query)).map(t=>{
      const b=el('button',t.record.title);b.addEventListener('click',()=>open(t.target_id));return b;
    }));
  }
  async function refresh() {
    clearDocument();const serial=++generation;
    message('Caricamento dei dati…');
    try {
      const state=await api('status');const data=await api('targets');if(serial!==generation)return;
      targets=data.targets.map(t=>({...t,record:JSON.parse(t.record_json)}));list();
      const requested=new URL(location.href).searchParams.get('candidate');
      if(requested){const selected=targets.find(t=>t.record_id===requested||t.record.id===requested);if(selected){await open(selected.target_id);return}}
      $("enrich-scope").textContent=state.enabled?'Acquisizione meccanica abilitata':'Acquisizione meccanica disabilitata';
      const pane=$("enrich-detail");pane.replaceChildren(el('h1','Stato dell’arricchimento'),el('p','Consulta le lavorazioni e le analisi già registrate. Le proposte restano distinte dalle decisioni scientifiche.'));
      if(state.scheduling){pane.append(el('h2','Iterazioni pianificate'),el('p','Slot previsti distinti dalle esecuzioni effettive. Le iterazioni in attesa non vengono cancellate.'));
        table(pane,state.scheduling.totals,['status','count']);
        table(pane,state.scheduling.iterations.map(r=>({...r,scheduled_at:new Date(r.scheduled_at).toISOString(),materialised_at:new Date(r.materialised_at).toISOString(),started_at:r.started_at?new Date(r.started_at).toISOString():'—',finished_at:r.finished_at?new Date(r.finished_at).toISOString():'—'})),['scheduled_at','materialised_at','started_at','finished_at','status','attempts','error_code']);}
      table(pane,state.jobs,['kind','status','count']);pane.append(el('h2','Ultime esecuzioni'));table(pane,state.runs,['scheduled_slot','status','selected_job_id','error_code']);
      message(targets.length+' paper nel registro privato. I dati delle lavorazioni non indicano l’inclusione nel corpus.');
    }catch(e){$("enrich-detail").replaceChildren(el('h1','Accesso o configurazione richiesti'),el('p','Accedi dalla console curatoriale. Un archivio privato non disponibile resta un blocco esplicito.'));message(e.message);}
  }
  async function open(id) {
    clearDocument();const serial=++generation;
    message('Caricamento dei dati…');
    try {
      const data=await api('target?id='+encodeURIComponent(id));if(serial!==generation)return;
      const pane=$("enrich-detail");pane.replaceChildren(el('h1',JSON.parse(data.target.record_json).title),el('p','Analisi proposte da revisionare. Le fonti originali restano private.'));
      pane.append(el('h2','Lavorazioni'));table(pane,data.jobs,['kind','status','error_code','due_at']);
      pane.append(el('h2','Fonti'));
      for(const source of data.sources){const b=el('button',source.evidence_kind+' · '+source.provider);const text=el('pre');b.addEventListener('click',async()=>{try{const s=await api('source?id='+encodeURIComponent(id)+'&source='+encodeURIComponent(source.source_id));if(serial===generation)text.textContent=s.text;}catch(e){message(e.message);}});pane.append(b,text);}
      pane.append(el('h2','PDF conservati'));
      const documentPane=el('section');pane.append(documentPane);
      try{const listing=await api('documents?id='+encodeURIComponent(id));if(serial!==generation)return;
        if(!listing.documents.length)documentPane.append(el('p','Nessun PDF originale conservato per questa versione. Un collegamento esterno non è una copia archiviata.'));
        for(const d of listing.documents){const button=el('button','Leggi PDF · '+d.version_label+' · '+d.visibility),viewer=el('div');
          button.addEventListener('click',async()=>{button.disabled=true;try{const response=await fetch('/api/paper-enrichment/document?id='+encodeURIComponent(id)+'&document='+d.document_id,{headers:{Authorization:'Bearer '+(sessionStorage.getItem('criminal-infiltration-curator-session')||'')}});if(!response.ok||!response.headers.get('Content-Type')?.startsWith('application/pdf'))throw Error('PDF non disponibile');const blob=await response.blob();if(serial!==generation)return;clearDocument();documentUrl=URL.createObjectURL(blob);const frame=el('iframe');frame.title='PDF originale conservato';frame.src=documentUrl;frame.className='enrichment-pdf-viewer';const link=el('a','Apri il PDF conservato in una nuova scheda');link.href=documentUrl;link.target='_blank';link.rel='noopener';viewer.replaceChildren(link,frame);}catch(e){message(e.message)}finally{button.disabled=false}});
          documentPane.append(button,el('p',d.attribution+' · '+d.licence_status+' · '+d.byte_length+' byte · SHA-256 '+d.pdf_sha256),viewer);
        }
      }catch(e){documentPane.append(el('p','Stato dei PDF non verificabile: '+e.message))}
      pane.append(el('h2','Proposte di estrazione'));
      if(!data.proposals.length)pane.append(el('p','Nessuna proposta registrata per questa versione del paper.'));
      for(const p of data.proposals){
        const proposal=JSON.parse(p.payload_json),card=el('section');card.append(el('h3','Scheda proposta · '+p.created_at),el('p','Copertura della fonte: '+proposal.source_coverage+' · Proposta da revisionare scientificamente'));
        const value=f=>f?.value??'Non verificabile dalla fonte disponibile';
        const facts=['summary','research_question','contribution','infiltration_definition','infiltration_operationalisation','authors_limitations','analyst_limitations'].map(k=>({campo:k,contenuto:value(proposal[k]),stato:proposal[k]?.status,evidenze:(proposal[k]?.evidence_span_ids||[]).join(', ')}));
        table(card,facts,['campo','contenuto','stato','evidenze']);
        for(const [label,key] of [['Studi','studies'],['Dati','datasets'],['Analisi e metodi','analyses'],['Variabili','variable_uses'],['Risultati','findings']]){
          card.append(el('h4',label));for(const item of proposal[key]||[])table(card,Object.entries(item).filter(([,f])=>f&&typeof f==='object'&&!Array.isArray(f)).map(([k,f])=>({campo:k,contenuto:value(f),stato:f.status,evidenze:(f.evidence_span_ids||[]).join(', ')})),['campo','contenuto','stato','evidenze']);
          if(!(proposal[key]||[]).length)card.append(el('p','Nessun elemento estratto; non equivale ad assenza nel paper completo.'));
        }
        card.append(el('h4','Posizionamento nel framework'),el('p',(proposal.framework.primary||proposal.framework.status)+' — '+value(proposal.framework.rationale)));
        const d=el('details'),h=el('summary','Dettagli tecnici e provenienza · '+p.proposal_id),pre=el('pre',JSON.stringify(proposal,null,2));d.append(h,pre);card.append(d);pane.append(card);
      }
      await renderPrivateProvenance(pane,id,serial);if(serial!==generation)return;
      pane.append(el('h2','Relazioni di citazione'),el('p','Identificatori restituiti dal provider, non nuove pubblicazioni incluse. Ogni snapshot ha copertura separata; gli stessi collegamenti possono ricomparire in snapshot diversi.'));
      const graph=el('div'),more=el('button','Carica relazioni');let offset=0;
      more.addEventListener('click',async()=>{more.disabled=true;try{const d=await api('citations?id='+encodeURIComponent(id)+'&offset='+offset);if(serial!==generation)return;table(graph,d.edges,['direction','citing_identifier','cited_identifier','snapshot_id']);if(offset===0)table(graph,d.coverage,['direction','status','returned_count','provider_count','observed_at']);offset=d.next_offset;more.hidden=offset===null;}catch(e){message(e.message);}finally{more.disabled=false;}});pane.append(more,graph);message(data.target.record_id);
    }catch(e){message(e.message);}
  }
  window.addEventListener('pagehide',clearDocument);
  $("enrich-refresh").addEventListener('click',refresh);$("enrich-filter").addEventListener('input',list);refresh();
})();
