/* Read-only filters over the same identity-checked public data as the paper sheet. */
(() => {
  'use strict';
  const ENDPOINT = 'https://criminal-infiltration-curator.colazeta-research.workers.dev/api/public-paper-research';
  const CLASSES = {aetiology:'Eziologia', diagnosis:'Diagnosi', screening:'Screening', therapy:'Terapia', prognosis:'Prognosi', prevention:'Prevenzione'};
  const COVERAGE = {abstract_only:'solo abstract', partial_text:'testo parziale', full_text:'testo completo'};
  const SUMMARY_KINDS = new Set(['verified_abstract_source', 'publisher_summary', 'full_text_intro', 'review_synopsis']);
  const MODES = [
    ['all', 'Tutti i paper'], ['content', 'Già elaborati: sintesi o analisi'],
    ['summary', 'Con sintesi disponibile'], ['ai', 'Analizzati dall’AI: analisi strutturata'],
    ['ai_full_text', 'AI: testo completo'], ['ai_partial_text', 'AI: testo parziale'],
    ['ai_abstract_only', 'AI: solo abstract'], ['unavailable', 'Stato non verificabile / analisi non aggiornata'],
  ];
  const empty = () => ({support:'pending', summary:false, research:'pending', automated:false, coverage:null, classes:[], updatedAt:null});

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
    return {research:'available', automated:r.generation_kind === 'automated', coverage:r.source_coverage, classes, updatedAt:r.updated_at || null};
  }

  function matches(entry, mode='all', category='all') {
    const s = entry || empty();
    const available = s.research === 'available';
    const ai = available && s.automated;
    const modes = {
      all:true, content:s.summary || available, summary:s.summary, ai,
      ai_full_text:ai && s.coverage === 'full_text', ai_partial_text:ai && s.coverage === 'partial_text',
      ai_abstract_only:ai && s.coverage === 'abstract_only',
      unavailable:s.support === 'error' || ['error','stale','withheld'].includes(s.research),
    };
    return Boolean(Object.hasOwn(modes, mode) && modes[mode] && (category === 'all' || (available && s.classes.includes(category))));
  }

  function describe(entry) {
    if (!entry) return '';
    const parts = [];
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
      if (!response.ok) throw Error('public_data_unavailable');
      return await response.json();
    } finally { clearTimeout(timer); }
  }

  function createIndex(records, {read=readJSON, selectSupport, selectResearch, onUpdate=()=>{}}) {
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
      if (scanPromise) return scanPromise;
      Object.assign(progress, {running:true, scanned:false, attempted:0, checked:0, errors:0});
      for (const row of rows.values()) Object.assign(row, {research:'pending', automated:false, coverage:null, classes:[], updatedAt:null});
      scanPromise = (async () => {
        try {
          await loadSupport();
          let next = 0, consecutiveFailures = 0;
          async function worker() {
            while (next < records.length && consecutiveFailures < 4) {
              const record = records[next++], row = rows.get(record.id);
              try {
                const payload = await read(ENDPOINT + '?id=' + encodeURIComponent(record.id));
                Object.assign(row, researchState(selectResearch(payload, record)));
                progress.checked++; consecutiveFailures = 0;
              } catch {
                Object.assign(row, {research:'error', automated:false, coverage:null, classes:[], updatedAt:null});
                progress.errors++; consecutiveFailures++;
              }
              progress.attempted++;
              if (progress.attempted % 12 === 0) onUpdate();
            }
          }
          await Promise.all(Array.from({length:Math.min(4, records.length)}, worker));
        } finally {
          progress.running = false; progress.scanned = true; scanPromise = null; onUpdate();
        }
      })();
      onUpdate();
      return scanPromise;
    }
    return {rows, progress, loadSupport, scan};
  }

  function mount({controls, records, onChange, selectSupport, selectResearch}) {
    const el = (tag, text) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; return node; };
    const mode = el('select'), category = el('select');
    mode.id = 'register-processing-filter'; category.id = 'register-framework-filter';
    const addOption = (select, value, text) => { const option = el('option', text); option.value=value; select.append(option); };
    MODES.forEach(([value, text]) => addOption(mode, value, text));
    addOption(category, 'all', 'Tutte le classi proposte');
    Object.entries(CLASSES).forEach(([value, text]) => addOption(category, value, text));
    const first = el('label', 'Elaborazione del contenuto '); first.append(mode);
    const second = el('label', 'Classe proposta (principale o secondaria) '); second.append(category);
    const refresh = el('button', 'Aggiorna stato delle analisi'); refresh.type='button';
    const status = el('p'); status.id='register-processing-status'; status.setAttribute('role','status'); status.setAttribute('aria-live','polite');
    mode.setAttribute('aria-describedby', status.id); category.setAttribute('aria-describedby', status.id);
    const note = el('p', 'Una sintesi non equivale a una lettura completa. “Analizzati dall’AI” richiede un’estrazione strutturata con origine automatica attestata. Le classi restano proposte non validate scientificamente; i soli DOI, link, metadati e abstract reperiti non bastano.');
    const panel = el('section'); panel.setAttribute('aria-label','Stato dell’elaborazione dei paper'); panel.append(status, note);
    controls.append(first, second, refresh); controls.after(panel);
    let index;
    function update() {
      if (!index) return;
      const p = index.progress;
      const summaries = [...index.rows.values()].filter(s => s.summary).length;
      const ai = [...index.rows.values()].filter(s => matches(s, 'ai')).length;
      const supportErrors = [...index.rows.values()].filter(s => s.support === 'error').length;
      const supportChecked = [...index.rows.values()].filter(s => s.support === 'checked').length;
      const supportPending = [...index.rows.values()].filter(s => s.support === 'pending').length;
      const summaryText = supportChecked === p.total ? `${summaries} sintesi disponibili` : supportChecked ? `${summaries} sintesi trovate nei record verificati` : 'Disponibilità delle sintesi da verificare';
      const aiText = p.checked ? `${ai} analisi AI trovate nei record verificati` : 'Analisi AI da verificare';
      const lead = p.running ? 'Verifica in corso: risultati parziali. ' : p.scanned && p.checked < p.total ? 'Verifica incompleta: non interpretare gli stati mancanti come assenza di analisi. ' : '';
      status.textContent = lead + summaryText + ` · ${supportChecked}/${p.total} stati delle sintesi verificati · ` + aiText + ` · ${p.checked}/${p.total} stati analitici verificati.` +
        (supportPending ? ' Verifica delle sintesi in corso.' : '') +
        (supportErrors ? ` ${supportErrors} sintesi non verificabili.` : '') +
        (p.errors ? ` ${p.errors} richieste analitiche non riuscite.` : '') +
        (!p.scanned && !p.running ? ' Seleziona un filtro di analisi o premi Aggiorna per verificare l’intero registro.' : '');
      refresh.disabled = p.running;
      panel.setAttribute('aria-busy', String(p.running));
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
    return {
      matches:record => matches(index.rows.get(record.id), mode.value, category.value),
      describe:record => describe(index.rows.get(record.id)),
      emptyMessage:() => {
        if (mode.value === 'all' && category.value === 'all') return '';
        const incomplete = mode.value === 'summary' && category.value === 'all'
          ? [...index.rows.values()].some(row => row.support !== 'checked')
          : index.progress.running || index.progress.checked < records.length || (mode.value === 'content' && [...index.rows.values()].some(row => row.support !== 'checked'));
        return incomplete ? 'Nessuna corrispondenza verificata finora. La verifica dei contenuti non è completa: consulta lo stato sopra i risultati.' : '';
      },
    };
  }
  globalThis.CILEPaperProcessing = {researchState, matches, describe, readJSON, createIndex, mount};
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
  let opener = null;
  let sheetSequence = 0;
  dialog.addEventListener("close", () => { if (opener?.isConnected) opener.focus(); });

  function openSheet(record, button) {
    opener = button;
    const sequence = ++sheetSequence;
    dialog.replaceChildren();
    const bar = el("div");
    bar.className = "paper-sheet-bar";
    bar.append(el("span", "Archivio · Scheda bibliografica"));
    const close = el("button", "Chiudi ×");
    close.type = "button";
    close.addEventListener("click", () => dialog.close());
    bar.append(close);
    const body = el("div");
    body.className = "paper-sheet-body";
    const title = el("h2", record.title);
    title.id = "paper-sheet-title";
    body.append(title);
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
    body.append(metadata, research, support);
    body.append(el("h3", "Fonti registrate all’acquisizione"));
    for (const [index, url] of (record.sourceLinks || []).entries()) {
      try {
        const parsed = new URL(url);
        if (!["https:", "http:"].includes(parsed.protocol) || parsed.username || parsed.password) continue;
        const link = el("a", `Fonte ${index + 1} · ${parsed.hostname}`);
        link.href = parsed.href;
        link.rel = "noreferrer";
        const line = el("p"); line.append(link); body.append(line);
      } catch (_) { /* Invalid source URLs are never rendered. */ }
    }
    body.append(el("p", "La registrazione non equivale all’inclusione scientifica. Gli stati di verifica si riferiscono al singolo record."));
    dialog.append(bar, body);
    if (!dialog.open) dialog.showModal();
    close.focus();
    const isCurrent = () => dialog.open && sequence === sheetSequence;
    import("./paper-sheet-research.js")
      .then(() => globalThis.CILEPaperResearch.load(research, record, isCurrent))
      .catch(() => { if (isCurrent()) research.textContent = "Il pannello di ricerca non è disponibile; non è una conferma dell’assenza di analisi."; });
    import("./paper-sheet-support.js")
      .then(() => globalThis.CILEPaperSheetSupport.load(support, record, isCurrent))
      .catch(() => {
        if (isCurrent()) support.textContent = "Il pannello dei dati arricchiti non è disponibile. Ricarica la pagina; non è una conferma dell’assenza dell’abstract.";
      });
  }

  function render() {
    const found = filteredRecords();
    count.textContent = `${found.length} record visualizzati · ${records.length} registrati. L’analisi AI è distinta dalla revisione e dall’inclusione scientifica.`;
    list.replaceChildren();

    for (const record of found) {
      const row = document.createElement("tr");
      const citation = document.createElement("td");
      const open = el("button", "Apri scheda");
      open.type = "button";
      open.setAttribute("aria-haspopup", "dialog");
      open.setAttribute("aria-label", "Apri scheda: " + record.title);
      open.addEventListener("click", () => openSheet(record, open));
      row.addEventListener("dblclick", (event) => {
        if (!event.target.closest("a, button")) openSheet(record, open);
      });
      citation.append(
        el("strong", record.title),
        el("p", [record.authors, record.year, record.venue].filter(Boolean).join(" · ") || "Metadati da completare"),
      );
      citation.append(open);
      const status = el("td", reviewLabels[record.reviewStatus] || "Da verificare");
      if (record.topicCode) status.append(el("p", `Etichetta: ${record.topicCode}`));
      status.append(el("p", record.metadataStatus === "metadata_verified" ? "Metadati verificati" : "Metadati da verificare"));
      const processingLabel = processing?.describe(record);
      if (processingLabel) status.append(el("p", processingLabel));
      const access = el("td", accessLabels[record.accessStatus] || "Accesso da verificare");
      const links = document.createElement("td");
      for (const [index, url] of (record.sourceLinks || []).entries()) {
        try {
          const parsed = new URL(url);
          if (!["https:", "http:"].includes(parsed.protocol) || parsed.username || parsed.password) continue;
          const anchor = el("a", `Fonte ${index + 1}`);
          anchor.href = url;
          anchor.rel = "noreferrer";
          links.append(anchor, document.createElement("br"));
        } catch (_) {
          continue;
        }
      }
      const review = el("a", "Analizza nel curatore");
      review.href = "./curate.html";
      links.append(review);
      row.append(citation, status, access, links);
      list.append(row);
    }

    if (!found.length) {
      const row = document.createElement("tr");
      const cell = el("td", processing?.emptyMessage() || (records.length ? "Nessun record corrisponde ai filtri correnti." : "Nessun lavoro ancora registrato."));
      cell.colSpan = 4;
      row.append(cell);
      list.append(row);
    }
  }

  elements.search.addEventListener("input", (event) => { state.query = event.target.value; render(); });
  elements.year.addEventListener("change", (event) => { state.year = event.target.value; render(); });
  elements.author.addEventListener("change", (event) => { state.author = event.target.value; render(); });
  elements.venue.addEventListener("change", (event) => { state.venue = event.target.value; render(); });
  elements.review.addEventListener("change", (event) => { state.review = event.target.value; render(); });
  elements.access.addEventListener("change", (event) => { state.access = event.target.value; render(); });
  elements.sort.addEventListener("change", (event) => { state.sort = event.target.value; render(); });
  controls.addEventListener("reset", () => {
    window.setTimeout(() => {
      Object.assign(state, { query: "", year: "all", author: "all", venue: "all", review: "all", access: "all", sort: "newest" });
      render();
    });
  });

  fetch("./data/paper-register.json", { cache: "no-store" })
    .then((response) => {
      if (!response.ok) throw new Error("register unavailable");
      return response.json();
    })
    .then((payload) => {
      records = Array.isArray(payload.records) ? payload.records : [];
      populateFilters();
      render();
      Promise.all([import("./paper-sheet-support.js"), import("./paper-sheet-research.js")])
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
        });
    })
    .catch(() => {
      count.textContent = "Il registro non è disponibile. Consultare il pannello del curatore o riprovare.";
      Object.values(elements).forEach((element) => { if (element) element.disabled = true; });
    });
})();
