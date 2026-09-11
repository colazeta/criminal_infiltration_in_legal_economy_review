"use strict";
(() => {
  const $ = id => document.getElementById(id);
  let targets = [], generation = 0;
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
  function list() {
    const query=$("enrich-filter").value.toLowerCase();
    $("enrich-candidates").replaceChildren(...targets.filter(t=>t.record.title.toLowerCase().includes(query)).map(t=>{
      const b=el('button',t.record.title);b.addEventListener('click',()=>open(t.target_id));return b;
    }));
  }
  async function refresh() {
    const serial=++generation;
    try {
      const state=await api('status');const data=await api('targets');if(serial!==generation)return;
      targets=data.targets.map(t=>({...t,record:JSON.parse(t.record_json)}));list();
      $("enrich-scope").textContent=state.enabled?'Acquisizione meccanica abilitata':'Acquisizione meccanica disabilitata';
      const pane=$("enrich-detail");pane.replaceChildren(el('h1','Stato dell’arricchimento'),el('p','Estrazione scientifica automatica non attiva: calibrazione del modello ancora necessaria. Le proposte non sono decisioni approvate.'));
      if(state.scheduling){pane.append(el('h2','Iterazioni orarie alle :40'),el('p','Slot previsti distinti dalle esecuzioni effettive. Le iterazioni in attesa non vengono cancellate.'));
        table(pane,state.scheduling.totals,['status','count']);
        table(pane,state.scheduling.iterations.map(r=>({...r,scheduled_at:new Date(r.scheduled_at).toISOString(),materialised_at:new Date(r.materialised_at).toISOString(),started_at:r.started_at?new Date(r.started_at).toISOString():'—',finished_at:r.finished_at?new Date(r.finished_at).toISOString():'—'})),['scheduled_at','materialised_at','started_at','finished_at','status','attempts','error_code']);}
      table(pane,state.jobs,['kind','status','count']);pane.append(el('h2','Ultime esecuzioni'));table(pane,state.runs,['scheduled_slot','status','selected_job_id','error_code']);
      message(targets.length+' paper privati in coda · Il pianificatore e la qualità scientifica sono verifiche separate.');
    }catch(e){$("enrich-detail").replaceChildren(el('h1','Accesso o configurazione richiesti'),el('p','Accedi dalla console curatoriale. Un archivio privato non disponibile resta un blocco esplicito.'));message(e.message);}
  }
  async function open(id) {
    const serial=++generation;
    try {
      const data=await api('target?id='+encodeURIComponent(id));if(serial!==generation)return;
      const pane=$("enrich-detail");pane.replaceChildren(el('h1',JSON.parse(data.target.record_json).title),el('p','Proposte non approvate. Le fonti originali restano private.'));
      pane.append(el('h2','Lavorazioni'));table(pane,data.jobs,['kind','status','error_code','due_at']);
      pane.append(el('h2','Fonti'));
      for(const source of data.sources){const b=el('button',source.evidence_kind+' · '+source.provider);const text=el('pre');b.addEventListener('click',async()=>{try{const s=await api('source?id='+encodeURIComponent(id)+'&source='+encodeURIComponent(source.source_id));if(serial===generation)text.textContent=s.text;}catch(e){message(e.message);}});pane.append(b,text);}
      pane.append(el('h2','Proposte di estrazione'));
      if(!data.proposals.length)pane.append(el('p','Nessuna proposta: non è stata eseguita un’estrazione scientifica.'));
      for(const p of data.proposals){
        const proposal=JSON.parse(p.payload_json),card=el('section');card.append(el('h3','Scheda proposta · '+p.created_at),el('p','Copertura della fonte: '+proposal.source_coverage+' · Verifica scientifica non approvata'));
        const value=f=>f?.value??'Non verificabile dalla fonte disponibile';
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
      more.addEventListener('click',async()=>{more.disabled=true;try{const d=await api('citations?id='+encodeURIComponent(id)+'&offset='+offset);if(serial!==generation)return;table(graph,d.edges,['direction','citing_identifier','cited_identifier','snapshot_id']);if(offset===0)table(graph,d.coverage,['direction','status','returned_count','provider_count','observed_at']);offset=d.next_offset;more.hidden=offset===null;}catch(e){message(e.message);}finally{more.disabled=false;}});pane.append(more,graph);message(data.target.record_id);
    }catch(e){message(e.message);}
  }
  $("enrich-refresh").addEventListener('click',refresh);$("enrich-filter").addEventListener('input',list);refresh();
})();
