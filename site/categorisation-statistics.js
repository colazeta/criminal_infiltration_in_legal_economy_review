/* Statistics derived from the six-class scientific contribution framework.
   Uses the same selected bibliometric population and the public, read-only index. */
(() => {
  'use strict';

  const API = 'https://criminal-infiltration-curator.colazeta-research.workers.dev/api/public-paper-research';
  const CLASS_ENTRIES = [
    ['aetiology', 'Eziologia'],
    ['diagnosis', 'Diagnosi'],
    ['screening', 'Screening'],
    ['therapy', 'Terapia'],
    ['prognosis', 'Prognosi'],
    ['prevention', 'Prevenzione'],
  ];
  const CLASS_LABELS = Object.fromEntries(CLASS_ENTRIES);
  const CLASS_KEYS = new Set(CLASS_ENTRIES.map(([key]) => key));
  const AVAILABILITY = new Set(['available', 'not_assessed', 'not_registered', 'stale', 'withheld']);
  const FRAMEWORK_STATUS = new Set(['proposed', 'insufficient_evidence', 'outside_framework']);
  const STATE_LABELS = {
    classified: 'Categoria proposta',
    insufficient_evidence: 'Evidenza insufficiente per classificare',
    outside_framework: 'Contributo proposto come esterno al framework',
    not_assessed: 'Estrazione non ancora disponibile',
    not_registered: 'Scheda analitica non associata',
    stale: 'Analisi non aggiornata',
    withheld: 'Analisi non pubblicabile',
    not_in_index: 'Record non presente nell’indice analitico pubblico',
  };

  const anchor = document.querySelector('#author-evolution-title')?.closest('article');
  if (!anchor) return;

  const el = (tag, text) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const format = new Intl.NumberFormat('it-IT', { maximumFractionDigits: 1 });
  const pct = (value, denominator) => denominator ? `${format.format((value / denominator) * 100)}%` : '—';
  const yearOf = (record) => {
    const value = Number(record?.year);
    return Number.isInteger(value) && value > 0 ? value : null;
  };

  const host = el('section');
  host.id = 'categorisation-statistics';
  host.className = 'statistics-section';
  host.setAttribute('aria-labelledby', 'categorisation-statistics-title');

  const heading = el('div');
  heading.className = 'section-heading';
  const headingText = el('div');
  headingText.append(el('p', 'Struttura dei contributi scientifici'));
  headingText.firstChild.className = 'eyebrow';
  const title = el('h3', 'Statistiche della categorizzazione dei paper');
  title.id = 'categorisation-statistics-title';
  headingText.append(title);
  heading.append(
    headingText,
    el('p', 'Le sei classi descrivono il contributo scientifico proposto del paper, non la sua eleggibilità nella review. Le statistiche seguono lo stesso perimetro selezionato nelle statistiche bibliometriche.'),
  );

  const status = el('p');
  status.className = 'bibliometric-note';
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  const refresh = el('button', 'Ricarica categorie');
  refresh.type = 'button';

  const metrics = el('section');
  metrics.className = 'metrics stats-metrics';
  metrics.setAttribute('aria-label', 'Indicatori della categorizzazione');
  const metricNodes = {};
  const metric = (key, label) => {
    const article = el('article');
    const value = el('span', '—');
    value.id = `categorisation-${key}`;
    metricNodes[key] = value;
    article.append(value, el('p', label));
    return article;
  };
  metrics.append(
    metric('classified', 'paper con categoria proposta'),
    metric('coverage', 'quota con categoria tra le schede lette'),
    metric('multi', 'paper con almeno una classe secondaria'),
    metric('represented', 'classi primarie rappresentate su 6'),
  );

  const content = el('div');
  const empty = el('div');
  empty.className = 'empty-state';
  empty.hidden = true;
  empty.append(el('h4', 'Nessun record nella vista selezionata'), el('p', 'Le statistiche di categorizzazione appariranno quando la vista bibliometrica contiene almeno un record.'));

  const errorBox = el('div');
  errorBox.className = 'empty-state error-state';
  errorBox.hidden = true;
  errorBox.append(el('h4', 'Le categorizzazioni non possono essere caricate'), el('p', 'Nessun valore viene stimato: riprova con “Ricarica categorie”.'));

  const categoryPanel = el('article');
  categoryPanel.className = 'bibliometric-panel';
  categoryPanel.append(
    el('h4', 'Distribuzione delle sei classi'),
    el('p', 'Ogni paper classificato contribuisce una volta alla colonna “Primaria”. Le classi secondarie sono contate separatamente; per questo il totale “Primaria o secondaria” può superare il numero di paper classificati.'),
  );
  const categoryTableHost = el('div');
  categoryTableHost.className = 'table-scroll';
  categoryPanel.append(categoryTableHost);

  const evolutionPanel = el('article');
  evolutionPanel.className = 'bibliometric-panel';
  evolutionPanel.append(
    el('h4', 'Evoluzione per anno della classe primaria'),
    el('p', 'Sono mostrati soltanto gli anni con almeno un paper classificato nella vista corrente; l’anno è quello di pubblicazione del record bibliografico.'),
  );
  const evolutionHost = el('div');
  evolutionPanel.append(evolutionHost);

  const combinationPanel = el('article');
  combinationPanel.className = 'bibliometric-panel';
  combinationPanel.append(
    el('h4', 'Combinazioni di classi'),
    el('p', 'Le combinazioni mantengono distinta la classe primaria dalle secondarie e mostrano quanto spesso i paper attraversano più dimensioni del framework.'),
  );
  const combinationHost = el('div');
  combinationHost.className = 'table-scroll';
  combinationPanel.append(combinationHost);

  const statePanel = el('details');
  const stateSummary = el('summary', 'Copertura e stati della categorizzazione');
  const stateHost = el('div');
  statePanel.append(stateSummary, stateHost);

  content.append(categoryPanel, evolutionPanel, combinationPanel, statePanel);
  host.append(heading, status, refresh, metrics, empty, errorBox, content);
  anchor.after(host);

  let selected = [];
  let indexRows = new Map();
  let loaded = false;
  let running = false;
  let loadError = false;

  function validateIndexRow(row) {
    const id = row?.candidate?.id;
    if (typeof id !== 'string' || !/^CAND-[A-Za-z0-9-]{1,100}$/.test(id)) throw Error('invalid_index_identity');
    if (!AVAILABILITY.has(row.availability)) throw Error('invalid_index_availability');
    if (!Array.isArray(row.classes) || row.classes.some((key) => !CLASS_KEYS.has(key))) throw Error('invalid_index_classes');
    if (new Set(row.classes).size !== row.classes.length) throw Error('duplicate_index_class');
    if (row.availability === 'available') {
      if (!FRAMEWORK_STATUS.has(row.framework_status)) throw Error('invalid_framework_status');
      if (row.framework_status === 'proposed' && row.classes.length === 0) throw Error('missing_primary_class');
      if (row.framework_status !== 'proposed' && row.classes.length !== 0) throw Error('unexpected_classes');
    } else if (row.framework_status !== null || row.classes.length !== 0) {
      throw Error('invalid_missingness');
    }
    return {
      id,
      availability: row.availability,
      frameworkStatus: row.framework_status,
      primary: row.classes[0] || null,
      secondary: row.classes.slice(1),
    };
  }

  async function readJSON(url) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch(url, { cache: 'no-store', credentials: 'omit', signal: controller.signal });
      if (!response.ok) throw Object.assign(Error('categorisation_index_unavailable'), { status: response.status });
      return await response.json();
    } finally {
      clearTimeout(timer);
    }
  }

  async function fetchIndex() {
    for (let attempt = 0; attempt < 2; attempt++) {
      const rows = new Map();
      let cursor = 0;
      let revision = null;
      try {
        do {
          const url = API + '?view=index&cursor=' + cursor + (revision ? '&revision=' + revision : '');
          const page = await readJSON(url);
          if (page?.schema_version !== 1 || page.projection_version !== 'CILE-PUBLIC-INDEX-1') throw Error('invalid_index_projection');
          if (!/^[a-f0-9]{64}$/.test(page.index_revision || '') || !Number.isSafeInteger(page.total) || page.total < 0 || page.total > 10000) throw Error('invalid_index_header');
          if (!Array.isArray(page.records) || page.records.length > 50) throw Error('invalid_index_page');
          if (revision && revision !== page.index_revision) throw Object.assign(Error('index_changed'), { status: 409 });
          if (page.next_cursor !== null && (!Number.isSafeInteger(page.next_cursor) || page.next_cursor !== cursor + page.records.length || page.next_cursor <= cursor || page.next_cursor > page.total)) throw Error('invalid_index_cursor');
          if (page.next_cursor === null && cursor + page.records.length !== page.total) throw Error('incomplete_index_page');
          revision = page.index_revision;
          for (const raw of page.records) {
            const row = validateIndexRow(raw);
            if (rows.has(row.id)) throw Error('duplicate_index_identity');
            rows.set(row.id, row);
          }
          cursor = page.next_cursor;
        } while (cursor !== null);
        return rows;
      } catch (error) {
        if (error.status === 409 && attempt === 0) continue;
        throw error;
      }
    }
    throw Error('index_changed');
  }

  function aggregate(records, rows) {
    const categories = new Map(CLASS_ENTRIES.map(([key, label]) => [key, { key, label, primary: 0, secondary: 0, any: 0 }]));
    const states = new Map(Object.keys(STATE_LABELS).map((key) => [key, 0]));
    const combinations = new Map();
    const yearly = new Map();
    let classified = 0;
    let multi = 0;

    for (const record of records) {
      const row = rows.get(record.id);
      if (!row) {
        states.set('not_in_index', states.get('not_in_index') + 1);
        continue;
      }
      if (row.availability !== 'available') {
        states.set(row.availability, (states.get(row.availability) || 0) + 1);
        continue;
      }
      if (row.frameworkStatus === 'insufficient_evidence') {
        states.set('insufficient_evidence', states.get('insufficient_evidence') + 1);
        continue;
      }
      if (row.frameworkStatus === 'outside_framework') {
        states.set('outside_framework', states.get('outside_framework') + 1);
        continue;
      }

      classified++;
      states.set('classified', states.get('classified') + 1);
      const primary = row.primary;
      const secondary = [...row.secondary].sort((a, b) => CLASS_ENTRIES.findIndex(([key]) => key === a) - CLASS_ENTRIES.findIndex(([key]) => key === b));
      categories.get(primary).primary++;
      categories.get(primary).any++;
      for (const key of secondary) {
        categories.get(key).secondary++;
        categories.get(key).any++;
      }
      if (secondary.length) multi++;

      const combinationKey = `${primary}|${secondary.join(',')}`;
      if (!combinations.has(combinationKey)) combinations.set(combinationKey, { primary, secondary, count: 0 });
      combinations.get(combinationKey).count++;

      const year = yearOf(record);
      if (year !== null) {
        if (!yearly.has(year)) yearly.set(year, new Map(CLASS_ENTRIES.map(([key]) => [key, 0])));
        yearly.get(year).set(primary, yearly.get(year).get(primary) + 1);
      }
    }

    return {
      total: records.length,
      classified,
      multi,
      represented: [...categories.values()].filter((row) => row.primary > 0).length,
      categories: [...categories.values()],
      states: [...states.entries()].map(([state, count]) => ({ state, count })),
      combinations: [...combinations.values()].sort((a, b) => b.count - a.count || CLASS_LABELS[a.primary].localeCompare(CLASS_LABELS[b.primary], 'it')),
      years: [...yearly.keys()].sort((a, b) => a - b),
      yearly,
    };
  }

  function renderCategoryTable(data) {
    categoryTableHost.replaceChildren();
    const table = el('table');
    const head = el('thead');
    const header = el('tr');
    for (const label of ['Categoria', 'Primaria', 'Secondaria', 'Primaria o secondaria', 'Quota fra le primarie']) {
      const th = el('th', label);
      th.scope = 'col';
      header.append(th);
    }
    head.append(header);
    const body = el('tbody');
    for (const row of data.categories) {
      const tr = el('tr');
      const name = el('th', row.label);
      name.scope = 'row';
      tr.append(name, el('td', String(row.primary)), el('td', String(row.secondary)), el('td', String(row.any)), el('td', pct(row.primary, data.classified)));
      body.append(tr);
    }
    table.append(head, body);
    categoryTableHost.append(table);
  }

  function renderEvolution(data) {
    evolutionHost.replaceChildren();
    if (!data.years.length) {
      evolutionHost.append(el('p', 'Nessun anno di pubblicazione disponibile per i paper classificati nella vista corrente.'));
      return;
    }
    const table = el('table');
    table.className = 'bibliometric-matrix';
    const head = el('thead');
    const header = el('tr');
    header.append(el('th', 'Classe primaria'));
    for (const year of data.years) header.append(el('th', String(year)));
    head.append(header);
    const body = el('tbody');
    const maximum = Math.max(1, ...data.categories.flatMap((category) => data.years.map((year) => data.yearly.get(year).get(category.key))));
    for (const category of data.categories) {
      const tr = el('tr');
      const name = el('th', category.label);
      name.scope = 'row';
      tr.append(name);
      for (const year of data.years) {
        const value = data.yearly.get(year).get(category.key);
        const td = el('td', String(value));
        td.className = 'matrix-count';
        td.dataset.level = value === 0 ? '0' : String(Math.max(1, Math.ceil((value / maximum) * 4)));
        td.title = `${category.label} · ${year}: ${value}`;
        tr.append(td);
      }
      body.append(tr);
    }
    table.append(head, body);
    const scroll = el('div');
    scroll.className = 'table-scroll';
    scroll.append(table);
    evolutionHost.append(scroll);
  }

  function renderCombinations(data) {
    combinationHost.replaceChildren();
    if (!data.combinations.length) {
      combinationHost.append(el('p', 'Nessuna combinazione disponibile perché non ci sono paper classificati nella vista corrente.'));
      return;
    }
    const table = el('table');
    const head = el('thead');
    const header = el('tr');
    for (const label of ['Classe primaria', 'Classi secondarie', 'Paper', 'Quota dei classificati']) {
      const th = el('th', label);
      th.scope = 'col';
      header.append(th);
    }
    head.append(header);
    const body = el('tbody');
    for (const row of data.combinations) {
      const tr = el('tr');
      const primary = el('th', CLASS_LABELS[row.primary]);
      primary.scope = 'row';
      tr.append(primary, el('td', row.secondary.length ? row.secondary.map((key) => CLASS_LABELS[key]).join(', ') : 'Nessuna'), el('td', String(row.count)), el('td', pct(row.count, data.classified)));
      body.append(tr);
    }
    table.append(head, body);
    combinationHost.append(table);
  }

  function renderStates(data) {
    stateHost.replaceChildren();
    const table = el('table');
    const head = el('thead');
    const header = el('tr');
    for (const label of ['Stato', 'Record', 'Quota della vista']) {
      const th = el('th', label);
      th.scope = 'col';
      header.append(th);
    }
    head.append(header);
    const body = el('tbody');
    for (const row of data.states) {
      const tr = el('tr');
      const name = el('th', STATE_LABELS[row.state] || row.state);
      name.scope = 'row';
      tr.append(name, el('td', String(row.count)), el('td', pct(row.count, data.total)));
      body.append(tr);
    }
    table.append(head, body);
    const scroll = el('div');
    scroll.className = 'table-scroll';
    scroll.append(table);
    stateHost.append(
      el('p', '“Evidenza insufficiente” e “fuori framework” sono astensioni/valutazioni distinte e non vengono trattate come una settima o ottava categoria. Gli stati mancanti o non verificabili non valgono zero.'),
      scroll,
    );
  }

  function render() {
    refresh.disabled = running;
    errorBox.hidden = !loadError;
    empty.hidden = selected.length !== 0 || loadError;
    content.hidden = !loaded || running || loadError || selected.length === 0;
    if(running || loadError || !loaded || !selected.length){
      Object.values(metricNodes).forEach(node=>{node.textContent='—';});
      metrics.hidden=true;
    }

    if (running) {
      status.textContent = `Caricamento delle categorie per ${selected.length} record nella vista…`;
      return;
    }
    if (loadError) {
      status.textContent = 'Non è stato possibile caricare le categorie. Riprova.';
      return;
    }
    if (!loaded) {
      status.textContent = 'Categorie non ancora caricate…';
      return;
    }
    if (!selected.length) {
      status.textContent = 'La vista bibliometrica corrente non contiene record.';
      return;
    }

    const data = aggregate(selected, indexRows);
    const received=selected.filter(record=>{
      const row=indexRows.get(record.id);
      return row && !['stale','withheld'].includes(row.availability);
    }).length;
    if(!received){
      metrics.hidden=content.hidden=true;
      Object.values(metricNodes).forEach(node=>{node.textContent='—';});
      status.textContent='Le informazioni sulle categorie non sono disponibili per i paper di questa vista. Nessun totale può essere calcolato.';
      return;
    }
    metrics.hidden=false;
    metricNodes.classified.textContent = String(data.classified);
    metricNodes.coverage.textContent = pct(data.classified, received);
    metricNodes.multi.textContent = String(data.multi);
    metricNodes.represented.textContent = `${data.represented}/6`;
    status.textContent = `${data.classified} paper con categorie proposte nelle ${received} schede lette. `+
      (received===data.total?'Tutte le schede della vista sono state lette.':`Dati parziali: ${data.total-received} paper esclusi dalla distribuzione perché non consultabili.`)+
      ' Le categorie restano proposte, non validazioni scientifiche.';
    renderCategoryTable(data);
    renderEvolution(data);
    renderCombinations(data);
    renderStates(data);
  }

  async function load() {
    if (running) return;
    running = true;
    loadError = false;
    render();
    try {
      indexRows = await fetchIndex();
      loaded = true;
    } catch {
      loaded = false;
      loadError = true;
    } finally {
      running = false;
      render();
    }
  }

  function update(records) {
    const seen = new Set();
    selected = [];
    for (const record of records || []) {
      if (!record || typeof record.id !== 'string' || seen.has(record.id)) continue;
      seen.add(record.id);
      selected.push(record);
    }
    render();
  }

  refresh.addEventListener('click', () => { void load(); });
  globalThis.addEventListener('cile:bibliometric-view', () => update(globalThis.CILEBibliometricView));
  update(globalThis.CILEBibliometricView || []);
  void load();

  globalThis.CILECategorisationStatistics = { aggregate };
})();
