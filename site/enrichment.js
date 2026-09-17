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
    if(!Array.isArray(rows)){parent.append(el('p','Dati non disponibili per questa sezione.'));return;}
    if(!rows.length){parent.append(el('p','Nessun elemento registrato in questa vista.'));return;}
    const t=el('table'),head=el('tr');for(const f of fields)head.append(el('th',f));t.append(head);
    for(const row of rows){const tr=el('tr');for(const f of fields)tr.append(el('td',row[f]??'—'));t.append(tr);}parent.append(t);
  }
  function list() {
    const query=$("enrich-filter").value.toLowerCase();
    $("enrich-candidates").replaceChildren(...targets.filter(t=>t.record.title.toLowerCase().includes(query)).map(t=>{
      const b=el('button',t.record.title);b.addEventListener('click',()=>open(t.target_id));return b;
    }));
  }
  async function refresh() {
    clearDocument();const serial=++generation;
    targets=[];list();message('Caricamento della vista riservata…');
    $("enrich-scope").textContent='Stato del servizio non ancora caricato';
    $("enrich-detail").replaceChildren(el('p','Caricamento dei dati…'));
    try {
      const state=await api('status');const data=await api('targets');if(serial!==generation)return;
      if(!Array.isArray(data.targets))throw Error('Elenco dei paper non disponibile');
      targets=data.targets.map(t=>({...t,record:JSON.parse(t.record_json)}));list();
      const requested=new URL(location.href).searchParams.get('candidate');
      if(requested){const selected=targets.find(t=>t.record_id===requested||t.record.id===requested);if(selected){await open(selected.target_id);return}}
      $("enrich-scope").textContent=state.enabled===true?'Acquisizione meccanica abilitata':state.enabled===false?'Acquisizione meccanica disabilitata':'Stato del servizio non disponibile';
      const pane=$("enrich-detail");pane.replaceChildren(el('h1','Stato dell’arricchimento'),el('p','Questa vista mostra le lavorazioni e le schede restituite dal servizio. Il completamento dell’analisi è distinto dalla validazione scientifica.'));
      if(state.scheduling){pane.append(el('h2','Esecuzioni pianificate'),el('p','Slot previsti distinti dalle esecuzioni effettive. Le iterazioni in attesa non vengono cancellate.'));
        table(pane,state.scheduling.totals,['status','count']);
        table(pane,state.scheduling.iterations.map(r=>({...r,scheduled_at:new Date(r.scheduled_at).toISOString(),materialised_at:new Date(r.materialised_at).toISOString(),started_at:r.started_at?new Date(r.started_at).toISOString():'—',finished_at:r.finished_at?new Date(r.finished_at).toISOString():'—'})),['scheduled_at','materialised_at','started_at','finished_at','status','attempts','error_code']);}
      table(pane,state.jobs,['kind','status','count']);pane.append(el('h2','Ultime esecuzioni'));table(pane,state.runs,['scheduled_slot','status','selected_job_id','error_code']);
      message(targets.length+' paper presenti nella vista riservata. Non è un conteggio delle analisi completate.');
    }catch(e){if(serial!==generation)return;$("enrich-detail").replaceChildren(el('h1','Accesso o configurazione richiesti'),el('p','Non è stato possibile caricare i dati. Controlla l’accesso dalla console curatoriale e riprova.'));message(e.message);}
  }
  async function open(id) {
    clearDocument();const serial=++generation;
    $("enrich-detail").replaceChildren(el('p','Caricamento della scheda…'));message('Caricamento della scheda…');
    try {
      const data=await api('target?id='+encodeURIComponent(id));if(serial!==generation)return;
      const pane=$("enrich-detail");pane.replaceChildren(el('h1',JSON.parse(data.target.record_json).title),el('p','Proposte di estrazione: la loro presenza non dimostra una validazione scientifica. Le fonti originali restano private.'));
      pane.append(el('h2','Lavorazioni'));table(pane,data.jobs,['kind','status','error_code','due_at']);
      pane.append(el('h2','Fonti'));
      for(const source of data.sources){const b=el('button',source.evidence_kind+' · '+source.provider);const text=el('pre');b.addEventListener('click',async()=>{try{const s=await api('source?id='+encodeURIComponent(id)+'&source='+encodeURIComponent(source.source_id));if(serial===generation)text.textContent=s.text;}catch(e){if(serial===generation)message(e.message);}});pane.append(b,text);}
      pane.append(el('h2','PDF conservati'));
      const documentPane=el('section');pane.append(documentPane);
      try{const listing=await api('documents?id='+encodeURIComponent(id));if(serial!==generation)return;
        if(!listing.documents.length)documentPane.append(el('p','Nessun PDF originale conservato per questa versione. Un collegamento esterno non è una copia archiviata.'));
        for(const d of listing.documents){const button=el('button','Leggi PDF · '+d.version_label+' · '+d.visibility),viewer=el('div');
          button.addEventListener('click',async()=>{button.disabled=true;try{const response=await fetch('/api/paper-enrichment/document?id='+encodeURIComponent(id)+'&document='+d.document_id,{headers:{Authorization:'Bearer '+(sessionStorage.getItem('criminal-infiltration-curator-session')||'')}});if(!response.ok||!response.headers.get('Content-Type')?.startsWith('application/pdf'))throw Error('PDF non disponibile');const blob=await response.blob();if(serial!==generation)return;clearDocument();documentUrl=URL.createObjectURL(blob);const frame=el('iframe');frame.title='PDF originale conservato';frame.src=documentUrl;frame.className='enrichment-pdf-viewer';const link=el('a','Apri il PDF conservato in una nuova scheda');link.href=documentUrl;link.target='_blank';link.rel='noopener';viewer.replaceChildren(link,frame);}catch(e){if(serial===generation)message(e.message)}finally{button.disabled=false}});
          documentPane.append(button,el('p',d.attribution+' · '+d.licence_status+' · '+d.byte_length+' byte · SHA-256 '+d.pdf_sha256),viewer);
        }
      }catch(e){documentPane.append(el('p','Stato dei PDF non verificabile: '+e.message))}
      pane.append(el('h2','Proposte di estrazione'));
      if(!data.proposals.length)pane.append(el('p','Nessuna proposta è restituita per questa scheda. Non è una ricostruzione di tutte le lavorazioni svolte.'));
      for(const p of data.proposals){
        const proposal=JSON.parse(p.payload_json),card=el('section');card.append(el('h3','Scheda proposta · '+p.created_at),el('p','Copertura della fonte: '+proposal.source_coverage+' · La presenza della proposta non attesta una validazione scientifica'));
        const value=f=>f?.value??({not_reported:'Non riportato nella fonte consultata',not_applicable:'Non applicabile',not_verifiable:'Non verificabile dalla fonte consultata',ambiguous:'Informazione ambigua'}[f?.status]||'Informazione non disponibile');
        const facts=['summary','research_question','contribution','infiltration_definition','infiltration_operationalisation','authors_limitations','analyst_limitations'].map(k=>({campo:k,contenuto:value(proposal[k]),stato:proposal[k]?.status,evidenze:(proposal[k]?.evidence_span_ids||[]).join(', ')}));
        table(card,facts,['campo','contenuto','stato','evidenze']);
        for(const [label,key] of [['Studi','studies'],['Dati','datasets'],['Analisi e metodi','analyses'],['Variabili','variable_uses'],['Risultati','findings']]){
          card.append(el('h4',label));for(const item of proposal[key]||[])table(card,Object.entries(item).filter(([,f])=>f&&typeof f==='object'&&!Array.isArray(f)).map(([k,f])=>({campo:k,contenuto:value(f),stato:f.status,evidenze:(f.evidence_span_ids||[]).join(', ')})),['campo','contenuto','stato','evidenze']);
          if(!(proposal[key]||[]).length)card.append(el('p','Nessun elemento estratto; non equivale ad assenza nel paper completo.'));
        }
        card.append(el('h4','Posizionamento nel framework'),el('p',(proposal.framework.primary||proposal.framework.status)+' — '+value(proposal.framework.rationale)));
        const d=el('details'),h=el('summary','Dati strutturati e provenance · '+p.proposal_id),pre=el('pre',JSON.stringify(proposal,null,2));d.append(h,pre);card.append(d);pane.append(card);
      }
      pane.append(el('h2','Relazioni di citazione'),el('p','Identificatori restituiti dal provider, non nuove pubblicazioni incluse. Ogni snapshot ha copertura separata; gli stessi collegamenti possono ricomparire in snapshot diversi.'));
      const graph=el('div'),more=el('button','Carica relazioni');let offset=0;
      more.addEventListener('click',async()=>{more.disabled=true;try{const d=await api('citations?id='+encodeURIComponent(id)+'&offset='+offset);if(serial!==generation)return;table(graph,d.edges,['direction','citing_identifier','cited_identifier','snapshot_id']);if(offset===0)table(graph,d.coverage,['direction','status','returned_count','provider_count','observed_at']);offset=d.next_offset;more.hidden=offset===null;}catch(e){if(serial===generation)message(e.message);}finally{more.disabled=false;}});pane.append(more,graph);message(data.target.record_id);
    }catch(e){if(serial===generation){$("enrich-detail").replaceChildren(el('p','Non è stato possibile caricare la scheda. Riprova.'));message(e.message);}}
  }
  window.addEventListener('pagehide',clearDocument);
  $("enrich-refresh").addEventListener('click',refresh);$("enrich-filter").addEventListener('input',list);refresh();
})();
