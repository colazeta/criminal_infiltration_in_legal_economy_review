/* Read-only rendering of archived, explicitly unreviewed annotations. */
(() => {
  'use strict';
  const ENDPOINT='https://criminal-infiltration-curator.colazeta-research.workers.dev/api/public-paper-research';
  const ASSESSMENT_STATE='unreviewed_manual_support';
  const FIELD_LABELS = {
    summary: 'Sintesi della ricerca', contribution: 'Contributo principale',
    research_question: 'Domanda di ricerca', infiltration_definition: 'Definizione dell’infiltrazione',
    infiltration_operationalisation: 'Identificazione empirica dell’infiltrazione',
    authors_limitations: 'Limiti dichiarati dagli autori', study_type: 'Tipo di studio',
    population: 'Popolazione', sampling: 'Campionamento / copertura', sample_size: 'Numerosità',
    observation_unit: 'Unità di osservazione', analysis_unit: 'Unità di analisi', geography: 'Territorio',
    period: 'Periodo', design: 'Disegno', method: 'Metodo', comparison: 'Comparatore',
    identification: 'Strategia di identificazione', validation: 'Validazione', robustness: 'Robustezza',
    primary: 'Classe principale proposta', secondary: 'Classe secondaria proposta', alternative: 'Classificazione alternativa',
    rationale: 'Motivazione', secondary_rationale: 'Motivazione della classe secondaria', status: 'Stato della proposta',
  };
  const PRESET_TITLES = {
    overview: 'Domanda, contributo e definizione del fenomeno',
    framework: 'Collocazione nel framework delle sei classi',
    studies: 'Studi, campione, periodo e geografia',
    datasets: 'Dataset e fonti dei dati',
    methods: 'Disegno, metodi, identificazione e robustezza',
    variables: 'Variabili e operazionalizzazione',
    findings: 'Risultati, stime, incertezza e limiti',
    sources: 'Fonti consultate e versioni',
  };

  const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
  function validate(payload,record){
    if(payload?.schema_version!==1||payload.projection_version!=='CILE-PUBLIC-ANNOTATIONS-1'||payload.candidate_id!==record.id||!Array.isArray(payload.annotations)||payload.annotations.length>100||!/^[a-f0-9]{64}$/.test(payload.revision||'')||!Number.isSafeInteger(payload.conflicts)||payload.conflicts<0)throw Error('annotation_projection_invalid');
    const seen=new Set();
    for(const a of payload.annotations){
      if(!/^[a-f0-9]{64}$/.test(a.annotation_id||'')||seen.has(a.annotation_id)||a.assessment_state!==ASSESSMENT_STATE||!Array.isArray(a.sections)||!Array.isArray(a.classes)||!/^https:\/\/github\.com\/colazeta\/criminal_infiltration_in_legal_economy_review\/issues\/\d+#issuecomment-\d+$/.test(a.source_url))throw Error('annotation_projection_invalid');
      seen.add(a.annotation_id);
      for(const section of a.sections)if(!Object.hasOwn(PRESET_TITLES,section.scope)||typeof section.group_label!=='string'||!Array.isArray(section.fields)||section.fields.some(f=>typeof f.field_name!=='string'||typeof f.value!=='string'))throw Error('annotation_projection_invalid');
    }
    return payload;
  }
  async function fetchAnnotation(record){
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
    try{
      const response=await fetch(ENDPOINT+'?view=annotations&id='+encodeURIComponent(record.id),{cache:'no-store',credentials:'omit',signal:controller.signal});
      if(!response.ok)throw Error('annotation_projection_unavailable');
      return validate(await response.json(),record);
    }finally{clearTimeout(timer);}
  }
  function render(parent,payload){
    const host=el('section');host.className='paper-manual-research';host.dataset.revision=payload.revision;
    host.append(el('h3','Annotazioni di lettura'));
    host.append(el('p','Supporto manuale non revisionato scientificamente. Ogni annotazione conserva la propria fonte; non certifica il completamento dell’analisi.'));
    if(payload.conflicts)host.append(el('p',`${payload.conflicts} revisioni discordanti richiedono una verifica.`));
    if(!payload.annotations.length)host.append(el('p','Nessuna annotazione pubblicabile disponibile.'));
    payload.annotations.forEach((a,index)=>{
      const article=el('article');article.dataset.annotationId=a.annotation_id;
      article.append(el('h4',`Annotazione ${index+1}`));
      for(const section of a.sections){
        if(!section.fields.length)continue;
        const box=el('details');box.append(el('summary',PRESET_TITLES[section.scope]+(section.group_label?' · '+section.group_label:'')));
        const dl=el('dl');
        for(const f of section.fields)dl.append(el('dt',FIELD_LABELS[f.field_name]||({annotation_text:'Contenuto annotato',source_url:'Fonte'}[f.field_name])||f.field_name),el('dd',f.value));
        box.append(dl);article.append(box);
      }
      const link=el('a','Traccia originale dell’annotazione');link.href=a.source_url;link.target='_blank';link.rel='noreferrer noopener';article.append(link);
      if(a.updated_at)article.append(el('small',' Aggiornata: '+a.updated_at.slice(0,10)));
      if(a.unparsed_lines)article.append(el('p','Alcune parti della fonte non sono esposte in questa scheda.'));
      host.append(article);
    });
    parent.append(host);return host;
  }
  async function load(parent,record,isCurrent=()=>true){
    try{const payload=await fetchAnnotation(record);if(isCurrent())render(parent,payload);}
    catch{if(isCurrent())parent.append(el('p','Impossibile caricare le annotazioni. Riprova riaprendo la scheda.'));}
  }
  function wrapResearchApi(api) {
    if (!api || typeof api.load !== 'function' || api.__manualSupportWrapped) return api;
    const originalLoad = api.load.bind(api);
    api.load = async (parent, record, isCurrent = () => true) => {
      const result = await originalLoad(parent, record, isCurrent);
      if (isCurrent()) await load(parent, record, isCurrent);
      return result;
    };
    Object.defineProperty(api, '__manualSupportWrapped', { value: true });
    return api;
  }

  const existing = globalThis.CILEPaperResearch;
  if (existing) globalThis.CILEPaperResearch = wrapResearchApi(existing);
  else {
    let pending;
    Object.defineProperty(globalThis, 'CILEPaperResearch', {
      configurable: true, enumerable: true, get() { return pending; },
      set(value) {
        pending = wrapResearchApi(value);
        Object.defineProperty(globalThis, 'CILEPaperResearch', { configurable: true, enumerable: true, writable: true, value: pending });
      },
    });
  }

  globalThis.CILEManualResearch=Object.freeze({assessmentState:ASSESSMENT_STATE,fetchAnnotation,validate,render,load,wrapResearchApi});
})();
