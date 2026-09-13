/* Versioned public research display. Never calls the authenticated private API. */
(() => {
  'use strict';
  const ENDPOINT='https://criminal-infiltration-curator.colazeta-research.workers.dev/api/public-paper-research';
  const CLASSES={aetiology:'Eziologia',diagnosis:'Diagnosi',screening:'Screening',therapy:'Terapia',prognosis:'Prognosi',prevention:'Prevenzione'};
  const COVERAGE={abstract_only:'Solo abstract / sintesi dell’editore',partial_text:'Testo parziale',full_text:'Testo completo'};
  const MISSING={not_reported:'Non riportato nella fonte consultata',not_verifiable:'Non verificabile dalla fonte consultata',not_applicable:'Non applicabile',ambiguous:'Interpretazione ambigua'};
  const LABELS={summary:'Sintesi della ricerca',contribution:'Contributo principale',research_question:'Domanda di ricerca',infiltration_definition:'Definizione dell’infiltrazione',infiltration_operationalisation:'Identificazione empirica dell’infiltrazione',authors_limitations:'Limiti dichiarati dagli autori',study_type:'Tipo di studio',population:'Popolazione',sampling:'Campionamento',sample_size:'Numerosità',observation_unit:'Unità di osservazione',analysis_unit:'Unità di analisi',geography:'Territorio',period:'Periodo',name:'Dataset',provider:'Origine / fornitore',accessibility:'Accessibilità',selection:'Selezione',coverage:'Copertura',limitations:'Limiti del dataset',design:'Disegno di ricerca',method:'Metodo',comparison:'Comparatore',identification:'Strategia di identificazione',validation:'Validazione',robustness:'Robustezza',original_name:'Nome originale',concept:'Concetto misurato',operationalisation:'Operazionalizzazione',unit:'Unità',transformation:'Trasformazioni',role:'Ruolo nell’analisi',statement:'Risultato',finding_type:'Tipo di risultato',direction:'Direzione',estimate:'Stima',uncertainty:'Incertezza',reference_comparison:'Confronto di riferimento',population_scope:'Popolazione di riferimento',temporal_scope:'Ambito temporale',caveat:'Cautela interpretativa'};
  const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n};
  const normalDoi=s=>String(s||'').trim().replace(/^https?:\/\/(?:dx\.)?doi\.org\//i,'').toLowerCase();
  function safeUrl(value){try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password&&!/[\u0000-\u0020]/.test(value)&&![...u.searchParams.keys()].some(k=>/(token|secret|signature|session|api.?key|authorization|^sig$)/i.test(k))?u.href:null}catch{return null}}
  function selectRecord(data,record){
    if(data?.schema_version!==1||data.projection_version!=='CILE-PUBLIC-RESEARCH-1'||!['available','not_assessed','stale','not_registered','withheld'].includes(data.availability))throw Error('invalid_projection');
    if(data.availability==='not_registered'&&data.candidate===null&&data.research===null)return data;
    const c=data.candidate;
    if(!c||c.id!==record.id||c.title!==record.title||normalDoi(c.doi)!==normalDoi(record.doi)||JSON.stringify([...(c.sourceLinks||[])].sort())!==JSON.stringify([...(record.sourceLinks||[])].sort()))throw Error('identity_mismatch');
    if((data.availability==='available')!==(data.research!==null))throw Error('invalid_availability');
    if(data.research&&(data.research.assessment_state!=='unreviewed_proposal'||!COVERAGE[data.research.source_coverage]||!['proposed','insufficient_evidence','outside_framework'].includes(data.research.framework?.status)))throw Error('invalid_research_state');
    return data;
  }
  function section(parent,title,open=false){const d=el('details');d.open=open;d.append(el('summary',title));parent.append(d);return d}
  function render(parent,data){
    parent.replaceChildren(el('h3','Contesto della ricerca'));
    if(data.availability!=='available'){
      const messages={not_assessed:'Non è ancora disponibile un’estrazione scientifica per questo paper. Nessuna classe è stata attribuita.',not_registered:'Il paper non è ancora presente nell’indice analitico corrente. Questo non significa che sia fuori dal framework.',stale:'Esiste un’analisi riferita a una versione precedente dei metadati. Non viene mostrata come analisi corrente.',withheld:'È presente materiale analitico, ma la sua pubblicazione non ha superato i controlli su fonti, integrità o riservatezza. Nessuna classificazione viene dedotta in sua sostituzione.'};
      parent.append(el('p',messages[data.availability]));return;
    }
    const r=data.research,f=r.framework,sourceMap=new Map(r.sources.map(s=>[s.id,s])),spans=new Map(r.spans.map(s=>[s.id,s]));
    function fact(parent,label,v){
      const line=el('div');line.append(el('strong',label+': '));
      const value=v.value===null?(MISSING[v.status]||'Non disponibile'):v.value;
      line.append(el('span',value));
      if(v.value!==null&&v.status==='ambiguous')line.append(el('small',' — Interpretazione ambigua'));
      if(v.value!==null)line.append(el('small',v.origin==='analyst'?' — Valutazione analitica proposta':' — Sintesi attribuita alla fonte'));
      if(v.evidence_span_ids?.length){const evidence=section(line,'Fonti e localizzazione');for(const id of v.evidence_span_ids){const span=spans.get(id),source=sourceMap.get(span?.source_id);if(!source)continue;const p=el('p');const href=safeUrl(source.url);if(href){const a=el('a',new URL(href).hostname);a.href=href;a.rel='noreferrer noopener';p.append(a)}p.append(el('span',' · '+span.locator));evidence.append(p)}}
      parent.append(line);
    }
    parent.append(el('p',r.generation_kind==='automated'?'Estrazione automatica preliminare, non validata scientificamente. La classificazione resta una proposta.':'Estrazione preliminare non confermata. La modalità di produzione non è attestata come revisione umana.'));
    parent.append(el('p','Base documentale: '+COVERAGE[r.source_coverage]+' · Analisi aggiornata: '+r.updated_at));
    const cls=section(parent,'Collocazione nel framework delle sei classi',true);
    if(f.status==='proposed')cls.append(el('p','Classe principale proposta: '+CLASSES[f.primary]));
    else cls.append(el('p',f.status==='insufficient_evidence'?'Evidenza insufficiente per attribuire una classe.':'Contributo valutato come esterno al framework; proposta non confermata.'));
    fact(cls,'Motivazione',f.rationale);
    for(const s of f.secondary){cls.append(el('h4','Classe secondaria proposta: '+CLASSES[s.category]));fact(cls,'Motivazione distinta',s.rationale)}
    if(f.alternative)cls.append(el('p','Classificazione alternativa registrata: '+CLASSES[f.alternative]));
    cls.append(el('small','Eziologia · Diagnosi · Screening · Terapia · Prognosi · Prevenzione. Le classi descrivono il contributo, non l’ammissibilità del paper nella revisione.'));
    const overview=section(parent,'Domanda, contributo e definizione del fenomeno',true);
    for(const k of ['research_question','contribution','summary','infiltration_definition','infiltration_operationalisation'])fact(overview,LABELS[k],r[k]);
    function item(parent,object,title){const box=section(parent,title);for(const[k,v]of Object.entries(object)){if(v&&typeof v==='object'&&!Array.isArray(v)&&'status'in v)fact(box,LABELS[k]||k,v)}return box}
    const studies=section(parent,`Studi, dati e analisi (${r.studies.length} studi)`);
    if(!r.studies.length)studies.append(el('p','Nessuno studio strutturato estratto dalla fonte consultata; non equivale all’assenza di uno studio nell’articolo.'));
    r.studies.forEach((study,i)=>{
      const s=item(studies,study,'Studio '+(i+1));
      r.datasets.filter(d=>d.study_id===study.id).forEach(d=>item(s,d,'Dataset · '+d.id));
      r.analyses.filter(a=>a.study_id===study.id).forEach(a=>{
        const box=item(s,a,'Analisi · '+a.id);box.append(el('p','Dataset collegati: '+(a.dataset_ids.join(', ')||'Nessuno registrato')));
        const vars=r.variable_uses.filter(v=>v.analysis_id===a.id),findings=r.findings.filter(f=>f.analysis_id===a.id);
        const vs=section(box,`Variabili usate in questa analisi (${vars.length})`);vars.forEach(v=>{const b=item(vs,v,'Variabile · '+v.id);b.append(el('p','Dataset: '+(v.dataset_ids.join(', ')||'Nessuno registrato')))});
        const fs=section(box,`Risultati di questa analisi (${findings.length})`);findings.forEach(f=>{const b=item(fs,f,'Risultato · '+f.id);b.append(el('p','Variabili collegate: '+(f.variable_use_ids.join(', ')||'Nessuna registrata')))});
      });
    });
    const limits=section(parent,'Limiti e stato dell’analisi');fact(limits,LABELS.authors_limitations,r.authors_limitations);
    limits.append(el('p','Le osservazioni di lavoro interne non sono pubblicate automaticamente. Le motivazioni analitiche pubbliche sono distinte dalle affermazioni degli autori.'));
    limits.append(el('p','Non riportato significa non riportato nella fonte consultata, non assente dall’intero articolo. Nessuna approvazione scientifica è implicita.'));
    const provenance=section(parent,'Fonti consultate e versioni');
    r.sources.forEach(s=>{const p=el('p'),href=safeUrl(s.url);if(href){const a=el('a',href);a.href=href;a.rel='noreferrer noopener';p.append(a)}p.append(el('span',` · ${s.kind} · ${s.version||'Versione non specificata'} · Acquisita: ${s.checked_at}`));provenance.append(p)});
    provenance.append(el('p',`Protocollo ${r.protocol_version} · Codebook ${r.codebook_version}`));
  }
  async function load(parent,record,isCurrent=()=>true){
    parent.setAttribute('aria-busy','true');
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),12000);
    try{
      const response=await fetch(ENDPOINT+'?id='+encodeURIComponent(record.id),{cache:'no-store',credentials:'omit',signal:controller.signal});
      if(!response.ok)throw Error('public_research_unavailable');
      const data=selectRecord(await response.json(),record);
      if(isCurrent())render(parent,data);
    }catch{if(isCurrent())parent.textContent='Il contesto di ricerca non è verificabile in questo momento. Un errore di caricamento o un disallineamento dei metadati non significa che l’analisi sia assente.'}
    finally{clearTimeout(timeout);if(isCurrent())parent.setAttribute('aria-busy','false')}
  }
  globalThis.CILEPaperResearch={render,load,selectRecord,safeUrl};
})();
