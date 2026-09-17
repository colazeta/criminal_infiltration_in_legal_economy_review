/* Public fallback for owner-authorised manual reading-support annotations.
   It fills the existing empty research-sheet sections and never attests CILE completion. */
(() => {
  'use strict';

  const REPOSITORY = 'colazeta/criminal_infiltration_in_legal_economy_review';
  const GITHUB_API = 'https://api.github.com';
  const ASSESSMENT_STATE = 'unreviewed_manual_support';
  const CLASS_LABELS = {
    aetiology: 'Eziologia', diagnosis: 'Diagnosi', screening: 'Screening',
    therapy: 'Terapia', prognosis: 'Prognosi', prevention: 'Prevenzione',
  };
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
  const MAIN_HEADING = /^(manual scientific enrichment|source-based scientific pre-extraction|scientific reading-support annotation|catalogue-grounded scientific pre-extraction)/i;
  const HIDDEN_HEADING = /^(analyst|remaining|outstanding|boundary|data-quality|specific quality|important interpretation|retrieval check|quality improvements)/i;
  const HIDDEN_LINE = /^(boundary\b|this is (?:a|an) (?:public |preparatory )?(?:reading-support|research)|no eligibility\b|no canonical\b|canonical metadata\b|existing canonical\b|formal completion\b|private source\b|no original full text\b)/i;
  const PRESET_TITLES = {
    overview: 'Domanda, contributo e definizione del fenomeno',
    framework: 'Collocazione nel framework delle sei classi',
    studies: 'Studi, campione, periodo e geografia',
    datasets: 'Dataset e fonti dei dati',
    methods: 'Disegno, metodi, identificazione e robustezza',
    variables: 'Variabili e operazionalizzazione',
    findings: 'Risultati, stime, incertezza e limiti',
    sources: 'Fonti consultate e informazioni sulla scheda',
  };
  const cache = new Map();

  const el = (tag, text) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; return n; };
  const escapeRegex = (value) => String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const candidateMarker = (id) => new RegExp(`<!--\\s*curator-candidate:${escapeRegex(id)}\\s*-->`, 'i');
  const annotationMarker = (id) => new RegExp(`<!--\\s*manual-scientific-enrichment:[^>]*:${escapeRegex(id)}\\s*-->`, 'i');

  function plain(value) {
    return String(value || '')
      .replace(/<!--.*?-->/g, '')
      .replace(/\[([^\]]+)\]\(https:\/\/[^)]+\)/g, '$1')
      .replace(/https:\/\/\S+/g, '')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/__([^_]+)__/g, '$1')
      .replace(/^\s*(?:[-*+] |\d+\.\s+)/, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function classKeys(body) {
    const result = [];
    for (const rawLine of String(body || '').split('\n')) {
      const line = plain(rawLine).toLowerCase();
      if (!/(framework|orientation|primary|secondary|classe principale|classe secondaria|classificazione)/.test(line)) continue;
      for (const key of Object.keys(CLASS_LABELS)) if (new RegExp(`\\b${key}\\b`, 'i').test(line) && !result.includes(key)) result.push(key);
    }
    return result;
  }

  function labelled(item, keys) {
    for (const key of keys) {
      const pattern = new RegExp(`^${escapeRegex(key)}(?:\\s+—[^:]+)?\\s*:\\s*(.+)$`, 'i');
      const match = String(item).match(pattern);
      if (match) return [key, match[1].trim()];
    }
    return null;
  }

  function deriveStructured(sections, classes) {
    const out = { overview: [], framework: [], studies: [], datasets: [], methods: [], variables: [], findings: [], sources: [] };
    const topKeys = ['summary','contribution','research_question','infiltration_definition','infiltration_operationalisation','authors_limitations'];
    const studyKeys = ['study_type','population','sampling','sampling/data coverage','sample size','sample_size','observation unit / analysis unit','observation_unit','analysis_unit','geography','period'];
    const methodKeys = ['design','method','comparison','identification','validation','robustness','findings'];
    const frameworkKeys = ['status','primary','rationale','secondary','secondary rationale','secondary_rationale','alternative'];

    for (const section of sections) {
      const title = section.title.toLowerCase();
      if (/primary sources|sources consulted|source and version|fonti consultate/.test(title)) {
        out.sources.push(...section.items);
        continue;
      }
      if (/top-level scientific fields|top level scientific fields/.test(title)) {
        for (const item of section.items) {
          const parsed = labelled(item, topKeys);
          if (!parsed || parsed[0] === 'analyst_limitations') continue;
          const key = parsed[0] === 'authors_limitations' ? 'authors_limitations' : parsed[0];
          (key === 'authors_limitations' ? out.findings : out.overview).push([key, parsed[1]]);
        }
        continue;
      }
      if (/clinical-contribution framework|framework/.test(title)) {
        for (const item of section.items) {
          const parsed = labelled(item, frameworkKeys);
          if (parsed) out.framework.push([parsed[0].replace('secondary rationale','secondary_rationale'), parsed[1]]);
        }
        continue;
      }
      if (/^study\b/.test(title)) {
        const rows = [];
        for (const item of section.items) {
          const parsed = labelled(item, studyKeys);
          if (parsed) {
            let key = parsed[0].replace('sampling/data coverage','sampling').replace('sample size','sample_size').replace('observation unit / analysis unit','observation_unit');
            rows.push([key, parsed[1]]);
          } else rows.push(['Dettaglio', item]);
        }
        out.studies.push({ title: section.title, rows });
        continue;
      }
      if (/dataset/.test(title)) { out.datasets.push(...section.items); continue; }
      if (/^analysis\b|method|design/.test(title)) {
        const rows = [];
        for (const item of section.items) {
          const parsed = labelled(item, methodKeys);
          if (parsed?.[0] === 'findings') out.findings.push([section.title, parsed[1]]);
          else rows.push(parsed || ['Dettaglio', item]);
        }
        out.methods.push({ title: section.title, rows });
        continue;
      }
      if (/variable/.test(title)) { out.variables.push(...section.items); continue; }
      if (/finding|result/.test(title)) { out.findings.push(...section.items.map(item => ['Risultato', item])); continue; }
      if (/source-derived|scientific fields|scientific extraction|extraction/.test(title)) {
        out.overview.push(...section.items.map(item => ['Sintesi scientifica', item]));
      }
    }

    if (!out.framework.length && classes.length) out.framework.push(['primary', CLASS_LABELS[classes[0]] || classes[0]]);
    if (classes.length > 1 && !out.framework.some(([k]) => k === 'secondary')) out.framework.push(['secondary', classes.slice(1).map(k => CLASS_LABELS[k] || k).join(', ')]);
    return out;
  }

  function parseComment(comment, candidateId) {
    const body = String(comment?.body || '');
    if (!annotationMarker(candidateId).test(body)) throw Error('manual_annotation_identity');
    const sections = [];
    let current = { title: 'Sintesi dell’annotazione', items: [], hidden: false };
    const flush = () => { if (!current.hidden && current.items.length) sections.push({ title: current.title, items: current.items.slice(0, 100) }); };
    for (const raw of body.split('\n')) {
      const heading = raw.match(/^#{2,5}\s+(.+?)\s*$/);
      if (heading) {
        const title = plain(heading[1]);
        if (MAIN_HEADING.test(title)) continue;
        flush(); current = { title: title || 'Dettagli', items: [], hidden: HIDDEN_HEADING.test(title) }; continue;
      }
      if (current.hidden || /^\s*\|/.test(raw)) continue;
      const text = plain(raw);
      if (!text || /^candidate\s*:/i.test(text) || HIDDEN_LINE.test(text)) continue;
      if (/(source_id|input_sha256|UTF-16|schema-valid proposal|private source IDs?)/i.test(text)) continue;
      current.items.push(text);
    }
    flush();
    const classes = classKeys(body);
    const url = typeof comment?.html_url === 'string' && /^https:\/\/github\.com\//.test(comment.html_url) ? comment.html_url : null;
    const updated = String(comment?.updated_at || comment?.created_at || '');
    return {
      schema_version: 1, assessment_state: ASSESSMENT_STATE, candidate_id: candidateId,
      issue_number: Number(comment?._issue_number) || null, comment_url: url,
      updated_at: /^\d{4}-\d{2}-\d{2}T/.test(updated) ? updated : null,
      classes, sections, structured: deriveStructured(sections, classes),
    };
  }

  async function readJSON(url) {
    const response = await fetch(url, { cache: 'no-store', credentials: 'omit', headers: { Accept: 'application/vnd.github+json' } });
    if (!response.ok) throw Object.assign(Error('manual_support_unavailable'), { status: response.status });
    return response.json();
  }
  async function findCandidateIssue(record) {
    const query = `repo:${REPOSITORY} is:issue in:body "${record.id}"`;
    const payload = await readJSON(`${GITHUB_API}/search/issues?q=${encodeURIComponent(query)}&per_page=10`);
    const exact = (payload.items || []).filter(issue => !issue.pull_request && candidateMarker(record.id).test(String(issue.body || '')));
    if (!exact.length) return null;
    if (exact.length !== 1) throw Error('manual_support_issue_ambiguous');
    return exact[0];
  }
  async function commentsForIssue(issue) {
    const pages = Math.max(1, Math.ceil(Number(issue.comments || 0) / 100));
    if (pages > 5) throw Error('manual_support_comment_limit');
    const comments = [];
    for (let page = 1; page <= pages; page++) {
      const payload = await readJSON(`${issue.comments_url}?per_page=100&page=${page}`);
      for (const comment of payload) comments.push({ ...comment, _issue_number: issue.number });
    }
    return comments;
  }
  async function fetchAnnotation(record) {
    if (cache.has(record.id)) return cache.get(record.id);
    const promise = (async () => {
      const issue = await findCandidateIssue(record); if (!issue) return null;
      const matching = (await commentsForIssue(issue)).filter(comment => annotationMarker(record.id).test(String(comment.body || '')));
      if (!matching.length) return null;
      matching.sort((a,b) => String(a.updated_at || a.created_at).localeCompare(String(b.updated_at || b.created_at)) || Number(a.id)-Number(b.id));
      return parseComment(matching.at(-1), record.id);
    })();
    cache.set(record.id, promise);
    try { return await promise; } catch (error) { cache.delete(record.id); throw error; }
  }

  function detailsMap(parent) {
    const map = new Map();
    if (!parent?.querySelectorAll) return map;
    for (const box of parent.querySelectorAll('details')) {
      const summary = box.querySelector('summary');
      if (summary) map.set(String(summary.textContent || '').trim(), box);
    }
    return map;
  }
  function clearBox(box) {
    const summary = box.querySelector('summary');
    for (const child of [...box.children]) if (child !== summary) child.remove();
    return box;
  }
  function rows(box, values) {
    if (!values?.length) return;
    const dl = el('dl');
    for (const [key, value] of values) dl.append(el('dt', FIELD_LABELS[key] || key), el('dd', value));
    box.append(dl);
  }
  function list(box, items) { for (const item of items || []) box.append(el('p', item)); }
  function groups(box, groups) {
    for (const group of groups || []) {
      box.append(el('h4', group.title)); rows(box, group.rows);
    }
  }

  function hydratePresetFields(parent, annotation) {
    const map = detailsMap(parent);
    const preset = Object.fromEntries(Object.entries(PRESET_TITLES).map(([k,title]) => [k, map.get(title)]));
    if (!preset.overview && !preset.framework && !preset.studies) return false;
    const s = annotation.structured;
    const note = el('p', 'Informazioni da un’annotazione di lettura non revisionata. Da sole non dimostrano né il completamento né la validazione dell’analisi.');
    note.className = 'paper-manual-research-status';
    parent.insertBefore(note, preset.overview || parent.firstChild);

    if (preset.overview && s.overview.length) { clearBox(preset.overview); rows(preset.overview, s.overview); preset.overview.open = true; }
    if (preset.framework && (s.framework.length || annotation.classes.length)) {
      clearBox(preset.framework); rows(preset.framework, s.framework);
      if (annotation.classes.length) preset.framework.append(el('small', 'Classi proposte nell’annotazione: ' + annotation.classes.map(k => CLASS_LABELS[k] || k).join(', ') + '.'));
      preset.framework.open = true;
    }
    if (preset.studies && s.studies.length) { clearBox(preset.studies); groups(preset.studies, s.studies); }
    if (preset.datasets && s.datasets.length) { clearBox(preset.datasets); list(preset.datasets, s.datasets); }
    if (preset.methods && s.methods.length) { clearBox(preset.methods); groups(preset.methods, s.methods); }
    if (preset.variables && s.variables.length) { clearBox(preset.variables); list(preset.variables, s.variables); }
    if (preset.findings && s.findings.length) { clearBox(preset.findings); rows(preset.findings, s.findings); }
    if (preset.sources) {
      clearBox(preset.sources);
      if (s.sources.length) list(preset.sources, s.sources);
      if (annotation.updated_at) preset.sources.append(el('p', 'Annotazione aggiornata: ' + annotation.updated_at.slice(0,10)));
      if (annotation.comment_url) { const a = el('a', 'Apri l’annotazione persistita su GitHub'); a.href = annotation.comment_url; a.target = '_blank'; a.rel = 'noreferrer noopener'; preset.sources.append(a); }
    }
    return true;
  }

  async function load(parent, record, isCurrent = () => true) {
    try {
      const annotation = await fetchAnnotation(record);
      if (annotation && isCurrent()) hydratePresetFields(parent, annotation);
    } catch {
      if (isCurrent()) {
        const note = el('p', 'Il supporto manuale non è verificabile in questo momento; questo non significa che sia assente.');
        note.className = 'paper-manual-research-status'; parent.append(note);
      }
    }
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

  globalThis.CILEManualResearch = Object.freeze({ assessmentState: ASSESSMENT_STATE, fetchAnnotation, parseComment, deriveStructured, hydratePresetFields, load, wrapResearchApi });
})();