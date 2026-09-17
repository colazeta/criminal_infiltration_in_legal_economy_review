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
  // UI-only diagnostic over the existing closed projection. No approval is inferred.
  // CILE-PUBLIC-RESEARCH-1 contains proposals, not completion/adjudication receipts.
  function progress(data,completion=null) {
    const result={completed:false, evidence:false, extraction:false, classification:false,
      references:null, adjudication:null, fields:0, resolved:0, unresolved:0,
      availability:data?.availability||'unknown'};
    if(completion){result.adjudication=completion.status;result.references=completion.reference_coverage;result.completed=Boolean(globalThis.CILEPaperProcessing?.isCompleted({completionVerified:true,completion,researchRevision:data?.revision,research:data?.availability}))}
    if(data?.availability!=='available'||!data.research)return result;
    const r=data.research;
    if(r.assessment_state!=='unreviewed_proposal')throw Error('unsupported_completion_contract');
    result.extraction=true;
    result.evidence=r.source_coverage==='full_text'&&Array.isArray(r.sources)&&r.sources.some(s=>s.kind==='full_text');
    result.classification=r.framework?.status==='proposed'&&Object.hasOwn(CLASSES,r.framework.primary);
    const spans=new Set((r.spans||[]).map(s=>s.id));
    const inspect=v=>{
      result.fields++;
      const sourced=v?.status==='reported'&&typeof v.value==='string'&&v.value.trim()&&
        Array.isArray(v.evidence_span_ids)&&v.evidence_span_ids.length&&v.evidence_span_ids.every(id=>spans.has(id));
      const assessedMissing=result.evidence&&['not_reported','not_applicable'].includes(v?.status);
      if(sourced||assessedMissing)result.resolved++;else result.unresolved++;
    };
    ['summary','contribution','research_question','infiltration_definition','infiltration_operationalisation','authors_limitations'].forEach(k=>inspect(r[k]));
    const groups={
      studies:['study_type','research_question','population','sampling','sample_size','observation_unit','analysis_unit','geography','period'],
      datasets:['name','provider','accessibility','selection','coverage','limitations'],
      analyses:['design','method','comparison','identification','validation','robustness'],
      variable_uses:['original_name','concept','operationalisation','unit','period','transformation','role'],
      findings:['statement','finding_type','direction','estimate','unit','uncertainty','reference_comparison','population_scope','temporal_scope','caveat']
    };
    for(const [group,keys]of Object.entries(groups))for(const row of r[group]||[])keys.forEach(k=>inspect(row[k]));
    // A resolved field is not a quality judgement. Empty collections do not certify
    // completeness. Unknown citation/QA state is never silently turned into zero.
    return result;
  }
  function renderProgress(parent,data,completion=null) {
    const p=progress(data,completion),box=section(parent,'Stato dell’analisi e verifiche di completamento');box.setAttribute('aria-label','Progresso verso il completamento');
    box.append(el('h4',p.completed?'Arricchimento completo e validato':'Arricchimento end-to-end: non attestato come completato'));
    const stages=el('dl');
    const unavailable=['stale','withheld','unknown'].includes(p.availability);
    const rows=[
      ['Fonte sufficiente',p.evidence?'Testo completo attestato nella proposta corrente':'Non attestabile da questa proiezione; un link al PDF non basta'],
      ['Estrazione scientifica',p.extraction?`Proposta presente; ${p.resolved}/${p.fields} campi documentati o esplicitamente mancanti nella proposta, ${p.unresolved} da chiarire. Completezza e correttezza da validare`:(unavailable?'Stato non verificabile':'Nessuna proposta corrente visibile')],
      ['References e citazioni',completion?'Copertura per fonte e direzione nella sezione Riferimenti':'Copertura non verificabile; non equivale a zero references'],
      ['Classificazione nelle sei classi',p.classification?'Categoria proposta, non ancora validata':'Nessuna categoria validata attestata'],
      ['QA e adjudication',completion?(p.completed?'Accettata il '+completion.completed_at:'Stato dell’attestazione: '+completion.status):'Attestazione non verificabile'],
      ['Completed',p.completed?'Sì: attestazione valida per questa versione':'No: una proposta, una sintesi o il full text non attestano il completamento']
    ];
    for(const [label,value]of rows)stages.append(el('dt',label),el('dd',value));
    box.append(stages,el('p','I passaggi possono avanzare separatamente. I campi non riportati o non applicabili rimangono espliciti; non si inventano valori per completare la scheda.'));
    parent.append(box);
  }
  function emptySections(parent) {
    for(const title of ['Domanda, contributo e definizione del fenomeno','Collocazione nel framework delle sei classi','Studi, campione, periodo e geografia','Dataset e fonti dei dati','Disegno, metodi, identificazione e robustezza','Variabili e operazionalizzazione','Risultati, stime, incertezza e limiti','Fonti consultate, versioni e QA']){
      const box=section(parent,title);box.append(el('p','Contenuto non disponibile nella proiezione corrente. Questo spazio non rappresenta un dato estratto né una validazione.'));
    }
  }
  function section(parent,title,open=false){const d=el('details');d.open=open;d.append(el('summary',title));parent.append(d);return d}
  function render(parent,data,completion=null){
    parent.replaceChildren(el('h3','Contesto della ricerca'));
    renderProgress(parent,data,completion);
    renderReferences(parent,completion);
    const expand=el('button','Mostra tutti i campi'),collapse=el('button','Richiudi le sezioni');
    expand.type=collapse.type='button';
    expand.onclick=()=>parent.querySelectorAll('details').forEach(d=>{d.open=true});
    collapse.onclick=()=>parent.querySelectorAll('details').forEach(d=>{d.open=false});
    const tools=el('div');tools.className='research-tools';tools.append(expand,collapse);parent.append(tools);
    if(data.availability!=='available'){
      const messages={not_assessed:'Non è ancora disponibile un’estrazione scientifica per questo paper. Nessuna classe è stata attribuita.',not_registered:'Il paper non è ancora presente nell’indice analitico corrente. Questo non significa che sia fuori dal framework.',stale:'Esiste un’analisi riferita a una versione precedente dei metadati. Non viene mostrata come analisi corrente.',withheld:'È presente materiale analitico, ma la sua pubblicazione non ha superato i controlli su fonti, integrità o riservatezza. Nessuna classificazione viene dedotta in sua sostituzione.'};
      parent.append(el('p',messages[data.availability]));emptySections(parent);return;
    }
    const r=data.research,f=r.framework,sourceMap=new Map(r.sources.map(s=>[s.id,s])),spans=new Map(r.spans.map(s=>[s.id,s]));
    function fact(parent,label,v){
      if(!v||typeof v!=='object'){parent.append(el('p',label+': Informazione non disponibile nella scheda corrente.'));return}
      const line=el('div');line.className='research-fact';line.append(el('strong',label+': '));
      const value=v.value===null?(MISSING[v.status]||'Non disponibile'):v.value;
      line.append(el('span',value));
      if(v.value!==null&&v.status==='ambiguous')line.append(el('small',' — Interpretazione ambigua'));
      if(v.value!==null)line.append(el('small',v.origin==='analyst'?' — Valutazione analitica proposta':' — Sintesi attribuita alla fonte'));
      if(v.evidence_span_ids?.length){const evidence=section(line,'Fonti e localizzazione');for(const id of v.evidence_span_ids){const span=spans.get(id),source=sourceMap.get(span?.source_id);if(!source)continue;const p=el('p');const href=safeUrl(source.url);if(href){const a=el('a',new URL(href).hostname);a.href=href;a.rel='noreferrer noopener';p.append(a)}p.append(el('span',' · '+span.locator));evidence.append(p)}}
      parent.append(line);
    }
    parent.append(el('p',r.generation_kind==='automated'?'Estrazione automatica preliminare, non validata scientificamente. La classificazione resta una proposta.':'Estrazione preliminare non confermata. La modalità di produzione non è attestata come revisione umana.'));
    parent.append(el('p','Base documentale: '+COVERAGE[r.source_coverage]+' · Analisi aggiornata: '+r.updated_at));
    const geography=section(parent,'Ambito geografico dell’analisi');
    if(!r.studies.length)geography.append(el('p','Nessuno studio strutturato disponibile: il paese non viene dedotto dal titolo o dagli autori.'));
    r.studies.forEach((study,i)=>fact(geography,'Studio '+(i+1)+' · Territorio effettivamente analizzato',study.geography));
    if(globalThis.CILEPaperGeography){
      const g=globalThis.CILEPaperGeography.fromResearch(data);
      geography.append(el('p',g.countries.length?'Paesi / territori identificati nella geografia proposta: '+g.countries.map(globalThis.CILEPaperGeography.name).join(', '):'Nessun paese normalizzabile con sufficiente chiarezza dalla geografia estratta.'));
    }
    geography.append(el('small','La copertura può essere cittadina, regionale, nazionale o multipaese. Un paese presente non implica un campione nazionale. Affiliazioni, nazionalità degli autori e luoghi menzionati soltanto come contesto non definiscono l’area studiata.'));
    const cls=section(parent,'Collocazione nel framework delle sei classi');
    if(f.status==='proposed')cls.append(el('p','Classe principale proposta: '+CLASSES[f.primary]));
    else cls.append(el('p',f.status==='insufficient_evidence'?'Evidenza insufficiente per attribuire una classe.':'Contributo valutato come esterno al framework; proposta non confermata.'));
    fact(cls,'Motivazione',f.rationale);
    for(const s of f.secondary){cls.append(el('h4','Classe secondaria proposta: '+CLASSES[s.category]));fact(cls,'Motivazione distinta',s.rationale)}
    if(f.alternative)cls.append(el('p','Classificazione alternativa registrata: '+CLASSES[f.alternative]));
    cls.append(el('small','Eziologia · Diagnosi · Screening · Terapia · Prognosi · Prevenzione. Le classi descrivono il contributo, non l’ammissibilità del paper nella revisione.'));
    const overview=section(parent,'Domanda, contributo e definizione del fenomeno',true);
    for(const k of ['research_question','contribution','summary','infiltration_definition','infiltration_operationalisation'])fact(overview,LABELS[k],r[k]);
    parent.insertBefore(overview,geography);
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
  function selectCompletion(data,record,research) {
    if(data?.schema_version!==1||data.projection_version!=='CILE-PUBLIC-COMPLETION-1'||data.candidate_id!==record.id||!Array.isArray(data.reference_coverage)||!Array.isArray(data.outgoing_references?.identifiers))throw Error('invalid_completion_projection');
    if(!globalThis.CILEPaperProcessing)throw Error('completion_validator_unavailable');
    globalThis.CILEPaperProcessing.completionState(data,research.revision,research.availability==='available');
    return data;
  }
  function renderReferences(parent,completion) {
    const box=section(parent,'References e citazioni');
    if(!completion){box.append(el('p','Bibliografia e citazioni ricevute non sono verificabili in questo momento. Le fonti consultate non sono la bibliografia.'));return}
    if(!completion.reference_coverage.length)box.append(el('p','Copertura citazionale non ancora documentata: non equivale all’assenza di riferimenti.'));
    for(const c of completion.reference_coverage)box.append(el('p',`${c.provider} · ${c.direction==='incoming'?'Citazioni ricevute':'Riferimenti in uscita'} · ${c.status} · Osservati nell’unità di copertura: ${c.returned_count}; dichiarati: ${c.provider_count===null?'non disponibili':c.provider_count} · ${c.observed_at}`));
    box.append(el('p','Copertura riferita alla fonte e alla data indicate, non all’intero grafo citazionale. Gli identificativi riconciliati non sostituiscono le voci bibliografiche ancora irrisolte.'));
    const refs=completion.outgoing_references;
    box.append(el('p',`Identificativi bibliografici osservati: ${refs.total_observed}${refs.truncated?' (lista parziale)':''}.`));
    const list=el('ol');
    for(const identifier of refs.identifiers){
      const item=el('li'),doi=identifier.startsWith('doi:')?identifier.slice(4):null;
      const href=doi&&/^10\.\d{4,9}\/\S+$/.test(doi)?safeUrl('https://doi.org/'+encodeURIComponent(doi)):safeUrl(identifier);
      if(href){const a=el('a',identifier);a.href=href;a.rel='noreferrer noopener';item.append(a)}else item.textContent=identifier;
      list.append(item);
    }
    box.append(list);
  }
  const ASSETS_ENDPOINT='https://criminal-infiltration-curator.colazeta-research.workers.dev/api/public-paper-assets';
  function selectAssets(data,record){
    if(data?.schema_version!==1||data.projection_version!=='CILE-PUBLIC-ASSETS-1'||data.candidate_id!==record.id||!Array.isArray(data.documents)||data.documents.length>100)throw Error('invalid_assets');
    if(data.availability==='registered'){
      const c=data.candidate,n=v=>String(v||'').trim().toLowerCase().replace(/^https?:\/\/(dx\.)?doi\.org\//,'');
      if(!c||c.id!==record.id||c.title!==record.title||n(c.doi)!==n(record.doi)||JSON.stringify([...(c.sourceLinks||[])].sort())!==JSON.stringify([...(record.sourceLinks||[])].sort()))throw Error('assets_identity_mismatch');
    }else if(data.availability!=='not_registered'||data.candidate!==null)throw Error('invalid_assets');
    for(const d of data.documents)if(!/^[a-f0-9]{64}$/.test(d.document_id)||!safeUrl(d.source_url)||!safeUrl(d.licence_url)||typeof d.attribution!=='string')throw Error('invalid_public_document');
    if(data.bibliography){const b=data.bibliography;if(!['paper_bibliography','provider_references'].includes(b.scope)||!['partial','source_complete','not_reported'].includes(b.coverage)||b.assessment_state!=='unreviewed_proposal'||!Array.isArray(b.entries)||b.entries.length>100||!safeUrl(b.source_url)||!/^[a-f0-9]{64}$/.test(b.revision))throw Error('invalid_bibliography');}
    return data;
  }
  async function loadAssets(parent,record,isCurrent=()=>true){
    const box=section(parent,'PDF conservati e bibliografia dettagliata');box.append(el('p','Verifica del documento e dei riferimenti in corso.'));
    let revision=null,next=0;const seen=new Set();
    async function page(){
      const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
      try{const response=await fetch(ASSETS_ENDPOINT+'?id='+encodeURIComponent(record.id)+'&offset='+next+(revision?'&revision='+revision:''),{cache:'no-store',credentials:'omit',signal:controller.signal});if(!response.ok)throw Error('assets_unavailable');const data=selectAssets(await response.json(),record);if(!isCurrent())return;
        if(next===0){box.replaceChildren(el('summary','PDF conservati e bibliografia dettagliata'));
          if(!data.documents.length)box.append(el('p','Nessuna copia pubblica attestata. Le eventuali copie riservate si leggono nella console di arricchimento dopo l’accesso; un link esterno non equivale a una copia conservata.'));
          const privateReader=el('a','Apri la console riservata per questo paper');privateReader.href='https://criminal-infiltration-curator.colazeta-research.workers.dev/enrichment.html?candidate='+encodeURIComponent(record.id);privateReader.target='_blank';privateReader.rel='noopener noreferrer';box.append(privateReader);
          for(const d of data.documents){const link=el('a','Leggi PDF conservato · '+d.version_label);link.href=ASSETS_ENDPOINT+'?id='+encodeURIComponent(record.id)+'&document='+d.document_id;link.target='_blank';link.rel='noopener noreferrer';box.append(link,el('p',d.attribution+' · '+d.byte_length+' byte · '+d.licence_url));}
        }
        const b=data.bibliography;if(!b){box.append(el('p','Bibliografia dettagliata non ancora registrata; gli identificativi citazionali sono mostrati separatamente.'));return}
        if(revision&&revision!==b.revision)throw Error('bibliography_changed');revision=b.revision;
        if(next===0)box.append(el('p',`${b.scope==='paper_bibliography'?'Bibliografia del testo':'Riferimenti forniti dal provider'} · ${b.coverage} · ${b.entries_count} voci registrate; totale dichiarato ${b.declared_count===null?'non noto':b.declared_count} · ${b.observed_at}. Metadati proposti, non accettazione scientifica.`));
        const list=el('ol');list.start=next+1;
        for(const e of b.entries){if(!Number.isSafeInteger(e.position)||seen.has(e.position)||!Array.isArray(e.authors))throw Error('bibliography_identity');seen.add(e.position);const item=el('li',[e.authors.join('; '),e.year,e.title||'Titolo non riconciliato',e.venue].filter(v=>v!==null&&v!=='').join(' · '));if(e.doi||e.url){const href=safeUrl(e.doi?'https://doi.org/'+encodeURIComponent(e.doi):e.url);if(href){const a=el('a',' Fonte');a.href=href;a.rel='noopener noreferrer';item.append(a)}}if(e.unresolved_identity)item.append(el('span',' · Identità bibliografica da riconciliare'));list.append(item)}box.append(list);
        next=b.next_offset;if(next!==null){if(!Number.isSafeInteger(next)||next<seen.size||next>1000)throw Error('bibliography_cursor');const more=el('button','Altri riferimenti');more.type='button';more.onclick=()=>{more.remove();page()};box.append(more)}
      }catch{if(isCurrent())box.append(el('p','Stato del documento o della bibliografia non verificabile. Nessun dato mancante viene interpretato come assenza.'))}finally{clearTimeout(timer)}
    }
    await page();
  }
  async function load(parent,record,isCurrent=()=>true){
    parent.setAttribute('aria-busy','true');
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),12000);
    try{
      const response=await fetch(ENDPOINT+'?id='+encodeURIComponent(record.id),{cache:'no-store',credentials:'omit',signal:controller.signal});
      if(!response.ok)throw Error('public_research_unavailable');
      const data=selectRecord(await response.json(),record);
      if(!isCurrent())return;
      let completion=null;
      try{const response=await fetch(ENDPOINT+'?view=completion&id='+encodeURIComponent(record.id),{cache:'no-store',credentials:'omit',signal:controller.signal});if(response.ok)completion=selectCompletion(await response.json(),record,data)}catch{}
      if(isCurrent()){render(parent,data,completion);loadAssets(parent,record,isCurrent);}
    }catch{if(isCurrent()){parent.replaceChildren(el('h3','Contesto della ricerca'),el('p','Il contesto di ricerca non è verificabile in questo momento. Un errore di caricamento o un disallineamento dei metadati non significa che l’analisi sia assente.'));emptySections(parent);}}
    finally{clearTimeout(timeout);if(isCurrent())parent.setAttribute('aria-busy','false')}
  }
  globalThis.CILEPaperResearch={render,load,selectRecord,safeUrl,progress,renderProgress,selectCompletion,renderReferences,selectAssets,loadAssets};
})();

/* Read-only geography derived from source-grounded study.geography facts.
   Never scans titles, author affiliations, abstracts or publisher addresses. */
(() => {
  'use strict';
  const CODES='AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW'.split(' ');
  const normal=s=>String(s||'').normalize('NFKC').toLowerCase().replace(/[’']/g,"'").replace(/\s+/g,' ').trim().replace(/[.]$/,'');
  const aliases=new Map(), names=new Map();
  const add=(name,code)=>{const key=normal(name);if(key)aliases.set(key,code)};
  for(const locale of ['en','it']){
    const display=new Intl.DisplayNames([locale],{type:'region'});
    for(const code of CODES){const name=display.of(code);add(name,code);if(locale==='it')names.set(code,name)}
  }
  for(const[code,values]of Object.entries({BA:['Bosnia and Herzegovina'],TT:['Trinidad and Tobago'],AG:['Antigua and Barbuda'],KN:['Saint Kitts and Nevis'],VC:['Saint Vincent and the Grenadines'],ST:['Sao Tome and Principe','São Tomé and Príncipe'],GB:['UK','U.K.','United Kingdom','Great Britain','Regno Unito'],US:['USA','U.S.A.','U.S.','United States of America','United States','Stati Uniti'],RU:['Russian Federation'],CZ:['Czech Republic'],KR:['Republic of Korea','South Korea'],KP:["Democratic People's Republic of Korea",'North Korea'],CD:['Democratic Republic of the Congo','DR Congo'],CG:['Republic of the Congo'],CI:["Cote d'Ivoire","Côte d'Ivoire"],TR:['Turkey','Türkiye'],VA:['Vatican City','Holy See']}))values.forEach(value=>add(value,code));
  // Bare ambiguous names never silently pick a country or a successor state.
  ['congo','korea','georgia','georgie','georgien','georgia del sud'].forEach(value=>aliases.delete(value));
  const uncertain=/\b(unknown|unspecified|uncertain|probably|possibly|perhaps|e\.g\.|such as|not reported|other countries|among others|excluding|except|versus|origin|affiliation)\b/i;
  const broad=/^(?:europe|europa|european union|unione europea|eu|ue|africa|asia|latin america|america latina|north america|south america|oceania|oecd|ocse|americas|middle east)$/i;
  const global=/^(?:global|globale|worldwide|world-wide|mondiale|world|mondo)$/i;
  function parse(value){
    if(typeof value!=='string'||!value.trim())return{countries:[],kind:'missing'};
    const text=value.trim();
    if(global.test(text))return{countries:[],kind:'global'};
    if(broad.test(text))return{countries:[],kind:'supranational'};
    // Optional explicit form preserves full scope, while keeping a bounded list.
    const labelled=text.match(/^(?:countries|country|paesi|paese)\s*:\s*([^|]+)(?:\|\s*(?:scope|territorio|ambito)\s*:.+)?$/i);
    const list=labelled?labelled[1].trim():text;
    if(uncertain.test(list))return{countries:[],kind:'unresolved'};
    const exact=aliases.get(normal(list));
    if(exact)return{countries:[exact],kind:'country'};
    if(labelled&&/^Georgia\s*$/i.test(list))return{countries:['GE'],kind:'country'};
    // Protect names containing conjunctions/commas before tokenising a list.
    const tokens=[];
    let protectedList=list;
    for(const[name,code]of [...aliases].sort((a,b)=>b[0].length-a[0].length)){
      if(!/[,&;]|\band\b|\be\b/i.test(name))continue;
      const escaped=name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
      protectedList=protectedList.replace(new RegExp('(^|[\\s,;])('+escaped+')(?=$|[\\s,;)])','gi'),(_,lead)=>{const token='__country'+tokens.length+'__';tokens.push(code);return lead+token});
    }
    const parts=protectedList.split(/\s*(?:;|,|\band\b|\be\b|&)\s*/i).filter(Boolean);
    const result=[];
    for(const part of parts){
      const marker=part.match(/^__country(\d+)__$/);
      let code=marker?tokens[Number(marker[1])]:aliases.get(normal(part));
      // Accept a country with a qualified territorial scope, not arbitrary prose.
      if(!code){
        const match=part.match(/^([^()]+)\s*\(([^()]+)\)$/);
        if(match){
          code=aliases.get(normal(match[1]));
          if(!code&&/^[\p{L}\p{M} .'-]{1,80}$/u.test(match[1].trim())&&!/\b(mafia|firms?|companies|authors?|migrants?|diaspora|affiliations?)\b/i.test(match[1]))code=aliases.get(normal(match[2]));
        }
      }
      if(!code)code=aliases.get(normal(part.replace(/^(?:north(?:ern)?|south(?:ern)?|east(?:ern)?|west(?:ern)?|central|northern and southern|nord|sud|centro)\s+/i,'')));
      if(!code)return{countries:[],kind:'unresolved'};
      if(!result.includes(code))result.push(code);
    }
    return{countries:result.sort(),kind:result.length?'country':'unresolved'};
  }
  function fromResearch(payload){
    if(payload?.availability!=='available'||!payload.research)return{status:payload?.availability||'error',countries:[],studies:[]};
    const r=payload.research;
    if(r.assessment_state!=='unreviewed_proposal'||!Array.isArray(r.studies))throw Error('invalid_geography_projection');
    const spans=new Set((r.spans||[]).map(s=>s.id));
    const studies=r.studies.map((s,index)=>{
      const f=s.geography;
      const base={number:index+1,scope:typeof f?.value==='string'?f.value:null,countries:[],kind:f?.status||'missing'};
      if(f?.status!=='reported'||!f.value)return base;
      if(f.origin!=='source'||!Array.isArray(f.evidence_span_ids)||!f.evidence_span_ids.length||f.evidence_span_ids.some(id=>!spans.has(id)))return{...base,kind:'unverified'};
      return{...base,...parse(f.value)};
    });
    const countries=[...new Set(studies.flatMap(s=>s.countries))].sort();
    return{status:'available',countries,studies,partial:studies.some(s=>!s.countries.length),updatedAt:r.updated_at,coverage:r.source_coverage};
  }
  function aggregate(records,entries){
    const seen=new Set(),rows=new Map(),states=new Map();let total=0,known=0,partial=0;
    for(const record of records){
      if(seen.has(record.id))continue;seen.add(record.id);total++;
      const item=entries.get(record.id);
      const state=!item?'pending':item.countries?.length?'country':item.status==='available'?(item.studies?.length?([...new Set(item.studies.map(s=>s.kind))].join(' / ')):'no_study'):item.status;
      states.set(state,(states.get(state)||0)+1);
      if(!item?.countries?.length)continue;known++;if(item.partial)partial++;
      for(const code of new Set(item.countries)){
        if(!rows.has(code))rows.set(code,{code,name:names.get(code)||code,count:0,papers:[]});
        const row=rows.get(code);row.count++;row.papers.push({id:record.id,title:record.title,studies:item.studies.filter(s=>s.countries.includes(code)),updatedAt:item.updatedAt});
      }
    }
    return{total,known,partial,states:[...states].map(([status,count])=>({status,count})),rows:[...rows.values()].sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name,'it'))};
  }
  globalThis.CILEPaperGeography={parse,fromResearch,aggregate,name:code=>names.get(code)||code};
})();
