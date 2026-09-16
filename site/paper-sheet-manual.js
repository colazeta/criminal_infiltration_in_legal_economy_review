/* Public overlay for owner-authorised manual reading-support annotations.
   This is separate from CILE-PUBLIC-RESEARCH-1 and never attests completion. */
(() => {
  'use strict';

  const REPOSITORY = 'colazeta/criminal_infiltration_in_legal_economy_review';
  const GITHUB_API = 'https://api.github.com';
  const ASSESSMENT_STATE = 'unreviewed_manual_support';
  const CLASS_LABELS = {
    aetiology: 'Eziologia',
    diagnosis: 'Diagnosi',
    screening: 'Screening',
    therapy: 'Terapia',
    prognosis: 'Prognosi',
    prevention: 'Prevenzione',
  };
  const MAIN_HEADING = /^(manual scientific enrichment|source-based scientific pre-extraction|scientific reading-support annotation|catalogue-grounded scientific pre-extraction)/i;
  const HIDDEN_HEADING = /^(analyst|remaining|outstanding|boundary|data-quality|specific quality|important interpretation|retrieval check|quality improvements)/i;
  const HIDDEN_LINE = /^(boundary\b|this is (?:a|an) (?:public |preparatory )?(?:reading-support|research)|no eligibility\b|no canonical\b|canonical metadata\b|existing canonical\b|formal completion\b|private source\b|no original full text\b)/i;
  const cache = new Map();

  const el = (tag, text) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const escapeRegex = (value) => String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

  function candidateMarker(candidateId) {
    return new RegExp(`<!--\\s*curator-candidate:${escapeRegex(candidateId)}\\s*-->`, 'i');
  }

  function annotationMarker(candidateId) {
    return new RegExp(`<!--\\s*manual-scientific-enrichment:[^>]*:${escapeRegex(candidateId)}\\s*-->`, 'i');
  }

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
      for (const key of Object.keys(CLASS_LABELS)) {
        if (new RegExp(`\\b${key}\\b`, 'i').test(line) && !result.includes(key)) result.push(key);
      }
    }
    return result;
  }

  function parseComment(comment, candidateId) {
    const body = String(comment?.body || '');
    if (!annotationMarker(candidateId).test(body)) throw Error('manual_annotation_identity');

    const sections = [];
    let current = { title: 'Sintesi dell’annotazione', items: [], hidden: false };
    const flush = () => {
      if (!current.hidden && current.items.length) sections.push({ title: current.title, items: current.items.slice(0, 80) });
    };

    for (const raw of body.split('\n')) {
      const heading = raw.match(/^#{2,5}\s+(.+?)\s*$/);
      if (heading) {
        const title = plain(heading[1]);
        if (MAIN_HEADING.test(title)) continue;
        flush();
        current = { title: title || 'Dettagli', items: [], hidden: HIDDEN_HEADING.test(title) };
        continue;
      }
      if (current.hidden || /^\s*\|/.test(raw)) continue;
      const text = plain(raw);
      if (!text || /^candidate\s*:/i.test(text) || HIDDEN_LINE.test(text)) continue;
      if (/(source_id|input_sha256|UTF-16|schema-valid proposal|private source IDs?)/i.test(text)) continue;
      current.items.push(text);
    }
    flush();

    const url = typeof comment?.html_url === 'string' && /^https:\/\/github\.com\//.test(comment.html_url) ? comment.html_url : null;
    const updated = String(comment?.updated_at || comment?.created_at || '');
    return {
      schema_version: 1,
      assessment_state: ASSESSMENT_STATE,
      candidate_id: candidateId,
      issue_number: Number(comment?._issue_number) || null,
      comment_url: url,
      updated_at: /^\d{4}-\d{2}-\d{2}T/.test(updated) ? updated : null,
      classes: classKeys(body),
      sections,
    };
  }

  async function readJSON(url) {
    const response = await fetch(url, {
      cache: 'no-store',
      credentials: 'omit',
      headers: { Accept: 'application/vnd.github+json' },
    });
    if (!response.ok) throw Object.assign(Error('manual_support_unavailable'), { status: response.status });
    return response.json();
  }

  async function findCandidateIssue(record) {
    const query = `repo:${REPOSITORY} is:issue in:body \"${record.id}\"`;
    const payload = await readJSON(`${GITHUB_API}/search/issues?q=${encodeURIComponent(query)}&per_page=10`);
    const exact = (payload.items || []).filter((issue) =>
      !issue.pull_request && candidateMarker(record.id).test(String(issue.body || '')),
    );
    if (exact.length === 0) return null;
    if (exact.length !== 1) throw Error('manual_support_issue_ambiguous');
    return exact[0];
  }

  async function commentsForIssue(issue) {
    const count = Number(issue.comments || 0);
    const pages = Math.max(1, Math.ceil(count / 100));
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
      const issue = await findCandidateIssue(record);
      if (!issue) return null;
      const matching = (await commentsForIssue(issue)).filter((comment) => annotationMarker(record.id).test(String(comment.body || '')));
      if (!matching.length) return null;
      matching.sort((a, b) => String(a.updated_at || a.created_at).localeCompare(String(b.updated_at || b.created_at)) || Number(a.id) - Number(b.id));
      return parseComment(matching.at(-1), record.id);
    })();
    cache.set(record.id, promise);
    try {
      return await promise;
    } catch (error) {
      cache.delete(record.id);
      throw error;
    }
  }

  function render(parent, annotation) {
    if (!annotation) return;
    const box = el('section');
    box.className = 'paper-manual-research';
    box.setAttribute('aria-label', 'Supporto di lettura manuale non revisionato');
    box.append(el('h3', 'Supporto di lettura manuale'));
    box.append(el('p', 'Annotazione scientifica pubblica e non revisionata, separata dall’estrazione formale CILE-ENRICH-1. Non attesta inclusione, correttezza scientifica o completamento.'));

    if (annotation.classes.length) {
      box.append(el('p', 'Classi Cincimino proposte nell’annotazione: ' + annotation.classes.map((key) => CLASS_LABELS[key]).join(', ') + '.'));
    }
    if (annotation.updated_at) box.append(el('small', 'Ultimo aggiornamento dell’annotazione: ' + annotation.updated_at.slice(0, 10)));

    annotation.sections.forEach((section, index) => {
      const details = el('details');
      details.open = index < 2;
      details.append(el('summary', section.title));
      for (const item of section.items) details.append(el('p', item));
      box.append(details);
    });

    if (annotation.comment_url) {
      const link = el('a', 'Apri l’annotazione persistita su GitHub');
      link.href = annotation.comment_url;
      link.target = '_blank';
      link.rel = 'noreferrer noopener';
      box.append(link);
    }
    parent.append(box);
  }

  async function load(parent, record, isCurrent = () => true) {
    try {
      const annotation = await fetchAnnotation(record);
      if (annotation && isCurrent()) render(parent, annotation);
    } catch {
      if (!isCurrent()) return;
      const note = el('p', 'Il supporto di lettura manuale non è verificabile in questo momento; questo non significa che sia assente.');
      note.className = 'paper-manual-research-status';
      parent.append(note);
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
  if (existing) {
    globalThis.CILEPaperResearch = wrapResearchApi(existing);
  } else {
    let pending;
    Object.defineProperty(globalThis, 'CILEPaperResearch', {
      configurable: true,
      enumerable: true,
      get() { return pending; },
      set(value) {
        pending = wrapResearchApi(value);
        Object.defineProperty(globalThis, 'CILEPaperResearch', {
          configurable: true,
          enumerable: true,
          writable: true,
          value: pending,
        });
      },
    });
  }

  globalThis.CILEManualResearch = Object.freeze({
    assessmentState: ASSESSMENT_STATE,
    fetchAnnotation,
    parseComment,
    render,
    load,
    wrapResearchApi,
  });
})();
