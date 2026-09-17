/* Read-only filters over the same identity-checked public data as the paper sheet. */
(() => {
  'use strict';
  const ENDPOINT = 'https://criminal-infiltration-curator.colazeta-research.workers.dev/api/public-paper-research';
  const CLASSES = {aetiology:'Eziologia', diagnosis:'Diagnosi', screening:'Screening', therapy:'Terapia', prognosis:'Prognosi', prevention:'Prevenzione'};
  const COVERAGE = {abstract_only:'solo abstract', partial_text:'testo parziale', full_text:'testo completo'};
  const SUMMARY_KINDS = new Set(['verified_abstract_source', 'publisher_summary', 'full_text_intro', 'review_synopsis']);
  const MODES = [
    ['all', 'Tutti i paper'], ['completed', 'Con validazione finale registrata'], ['content', 'Con sintesi o analisi dettagliata'],
    ['summary', 'Con sintesi disponibile'], ['ai', 'Con analisi automatica consultabile'],
    ['ai_full_text', 'AI: testo completo'], ['ai_partial_text', 'AI: testo parziale'],
    ['ai_abstract_only', 'AI: solo abstract'], ['unavailable', 'Stato non verificabile / analisi non aggiornata'],
  ];
  const empty = () => ({support:'pending', summary:false, research:'pending', automated:false, coverage:null, classes:[], updatedAt:null, researchRevision:null, completion:null, completionVerified:false});

  function researchState(data) {
    if (!data || !['available', 'not_assessed', 'not_registered', 'stale', 'withheld'].includes(data.availability)) throw Error('invalid_availability');
    const r = data.research;
    if (data.availability !== 'available') {
      if (r !== null) throw Error('invalid_research');
      return {research:data.availability, automated:false, coverage:null, classes:[], updatedAt:null};
    }
    if (!r || r.assessment_state !== 'unreviewed_proposal' || !Object.hasOwn(COVERAGE, r.source_coverage)) throw Error('invalid_research');
    const f = r.framework;
    if (!f || !['proposed', 'insufficient_evidence', 'outside_framework'].includes(f.status)) throw Error('invalid_framework');
    const classes = [];
    if (f.status === 'proposed') {
      if (!Object.hasOwn(CLASSES, f.primary) || !Array.isArray(f.secondary)) throw Error('invalid_class');
      classes.push(f.primary);
      for (const item of f.secondary) {
        if (!Object.hasOwn(CLASSES, item.category)) throw Error('invalid_class');
        if (!classes.includes(item.category)) classes.push(item.category);
      }
    }
    // Alternative coding and abstentions are not assigned contribution classes.
    return {research:'available', automated:r.generation_kind === 'automated', coverage:r.source_coverage, classes, updatedAt:r.updated_at || null, researchRevision:data.revision || null};
  }

  // All public views consume the accepted backend receipt, never a content heuristic.
  function completionState(value, researchRevision, available) {
    if(!value||!['accepted','not_attested','stale','withheld','not_registered'].includes(value.status)||typeof value.completed!=='boolean'||value.completed!==(value.status==='accepted')||!/^[a-f0-9]{64}$/.test(value.revision||''))throw Error('invalid_completion');
    if(value.completed&&(!available||value.research_revision!==researchRevision||!Number.isFinite(Date.parse(value.completed_at))||value.protocol_version!=='CILE-ENRICH-1'||value.codebook_version!=='1.0.0'))throw Error('completion_revision_mismatch');
    if(!value.completed&&(value.completed_at!==null||value.protocol_version!==null||value.codebook_version!==null))throw Error('false_completion_attestation');
    return value;
  }
  function isCompleted(entry) {
    if(!entry?.completionVerified)return false;
    try{return completionState(entry.completion,entry.researchRevision,entry.research==='available').completed}catch{return false}
  }
  function indexState(row,record) {
    const c=row?.candidate,normal=s=>String(s||'').trim().replace(/^https?:\/\/(?:dx\.)?doi\.org\//i,'').toLowerCase();
    if(!c||c.id!==record.id||c.title!==record.title||normal(c.doi)!==normal(record.doi)||JSON.stringify([...(c.sourceLinks||[])].sort())!==JSON.stringify([...(record.sourceLinks||[])].sort()))throw Error('index_identity_mismatch');
    if(!['available','not_assessed','not_registered','stale','withheld'].includes(row.availability)||!/^[a-f0-9]{64}$/.test(row.research_revision||'')||!Array.isArray(row.classes)||row.classes.some(k=>!Object.hasOwn(CLASSES,k)))throw Error('invalid_index_row');
    const available=row.availability==='available';
    if(available&&(!Object.hasOwn(COVERAGE,row.source_coverage)||!['automated','unspecified'].includes(row.generation_kind)||!['proposed','outside_framework','insufficient_evidence'].includes(row.framework_status)))throw Error('invalid_index_research');
    if(!available&&(row.source_coverage!==null||row.generation_kind!==null||row.framework_status!==null||row.classes.length)||row.framework_status!=='proposed'&&row.classes.length)throw Error('invalid_index_missingness');
    const completion=completionState(row.completion,row.research_revision,available);
    return {research:row.availability,automated:available&&row.generation_kind==='automated',coverage:row.source_coverage,classes:row.classes,updatedAt:null,
      researchRevision:row.research_revision,completion,completionVerified:true,referenceCoverage:row.reference_coverage};
  }

  function matches(entry, mode='all', category='all') {
    const s = entry || empty();
    const available = s.research === 'available';
    const ai = available && s.automated;
    const modes = {
      all:true, completed:isCompleted(s), content:s.summary || available, summary:s.summary, ai,
      ai_full_text:ai && s.coverage === 'full_text', ai_partial_text:ai && s.coverage === 'partial_text',
      ai_abstract_only:ai && s.coverage === 'abstract_only',
      unavailable:s.support === 'error' || ['error','stale','withheld'].includes(s.research),
    };
    return Boolean(Object.hasOwn(modes, mode) && modes[mode] && (category === 'all' || (available && s.classes.includes(category))));
  }

  function describe(entry) {
    if (!entry) return '';
    const parts = [];
    if (isCompleted(entry)) parts.push('Validazione finale registrata');
    if (entry.summary) parts.push('Sintesi disponibile');
    if (entry.research === 'available') {
      parts.push((entry.automated ? 'Analisi AI: ' : 'Analisi, origine non attestata: ') + COVERAGE[entry.coverage]);
      if (entry.classes.length) parts.push('Classi proposte: ' + entry.classes.map(k => CLASSES[k]).join(', '));
    } else if (entry.research === 'stale') parts.push('Analisi da aggiornare');
    else if (entry.research === 'withheld') parts.push('Analisi non pubblicabile dopo i controlli');
    else if (entry.research === 'error') parts.push('Stato dell’analisi non verificabile');
    else if (entry.research === 'not_assessed') parts.push('Nessuna analisi strutturata disponibile');
    else if (entry.research === 'not_registered') parts.push('Non presente nell’indice analitico');
    if (entry.support === 'error') parts.push('Stato della sintesi non verificabile');
    return parts.join(' · ');
  }

  async function readJSON(url, fetcher=globalThis.fetch) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetcher(url, {cache:'no-store', credentials:'omit', signal:controller.signal});
      if (!response.ok) throw Object.assign(Error('public_data_unavailable'),{status:response.status});
      return await response.json();
    } finally { clearTimeout(timer); }
  }

  function createIndex(records, {read=readJSON, selectSupport, selectResearch, loadSummaries=true, onUpdate=()=>{}}) {
    const rows = new Map();
    for (const record of records) {
      if (!record || typeof record.id !== 'string' || !record.id || rows.has(record.id)) throw Error('invalid_register_identity');
      rows.set(record.id, empty());
    }
    let supportPromise = null, scanPromise = null;
    const progress = {running:false, scanned:false, attempted:0, checked:0, errors:0, total:records.length};
    function loadSupport() {
      if (supportPromise) return supportPromise;
      for (const row of rows.values()) Object.assign(row, {support:'pending', summary:false});
      supportPromise = (async () => {
        try {
          const payload = await read('./paper-support.json');
          for (const record of records) {
            const row = rows.get(record.id);
            try {
              const support = selectSupport(payload, record);
              const aid = support.readingAid;
              Object.assign(row, {support:'checked', summary:Boolean(aid && SUMMARY_KINDS.has(aid.kind) && typeof aid.synopsis === 'string' && aid.synopsis.trim())});
            } catch { Object.assign(row, {support:'error', summary:false}); }
          }
        } catch {
          for (const row of rows.values()) Object.assign(row, {support:'error', summary:false});
        } finally { supportPromise = null; onUpdate(); }
      })();
      return supportPromise;
    }
    function scan() {
      if(scanPromise)return scanPromise;
      function reset(){
        Object.assign(progress,{running:true,scanned:false,attempted:0,checked:0,errors:0,pages:0,indexRevision:null,indexTotal:null});
        for(const row of rows.values())Object.assign(row,{research:'pending',automated:false,coverage:null,classes:[],updatedAt:null,researchRevision:null,completion:null,completionVerified:false});
      }
      reset();
      scanPromise=(async()=>{
        try {
          if(loadSummaries)await loadSupport();
          for(let restart=0;restart<2;restart++) {
            let cursor=0,revision=null;const seen=new Set();
            try {
              do {
                const page=await read(ENDPOINT+'?view=index&cursor='+cursor+(revision?'&revision='+revision:''));
                if(page?.schema_version!==1||page.projection_version!=='CILE-PUBLIC-INDEX-1'||!/^[a-f0-9]{64}$/.test(page.index_revision||'')||!Number.isSafeInteger(page.total)||page.total<0||page.total>10000||!Array.isArray(page.records)||page.records.length>50)throw Error('invalid_index_page');
                if(revision&&revision!==page.index_revision)throw Object.assign(Error('index_changed'),{status:409});
                if(page.next_cursor!==null&&(!Number.isSafeInteger(page.next_cursor)||page.next_cursor!==cursor+page.records.length||page.next_cursor<=cursor||page.next_cursor>page.total))throw Error('invalid_index_cursor');
                if(page.next_cursor===null&&cursor+page.records.length!==page.total)throw Error('incomplete_index_page');
                revision=page.index_revision;progress.indexRevision=revision;progress.indexTotal=page.total;progress.pages++;
                for(const item of page.records) {
                  const id=item?.candidate?.id;if(typeof id!=='string'||seen.has(id))throw Error('duplicate_index_identity');seen.add(id);
                  const record=records.find(r=>r.id===id);if(!record)continue;
                  progress.attempted++;
                  try{Object.assign(rows.get(id),indexState(item,record));progress.checked++}
                  catch{Object.assign(rows.get(id),{research:'error',completion:null,completionVerified:false});progress.errors++}
                }
                cursor=page.next_cursor;onUpdate();
              }while(cursor!==null);
              break;
            }catch(error) {
              if(error.status===409&&restart===0){reset();onUpdate();continue}
              throw error;
            }
          }
        }catch{progress.errors++}
        finally{progress.running=false;progress.scanned=true;scanPromise=null;onUpdate()}
      })();
      onUpdate();return scanPromise;
    }
    return {rows, progress, loadSupport, scan};
  }


  // UI-only view model. A finished read is not completed research. The legacy
  // completed receipt below denotes validation, not F5 assessment completion.
  function overview(index) {
    const rows=[...index.rows.values()],p=index.progress,total=p.total;
    const received=rows.filter(row=>row.completionVerified===true &&
      ['available','not_assessed','not_registered','stale','withheld'].includes(row.research)).length;
    const ready=p.scanned===true && !p.running && !p.errors &&
      received===total && p.checked===total && rows.length===total;
    const phase=total===0?'empty':p.running?'loading':ready?'ready':
      !p.scanned?'idle':received?'partial':'error';
    const summaryKnown=rows.length===total && rows.every(row=>row.support==='checked');
    const summaries=summaryKnown?rows.filter(row=>row.summary).length:null;
    const messages={
      empty:'Nessun paper nel registro.',
      idle:'Il riepilogo delle analisi dettagliate non è ancora stato caricato.',
      loading:'Caricamento del riepilogo delle analisi…',
      partial:'Il caricamento del riepilogo non è completo. I totali non sono disponibili: riprova.',
      error:'Non è stato possibile caricare il riepilogo delle analisi. Riprova.',
      ready:'Riepilogo delle schede strutturate caricato. Le annotazioni di lettura aggiunte separatamente non sono incluse.',
    };
    const available=rows.filter(row=>row.research==='available');
    const canCount=ready && total>0;
    return {
      phase,total,received,ready:canCount,summaries,
      summaryText:summaries===null?'Disponibilità delle sintesi non ancora confermata.':`${summaries} sintesi disponibili nel registro.`,
      message:messages[phase],
      action:p.running?'Caricamento…':phase==='idle'?'Carica riepilogo analisi':
        ['partial','error'].includes(phase)?'Riprova caricamento':'Aggiorna riepilogo',
      // Never publish partial or unavailable counters as full-population totals.
      analyses:canCount?available.length:null,
      fullText:canCount?available.filter(row=>row.coverage==='full_text').length:null,
      categories:canCount?available.filter(row=>row.classes.length).length:null,
      references:canCount && rows.every(row=>Array.isArray(row.referenceCoverage))?
        rows.filter(row=>row.referenceCoverage.length).length:null,
      validated:canCount?rows.filter(isCompleted).length:null,
      assessmentComplete:null, // Not exposed by CILE-PUBLIC-INDEX-1.
    };
  }
  function overviewBreakdown(view) {
    if(!view.ready)return '';
    return `Analisi dettagliate consultabili: ${view.analyses}; di cui ${view.fullText} basate sul testo completo. Paper con categorie proposte: ${view.categories}. `+
      (view.references===null?'Copertura dei riferimenti non disponibile nel riepilogo.':`Paper con copertura dei riferimenti registrata: ${view.references}.`);
  }

  function mount({controls, records, onChange, selectSupport, selectResearch}) {
    const el = (tag, text) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; return node; };
    const mode = el('select'), category = el('select');
    mode.id = 'register-processing-filter'; category.id = 'register-framework-filter';
    const addOption = (select, value, text) => { const option = el('option', text); option.value=value; select.append(option); };
    MODES.forEach(([value, text]) => addOption(mode, value, text));
    addOption(category, 'all', 'Tutte le classi proposte');
    Object.entries(CLASSES).forEach(([value, text]) => addOption(category, value, text));
    const first = el('label'); first.append(el('span', 'Contenuto disponibile'), mode);
    const second = el('label'); second.append(el('span', 'Classe proposta'), category);
    const refresh = el('button', 'Carica riepilogo analisi'); refresh.type='button';
    const status = el('p'); status.id='register-processing-status'; status.setAttribute('role','status'); status.setAttribute('aria-live','polite');
    mode.setAttribute('aria-describedby', status.id); category.setAttribute('aria-describedby', status.id);
    status.setAttribute('aria-atomic','true');
    const completion = el('p'); completion.id='register-completion-status'; completion.hidden=true;
    const breakdown = el('p'); breakdown.id='register-enrichment-breakdown'; breakdown.hidden=true;
    const note=el('p','Le analisi e le categorie consultabili possono essere proposte non ancora validate scientificamente.');
    const help=el('a','Come leggere disponibilità, completamento e validazione');help.href='./method.html#reading-status';
    const panel = el('details'); panel.className='processing-details'; panel.setAttribute('aria-label','Riepilogo delle analisi');
    const summary=el('summary','Riepilogo delle analisi');
    const diagnostics=el('details');diagnostics.append(el('summary','Dettagli del caricamento'));
    const transport=el('p');diagnostics.append(transport);
    panel.append(summary, refresh, status, completion, breakdown, note, help, diagnostics);
    (controls.querySelector('.register-filter-grid') || controls).append(first, second); controls.after(panel);
    let index;
    function update() {
      if (!index) return;
      const view=overview(index),p=index.progress;
      const summaryMetric=document.getElementById('register-summary-count');
      if(summaryMetric){summaryMetric.textContent=view.summaries===null?'—':String(view.summaries);summaryMetric.title='Sintesi presenti nei dati bibliografici del registro; non misura il completamento delle analisi.';}
      const message=view.summaryText+' '+view.message;
      if(status.textContent!==message)status.textContent=message;
      completion.hidden=breakdown.hidden=!view.ready;
      completion.textContent=view.ready?`Validazione finale registrata per ${view.validated} di ${view.total} paper. Il numero di analisi completate non è disponibile in questo riepilogo.`:'';
      breakdown.textContent=overviewBreakdown(view);
      const supportRead=[...index.rows.values()].filter(row=>row.support==='checked').length;
      transport.textContent=`Disponibilità delle sintesi letta per ${supportRead} di ${p.total} record. `+
        (view.phase==='idle'?'Lettura delle analisi non avviata.':`Dati delle analisi ricevuti per ${view.received} di ${p.total} record.`)+
        ' Questi numeri descrivono il caricamento della pagina, non l’avanzamento della ricerca.';
      summary.textContent=view.phase==='loading'?'Riepilogo delle analisi · caricamento…':'Riepilogo delle analisi';
      refresh.textContent=view.action;refresh.disabled=p.running || p.total===0;
      // The live status remains outside aria-busy so failures/loading are announced.
      onChange();
    }
    index = createIndex(records, {selectSupport, selectResearch, onUpdate:update});
    function changed() {
      if ((category.value !== 'all' || !['all','summary'].includes(mode.value)) && !index.progress.scanned) index.scan();
      update();
    }
    mode.addEventListener('change', changed); category.addEventListener('change', changed);
    refresh.addEventListener('click', () => index.scan());
    controls.addEventListener('reset', () => { mode.value='all'; category.value='all'; update(); });
    index.loadSupport(); update();
    function incomplete() {
      if(!records.length || (mode.value==='all' && category.value==='all'))return false;
      const supportMissing=[...index.rows.values()].some(row=>row.support!=='checked');
      if(mode.value==='summary' && category.value==='all')return supportMissing;
      return !overview(index).ready || (mode.value==='content' && supportMissing);
    }
    return {
      matches:record => matches(index.rows.get(record.id), mode.value, category.value),
      describe:record => describe(index.rows.get(record.id)),
      incomplete,
      emptyMessage:() => {
        if(incomplete())return index.progress.running?'Caricamento dei dati necessari per questi filtri…':
          'I risultati di questi filtri non sono ancora disponibili per tutti i paper. Carica o aggiorna il riepilogo delle analisi.';
        if(mode.value==='completed')return 'Nessuna validazione finale registrata per i paper che corrispondono ai filtri. Non è un conteggio delle analisi completate.';
        return '';
      },
    };
  }

  // Pagination is presentation-only: never truncate or mutate the source registry.
  function pageRecords(records, requestedPage=1, size=25) {
    if(!Array.isArray(records)||![25,50,100].includes(size))throw Error('invalid_pagination');
    const pages=Math.max(1,Math.ceil(records.length/size));
    const page=Math.max(1,Math.min(Number.isSafeInteger(requestedPage)?requestedPage:1,pages));
    const start=(page-1)*size;
    return {page,pages,start,rows:records.slice(start,start+size),total:records.length};
  }
  globalThis.CILEPaperProcessing = {researchState, matches, describe, readJSON, createIndex, mount, isCompleted, completionState, indexState, pageRecords, overview, overviewBreakdown, hasRecordedValidation:isCompleted};
})();

(() => {
  const list = document.querySelector("#registered-papers");
  const controls = document.querySelector("#register-controls");
  const count = document.querySelector("#register-count");
  if (!list || !controls || !count) return;

  const elements = {
    search: document.querySelector("#register-search"),
    year: document.querySelector("#register-year-filter"),
    author: document.querySelector("#register-author-filter"),
    venue: document.querySelector("#register-venue-filter"),
    review: document.querySelector("#register-review-filter"),
    access: document.querySelector("#register-access-filter"),
    sort: document.querySelector("#register-sort-order"),
  };

  const reviewLabels = {
    pending: "Da valutare scientificamente",
    needs_full_text: "Testo da esaminare",
    screened_eligible_core: "Valutato: core",
    screened_eligible_contextual: "Valutato: contestuale",
    screened_not_eligible: "Escluso",
    duplicate_confirmed: "Duplicato confermato",
    screened_not_academic: "Non accademico",
    screened_not_retrievable: "Non reperibile",
  };
  const accessLabels = {
    unknown: "Accesso da verificare",
    verification_pending: "Verifica accesso pendente",
    verified_open: "OA verificato",
    not_open: "Non open access",
  };

  const state = {
    query: "",
    year: "all",
    author: "all",
    venue: "all",
    review: "all",
    access: "all",
    sort: "newest",
  };
  let records = [];
  let processing = null;
  let workspace = null;
  let currentPage = 1;
  let pageSize = 25;
  let searchTimer = null;
  document.querySelectorAll('form[role="search"]').forEach(form => form.addEventListener('submit', event => event.preventDefault()));

  const el = (tag, text) => {
    const node = document.createElement(tag);
    node.textContent = text;
    return node;
  };

  function splitAuthors(value) {
    return String(value || "")
      .split(";")
      .map((author) => author.trim())
      .filter(Boolean);
  }

  function addOption(select, value, label) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.append(option);
  }

  function populateFilters() {
    const years = [...new Set(records.map((record) => record.year).filter(Boolean))].sort((a, b) => b - a);
    years.forEach((year) => addOption(elements.year, String(year), String(year)));

    const authors = [...new Set(records.flatMap((record) => splitAuthors(record.authors)))].sort((a, b) => a.localeCompare(b, "it"));
    authors.forEach((author) => addOption(elements.author, author, author));

    const venues = [...new Set(records.map((record) => String(record.venue || "").trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, "it"));
    venues.forEach((venue) => addOption(elements.venue, venue, venue));

    const reviewStates = [...new Set(records.map((record) => record.reviewStatus).filter(Boolean))].sort();
    reviewStates.forEach((value) => addOption(elements.review, value, reviewLabels[value] || value));

    const accessStates = [...new Set(records.map((record) => record.accessStatus).filter(Boolean))].sort();
    accessStates.forEach((value) => addOption(elements.access, value, accessLabels[value] || value));
  }

  function filteredRecords() {
    const query = state.query.trim().toLocaleLowerCase("it");
    const found = records.filter((record) => {
      const haystack = [record.title, record.authors, record.doi, record.year, record.venue, record.topicCode]
        .join(" ")
        .toLocaleLowerCase("it");
      return (
        (!query || haystack.includes(query)) &&
        (state.year === "all" || String(record.year) === state.year) &&
        (state.author === "all" || splitAuthors(record.authors).includes(state.author)) &&
        (state.venue === "all" || String(record.venue || "").trim() === state.venue) &&
        (state.review === "all" || record.reviewStatus === state.review) &&
        (state.access === "all" || record.accessStatus === state.access) &&
        (!processing || processing.matches(record))
      );
    });

    return found.sort((a, b) => {
      if (state.sort === "title") return String(a.title || "").localeCompare(String(b.title || ""), "it");
      const direction = state.sort === "oldest" ? 1 : -1;
      return ((Number(a.year) || 0) - (Number(b.year) || 0)) * direction || String(a.title || "").localeCompare(String(b.title || ""), "it");
    });
  }

  const dialog = document.createElement("dialog");
  dialog.className = "paper-sheet";
  dialog.setAttribute("aria-labelledby", "paper-sheet-title");
  document.body.append(dialog);
  let opener = null, openedRecordId = null;
  let sheetSequence = 0;
  dialog.addEventListener('click', event => {
    const box=dialog.getBoundingClientRect();
    if(event.target===dialog&&(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)) dialog.close();
  });
  dialog.addEventListener("close", () => {
    workspace?.sheetClosed();
    const target=opener?.isConnected?opener:[...list.querySelectorAll("button[data-record-id]")].find(button=>button.dataset.recordId===openedRecordId);
    (target || elements.search).focus();
  });

  function openSheet(record, button) {
    opener = button;openedRecordId=record.id;
    const sequence = ++sheetSequence;
    dialog.replaceChildren();
    const bar = el("div");
    bar.className = "paper-sheet-bar";
    bar.append(el("span", "Archivio · Scheda di ricerca"));
    const close = el("button", "Chiudi ×");
    close.type = "button";
    close.addEventListener("click", () => dialog.close());
    bar.append(close);
    const body = el("div");
    body.className = "paper-sheet-body";
    const title = el("h2", record.title);
    title.id = "paper-sheet-title";
    body.append(title);
    const citation=el('p',[record.authors,record.year,record.venue].filter(Boolean).join(' · ')); citation.className='sheet-citation'; body.append(citation);
    const boundary=el('p','Revisione scientifica: '+(reviewLabels[record.reviewStatus]||'Da verificare')+'. Le analisi proposte non equivalgono all’inclusione nel corpus.'); boundary.className='sheet-boundary'; body.append(boundary);
    const metadata = el("dl");
    for (const [label, value] of [
      ["Autori", record.authors], ["Anno", record.year], ["Rivista / sede", record.venue],
      ["DOI", record.doi], ["Identificativo", record.id],
      ["Registrato il", record.registeredAt],
      ["Stato della revisione", reviewLabels[record.reviewStatus] || record.reviewStatus],
      ["Verifica dei metadati", record.metadataStatus === "metadata_verified" ? "Verificati" : "Da verificare"],
      ["Accesso all’acquisizione", accessLabels[record.accessStatus] || "Da verificare"],
      ["Etichetta assegnata", record.topicCode],
    ]) {
      metadata.append(el("dt", label), el("dd", value || "Non disponibile"));
    }
    const support = el("section", "Caricamento dei dati arricchiti…");
    support.setAttribute("aria-live", "polite");
    const research = el("section", "Caricamento del contesto di ricerca…");
    research.setAttribute("aria-live", "polite");
    research.className = "paper-research";
    support.className='paper-support';
    const provenance=el('details');provenance.className='sheet-provenance';provenance.append(el('summary','Identità bibliografica, stati e fonti del registro'),metadata);
    body.append(support,research,provenance);
    provenance.append(el("h3", "Fonti registrate all’acquisizione"));
    for (const [index, url] of (record.sourceLinks || []).entries()) {
      try {
        const parsed = new URL(url);
        if (!["https:", "http:"].includes(parsed.protocol) || parsed.username || parsed.password) continue;
        const link = el("a", `Fonte ${index + 1} · ${parsed.hostname}`);
        link.href = parsed.href;
        link.rel = "noreferrer";
        const line = el("p"); line.append(link); provenance.append(line);
      } catch (_) { /* Invalid source URLs are never rendered. */ }
    }
    body.append(el("p", "La registrazione non equivale all’inclusione scientifica. Gli stati di verifica si riferiscono al singolo record."));
    dialog.append(bar, body);
    if (!dialog.open) dialog.showModal();
    dialog.scrollTop=0;
    close.focus();
    workspace?.sheetOpened(record);
    const isCurrent = () => dialog.open && sequence === sheetSequence;
    import("./paper-sheet-research.js?v=frontend-20260917-status3")
      .then(() => globalThis.CILEPaperResearch.load(research, record, isCurrent))
      .catch(() => { if (isCurrent()) research.textContent = "Il pannello di ricerca non è disponibile; non è una conferma dell’assenza di analisi."; });
    import("./paper-sheet-support.js?v=frontend-20260917-status3")
      .then(() => globalThis.CILEPaperSheetSupport.load(support, record, isCurrent))
      .catch(() => {
        if (isCurrent()) support.textContent = "Il pannello dei dati arricchiti non è disponibile. Ricarica la pagina; non è una conferma dell’assenza dell’abstract.";
      });
  }

  const pager=document.createElement('div');pager.className='register-pagination';pager.setAttribute('role','group');pager.setAttribute('aria-label','Paginazione del registro');pager.hidden=true;
  const pageStatus=el('span');pageStatus.id='register-page-status';pageStatus.setAttribute('aria-live','polite');
  const previous=el('button','← Precedente'),next=el('button','Successiva →');previous.type=next.type='button';
  const sizeLabel=el('label','Per pagina '),sizeSelect=document.createElement('select');sizeSelect.id='register-page-size';
  for(const value of [25,50,100])addOption(sizeSelect,String(value),String(value));sizeLabel.append(sizeSelect);
  pager.append(pageStatus,sizeLabel,previous,next);list.closest('.table-scroll').after(pager);
  function changePage(delta){currentPage=globalThis.CILEPaperProcessing.pageRecords(filteredRecords(),currentPage,pageSize).page+delta;render();count.scrollIntoView({block:'nearest'});}
  previous.addEventListener('click',()=>changePage(-1));next.addEventListener('click',()=>changePage(1));
  sizeSelect.addEventListener('change',()=>{pageSize=Number(sizeSelect.value);currentPage=1;render();});
  controls.addEventListener('change',event=>{if(event.target.tagName==='SELECT'){currentPage=1;render();}});

  function render() {
    const found = filteredRecords();
    const page=globalThis.CILEPaperProcessing.pageRecords(found,currentPage,pageSize);
    const {pages,start,rows:visible}=page;
    count.textContent = processing?.incomplete()?
      (found.length?`${found.length} risultati nei dati già caricati · riepilogo incompleto`:'Risultati dei filtri non ancora disponibili · riepilogo incompleto'):
      `${found.length} record corrispondenti · ${records.length} registrati`;
    pageStatus.textContent=found.length?`${start+1}–${start+visible.length} di ${found.length} · Pagina ${page.page} di ${pages}`:'Nessun risultato';
    previous.disabled=page.page===1;next.disabled=page.page===pages;pager.hidden=found.length===0;
    const active=document.getElementById('register-active-filters');
    if(active){const n=[...controls.querySelectorAll('.register-filter-grid select')].filter(select=>select.value!=='all').length;active.textContent=n?` · ${n} attivi`:'';}
    const fragment=document.createDocumentFragment();
    for (const record of visible) {
      const row = document.createElement('tr');
      const citation = document.createElement('td');citation.className='register-citation';
      const open = el('button',record.title);open.className='paper-title';open.type='button';
      open.dataset.recordId=record.id;open.setAttribute('aria-haspopup','dialog');open.setAttribute('aria-label','Apri scheda: '+record.title);
      open.addEventListener('click',()=>openSheet(record,open));
      row.addEventListener('dblclick',event=>{if(!event.target.closest('a, button'))openSheet(record,open);});
      citation.append(open,el('p',[record.authors,record.year,record.venue].filter(Boolean).join(' · ')||'Metadati da completare'));
      const status=el('td');status.dataset.label='Revisione e analisi';
      const reviewState=el('span',reviewLabels[record.reviewStatus]||'Da verificare');reviewState.className='review-label';status.append(reviewState);
      if(record.topicCode)status.append(el('p',`Etichetta: ${record.topicCode}`));
      status.append(el('p',record.metadataStatus==='metadata_verified'?'Metadati verificati':'Metadati da verificare'));
      const processingLabel=processing?.describe(record);if(processingLabel)status.append(el('p',processingLabel));
      const access=el('td',accessLabels[record.accessStatus]||'Accesso da verificare');access.dataset.label='Accesso all’acquisizione';
      const links=document.createElement('td');links.dataset.label='Fonti';
      for(const [index,url]of(record.sourceLinks||[]).entries()){
        try{const parsed=new URL(url);if(!['https:','http:'].includes(parsed.protocol)||parsed.username||parsed.password)continue;
          const anchor=el('a',`Fonte ${index+1}`);anchor.href=url;anchor.rel='noreferrer';anchor.title=parsed.hostname;links.append(anchor,document.createElement('br'));
        }catch{continue;}
      }
      row.append(citation,status,access,links);fragment.append(row);
    }
    if(!found.length){
      const row=document.createElement('tr'),cell=el('td',processing?.emptyMessage()||(records.length?'Nessun record corrisponde ai filtri correnti. Azzera i filtri per tornare al registro.':'Nessun lavoro ancora registrato.'));
      cell.colSpan=4;cell.className='register-empty';row.append(cell);fragment.append(row);
    }
    list.replaceChildren(fragment);list.setAttribute('aria-busy','false');
  }

  elements.search.addEventListener("input", (event) => { state.query = event.target.value; currentPage=1; clearTimeout(searchTimer); searchTimer=setTimeout(render,120); });
  elements.year.addEventListener("change", (event) => { state.year = event.target.value; render(); });
  elements.author.addEventListener("change", (event) => { state.author = event.target.value; render(); });
  elements.venue.addEventListener("change", (event) => { state.venue = event.target.value; render(); });
  elements.review.addEventListener("change", (event) => { state.review = event.target.value; render(); });
  elements.access.addEventListener("change", (event) => { state.access = event.target.value; render(); });
  elements.sort.addEventListener("change", (event) => { state.sort = event.target.value; render(); });
  controls.addEventListener("reset", () => {
    window.setTimeout(() => {
      clearTimeout(searchTimer);currentPage=1;
      Object.assign(state, { query: "", year: "all", author: "all", venue: "all", review: "all", access: "all", sort: "newest" });
      render();
    });
  });

  function connectWorkspace() {
    if(!globalThis.CILEWorkspace)return;
    workspace=globalThis.CILEWorkspace.attach({
      controls,pager,dialog,getRecords:()=>records,
      getState:()=>({...state,page:currentPage,size:pageSize,
        content:document.getElementById('register-processing-filter')?.value||'all',
        category:document.getElementById('register-framework-filter')?.value||'all'}),
      applyState:view=>{
        clearTimeout(searchTimer);
        const ignored=[];
        state.query=view.query;elements.search.value=view.query;
        for(const key of ['year','author','venue','review','access','sort']) {
          const fallback=key==='sort'?'newest':'all',select=elements[key];
          const valid=[...select.options].some(option=>option.value===view[key]);
          state[key]=valid?view[key]:fallback;select.value=state[key];
          if(!valid)ignored.push(key);
        }
        for(const [key,id] of [['content','register-processing-filter'],['category','register-framework-filter']]) {
          const select=document.getElementById(id);
          const valid=select && [...select.options].some(option=>option.value===view[key]);
          if(select)select.value=valid?view[key]:'all';
          if(!valid && view[key]!=='all')ignored.push(key);
        }
        document.getElementById('register-processing-filter')?.dispatchEvent(new Event('change',{bubbles:true}));
        currentPage=view.page;pageSize=view.size;sizeSelect.value=String(pageSize);
        if([...controls.querySelectorAll('.register-filter-grid select')].some(select=>select.value!=='all'))document.getElementById('register-filter-panel').open=true;
        render();return ignored;
      },
      openPaper:record=>openSheet(record,null),
    });
  }

  fetch("./data/paper-register.json", { cache: "no-store" })
    .then((response) => {
      if (!response.ok) throw new Error("register unavailable");
      return response.json();
    })
    .then((payload) => {
      if(payload.schemaVersion!==1||!Array.isArray(payload.records))throw Error("invalid_register");
      const ids=new Set();
      for(const record of payload.records){
        if(!record||typeof record.id!=="string"||!record.id||ids.has(record.id)||typeof record.title!=="string"||!Array.isArray(record.sourceLinks))throw Error("invalid_register_identity");
        ids.add(record.id);
      }
      records = payload.records;
      const total=document.getElementById('register-total-count'),verified=document.getElementById('register-metadata-count');
      if(total)total.textContent=String(records.length);
      if(verified)verified.textContent=String(records.filter(record=>record.metadataStatus==='metadata_verified').length);
      populateFilters();
      render();
      Promise.all([import("./paper-sheet-support.js?v=frontend-20260917-status3"), import("./paper-sheet-research.js?v=frontend-20260917-status3")])
        .then(() => {
          processing = globalThis.CILEPaperProcessing.mount({
            controls, records, onChange: render,
            selectSupport: globalThis.CILEPaperSheetSupport.selectRecord,
            selectResearch: globalThis.CILEPaperResearch.selectRecord,
          });
          render();
        })
        .catch(() => {
          count.after(el("p", "Il filtro di elaborazione non è disponibile. Questo non significa che i paper non siano stati analizzati."));
        }).finally(connectWorkspace);
    })
    .catch(() => {
      list.replaceChildren();list.setAttribute("aria-busy","false");pager.hidden=true;
      count.textContent = "Il registro non è disponibile. Consultare il pannello del curatore o riprovare.";
      Object.values(elements).forEach((element) => { if (element) element.disabled = true; });
    });
})();
