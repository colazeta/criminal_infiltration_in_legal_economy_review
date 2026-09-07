"use strict";

(() => {
  const SESSION_KEY = "criminal-infiltration-curator-session";
  const config = window.CURATOR_APP_CONFIG || {};
  const apiBaseUrl = String(config.apiBaseUrl || "").replace(/\/$/, "");
  const abstractCache = new Map();
  const contextCache = new Map();
  let activeCandidateId = "";
  let activeController = null;

  const byId = (id) => document.getElementById(id);

  function clean(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function safeHttpsUrl(value) {
    try {
      const url = new URL(String(value || ""));
      return url.protocol === "https:" ? url.toString() : "";
    } catch {
      return "";
    }
  }

  function sessionToken() {
    try {
      return sessionStorage.getItem(SESSION_KEY) || "";
    } catch {
      return "";
    }
  }

  function selectedIssueNumber() {
    const href = byId("selected-candidate-issue")?.href || "";
    const match = href.match(/\/issues\/(\d+)(?:[/?#]|$)/);
    return match ? Number(match[1]) : null;
  }

  function createPanel(id, titleId, eyebrowText, titleText) {
    const panel = document.createElement("section");
    panel.id = id;
    panel.className = "candidate-abstract-panel";
    panel.setAttribute("aria-labelledby", titleId);

    const header = document.createElement("div");
    header.className = "candidate-abstract-heading";
    const titleGroup = document.createElement("div");
    const eyebrow = document.createElement("p");
    eyebrow.className = "workspace-label";
    eyebrow.textContent = eyebrowText;
    const title = document.createElement("h4");
    title.id = titleId;
    title.textContent = titleText;
    titleGroup.append(eyebrow, title);
    const source = document.createElement("span");
    source.className = "candidate-abstract-source";
    header.append(titleGroup, source);
    const body = document.createElement("p");
    body.className = "candidate-abstract-text";
    const note = document.createElement("p");
    note.className = "candidate-abstract-note";
    panel.append(header, body, note);
    return { panel, source, body, note };
  }

  function ensureReadingSurface() {
    const detail = byId("candidate-detail");
    if (!detail) return null;
    detail.classList.add("reading-candidate-detail");

    let headingActions = detail.querySelector(".candidate-heading-actions");
    if (!headingActions) {
      headingActions = document.createElement("div");
      headingActions.className = "candidate-heading-actions";
      const heading = detail.querySelector(".candidate-detail-heading");
      const audit = byId("selected-candidate-issue");
      if (heading && audit) {
        headingActions.append(audit);
        heading.append(headingActions);
      }
    }

    let articleLink = byId("selected-candidate-article");
    if (!articleLink) {
      articleLink = document.createElement("a");
      articleLink.id = "selected-candidate-article";
      articleLink.className = "candidate-article-action";
      articleLink.target = "_blank";
      articleLink.rel = "noopener noreferrer";
      articleLink.textContent = "Apri articolo ↗";
      articleLink.hidden = true;
      headingActions?.prepend(articleLink);
    }

    let byline = byId("selected-candidate-byline");
    if (!byline) {
      byline = document.createElement("p");
      byline.id = "selected-candidate-byline";
      byline.className = "candidate-reading-byline";
      byId("selected-candidate-title")?.insertAdjacentElement("afterend", byline);
    }

    let abstractPanel = byId("candidate-abstract-panel");
    if (!abstractPanel) {
      const created = createPanel("candidate-abstract-panel", "candidate-abstract-title", "Lettura", "Abstract / sintesi");
      abstractPanel = created.panel;
      created.source.id = "candidate-abstract-source";
      created.source.textContent = "—";
      created.body.id = "candidate-abstract-text";
      created.body.textContent = "Seleziona un record.";
      created.note.id = "candidate-abstract-note";
      detail.querySelector(".candidate-metadata")?.insertAdjacentElement("afterend", abstractPanel);
    }

    let aidPanel = byId("candidate-reading-aid-panel");
    if (!aidPanel) {
      const created = createPanel("candidate-reading-aid-panel", "candidate-reading-aid-title", "Supporto", "Lettura assistita");
      aidPanel = created.panel;
      created.source.id = "candidate-reading-aid-kind";
      created.body.id = "candidate-reading-aid-text";
      created.note.id = "candidate-reading-aid-note";
      aidPanel.hidden = true;
      abstractPanel.insertAdjacentElement("afterend", aidPanel);
    }

    let guidancePanel = byId("candidate-review-guidance-panel");
    if (!guidancePanel) {
      const created = createPanel("candidate-review-guidance-panel", "candidate-review-guidance-title", "Review", "Guida preparatoria");
      guidancePanel = created.panel;
      created.source.id = "candidate-review-gate";
      created.body.id = "candidate-review-guidance-text";
      created.note.id = "candidate-review-guidance-note";
      guidancePanel.hidden = true;
      aidPanel.insertAdjacentElement("afterend", guidancePanel);
    }

    return { articleLink, abstractPanel, aidPanel, guidancePanel };
  }

  function setArticleUrl(value) {
    const link = byId("selected-candidate-article");
    if (!link) return;
    const safe = safeHttpsUrl(value);
    link.hidden = !safe;
    if (safe) link.href = safe;
    else link.removeAttribute("href");
  }

  function renderByline() {
    const authors = clean(byId("selected-candidate-authors")?.textContent);
    const year = clean(byId("selected-candidate-year")?.textContent);
    const venue = clean(byId("selected-candidate-venue")?.textContent);
    const parts = [authors, year, venue].filter((value) => value && !/^Non registrat/i.test(value));
    const byline = byId("selected-candidate-byline");
    if (byline) byline.textContent = parts.join(" · ");
  }

  function aidKindLabel(kind) {
    const labels = {
      verified_abstract_source: "Abstract/source verificata",
      publisher_summary: "Summary dell’editore",
      full_text_intro: "Sintesi da full text / introduzione",
      review_synopsis: "Sintesi da fonti verificate",
      metadata_warning: "Sintesi dai metadati verificati",
    };
    return labels[kind] || "Sintesi preparatoria";
  }

  function renderReviewSupport(context) {
    const support = context?.reviewSupport || {};
    const aid = support.aid;
    const guidance = support.guidance;
    const aidPanel = byId("candidate-reading-aid-panel");
    const guidancePanel = byId("candidate-review-guidance-panel");
    if (aidPanel) aidPanel.hidden = !aid;
    if (guidancePanel) guidancePanel.hidden = !guidance;
    if (aid) {
      const kind = byId("candidate-reading-aid-kind");
      const text = byId("candidate-reading-aid-text");
      const note = byId("candidate-reading-aid-note");
      if (kind) kind.textContent = aidKindLabel(aid["Aid kind"]);
      if (text) text.textContent = aid["Review synopsis"] || "";
      if (note) note.textContent = [aid.Source, aid["Last checked"], aid.Note].filter(Boolean).join(" · ");
    }
    if (guidance) {
      const gate = byId("candidate-review-gate");
      const text = byId("candidate-review-guidance-text");
      const note = byId("candidate-review-guidance-note");
      if (gate) gate.textContent = guidance["Current gate"] || "Gate da verificare";
      if (text) text.textContent = [guidance["Candidate-specific focus"], guidance.approach].filter(Boolean).join(" ");
      if (note) note.textContent = [guidance["Suggested screening stage"], guidance["Prior triage signal"]].filter(Boolean).join(" · ");
    }
  }

  function metadataFallback() {
    const title = clean(byId("selected-candidate-title")?.textContent);
    const authors = clean(byId("selected-candidate-authors")?.textContent);
    const year = clean(byId("selected-candidate-year")?.textContent);
    const venue = clean(byId("selected-candidate-venue")?.textContent);
    const bibliographic = [authors && !/^Non registrat/i.test(authors) ? authors : "autore non verificato", year && !/^Non registrat/i.test(year) ? `(${year})` : "", title, venue && !/^Non registrat/i.test(venue) ? `in ${venue}` : ""].filter(Boolean).join(" ");
    return `${bibliographic}. Il record materializzato non espone ancora un abstract o una sintesi sostanziale verificata. Dal solo record bibliografico non è possibile stabilire la relazione con l’infiltrazione criminale nell’economia legale; la decisione richiede quindi evidenza ulteriore.`;
  }

  function promoteSynthesis(context) {
    ensureReadingSurface();
    const panel = byId("candidate-abstract-panel");
    const title = byId("candidate-abstract-title");
    const source = byId("candidate-abstract-source");
    const text = byId("candidate-abstract-text");
    const note = byId("candidate-abstract-note");
    if (!panel || !title || !source || !text || !note) return false;
    if (panel.dataset.evidenceMode === "abstract") return true;

    const aid = context?.reviewSupport?.aid;
    const synopsis = clean(aid?.["Review synopsis"]);
    const kind = clean(aid?.["Aid kind"]);
    if (synopsis) {
      panel.dataset.evidenceMode = "synthesis";
      panel.dataset.synthesisKind = kind || "review_synopsis";
      title.textContent = "Sintesi per lo screening";
      source.textContent = `${aidKindLabel(kind)}${aid?.Source ? ` · ${aid.Source}` : ""}`;
      text.textContent = synopsis;
      note.textContent = aid?.Note
        ? `Sintesi sostitutiva, non abstract dell’autore. ${aid.Note}`
        : "Sintesi sostitutiva basata su evidenza materializzata; non è l’abstract dell’autore.";
      return true;
    }

    panel.dataset.evidenceMode = "metadata";
    title.textContent = "Sintesi minima per lo screening";
    source.textContent = "Metadati materializzati";
    text.textContent = metadataFallback();
    note.textContent = "Fallback descrittivo limitato ai metadati: non inferisce contenuti non verificati.";
    return false;
  }

  function providerTrace(payload) {
    const providers = Array.isArray(payload?.providersTried) ? payload.providersTried.filter(Boolean) : [];
    return providers.length ? providers.join(" · ") : "";
  }

  function matchLabel(payload) {
    if (payload?.matchType === "doi") return "DOI verificato";
    if (payload?.matchType === "title_year") return "Titolo + anno verificati";
    if (payload?.matchType === "free_page_reader") return "Pagina DOI letta";
    if (payload?.matchType === "resolved_url") return "Locator verificato";
    if (payload?.matchType === "resolved_url_none") return "Paper risolto, abstract non esposto";
    if (payload?.matchType === "needs_web_search") return "Abstract non risolto";
    if (payload?.matchType === "unavailable") return "Verifica tecnica incompleta";
    return "Verifica abstract";
  }

  function renderAbstract(payload) {
    const panel = byId("candidate-abstract-panel");
    const title = byId("candidate-abstract-title");
    const text = byId("candidate-abstract-text");
    const source = byId("candidate-abstract-source");
    const note = byId("candidate-abstract-note");
    const abstract = clean(payload?.abstract);
    if (!panel || !title || !text || !source || !note || !abstract) return false;
    panel.dataset.evidenceMode = "abstract";
    title.textContent = "Abstract";
    text.textContent = abstract;
    source.textContent = `${payload.abstractSource || payload.provider || "Fonte verificata"} · ${matchLabel(payload)}`;
    const trace = providerTrace(payload);
    note.textContent = trace
      ? `Fonti interrogate: ${trace}. Abstract mostrato nella sessione autenticata e non persistito nel corpus pubblico.`
      : "Abstract mostrato nella sessione autenticata e non persistito nel corpus pubblico.";
    if (payload?.articleUrl) setArticleUrl(payload.articleUrl);
    return true;
  }

  function annotateAbstractFailure(payload) {
    const panel = byId("candidate-abstract-panel");
    const note = byId("candidate-abstract-note");
    if (!panel || !note || panel.dataset.evidenceMode === "abstract") return;
    const trace = providerTrace(payload);
    const status = matchLabel(payload || {});
    const suffix = trace ? ` Fonti tentate: ${trace}.` : "";
    note.textContent = `${note.textContent} Abstract originale: ${status.toLowerCase()}.${suffix}`.trim();
  }

  function renderLoadingIfNeeded() {
    const panel = byId("candidate-abstract-panel");
    const title = byId("candidate-abstract-title");
    const text = byId("candidate-abstract-text");
    const source = byId("candidate-abstract-source");
    const note = byId("candidate-abstract-note");
    if (!panel || panel.dataset.evidenceMode === "synthesis" || panel.dataset.evidenceMode === "metadata") return;
    panel.dataset.evidenceMode = "loading";
    if (title) title.textContent = "Abstract / sintesi";
    if (text) text.textContent = "Recupero dell’evidenza in corso…";
    if (source) source.textContent = "Locator e fonti scholarly";
    if (note) note.textContent = "La console applica un limite temporale: il recupero esterno non può lasciare la scheda bloccata indefinitamente.";
  }

  function timedSignal(parentSignal, timeoutMs) {
    const controller = new AbortController();
    let timedOut = false;
    const abortFromParent = () => controller.abort(parentSignal?.reason || "candidate_changed");
    if (parentSignal?.aborted) abortFromParent();
    else parentSignal?.addEventListener("abort", abortFromParent, { once: true });
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort("timeout");
    }, timeoutMs);
    return {
      signal: controller.signal,
      timedOut: () => timedOut,
      clear() {
        clearTimeout(timer);
        parentSignal?.removeEventListener("abort", abortFromParent);
      },
    };
  }

  async function authenticatedJson(target, token, parentSignal, timeoutMs) {
    const timed = timedSignal(parentSignal, timeoutMs);
    try {
      const response = await fetch(target, {
        headers: { Authorization: `Bearer ${token}` },
        signal: timed.signal,
      });
      if (!response.ok) return null;
      return response.json();
    } catch (error) {
      if (parentSignal?.aborted) throw error;
      return null;
    } finally {
      timed.clear();
    }
  }

  async function fetchContext(candidateId, issueNumber, token, signal) {
    if (!issueNumber) return null;
    const key = `${candidateId}|${issueNumber}`;
    if (contextCache.has(key)) return contextCache.get(key);
    const target = new URL(`${apiBaseUrl}/api/retrieval`);
    target.searchParams.set("candidate", candidateId);
    target.searchParams.set("issue", String(issueNumber));
    const context = await authenticatedJson(target, token, signal, 6500);
    if (context) contextCache.set(key, context);
    return context;
  }

  async function fetchLocatorAbstract(candidateId, issueNumber, title, doi, year, token, signal) {
    if (!issueNumber) return null;
    const target = new URL(`${apiBaseUrl}/api/free-web-search`);
    target.searchParams.set("candidate", candidateId);
    target.searchParams.set("issue", String(issueNumber));
    target.searchParams.set("title", title);
    target.searchParams.set("mode", "locator_only");
    if (doi && doi !== "Non registrato") target.searchParams.set("doi", doi);
    if (year && year !== "Non registrato") target.searchParams.set("year", year);
    return authenticatedJson(target, token, signal, 7500);
  }

  async function fetchEnrichment(title, doi, year, token, signal) {
    const target = new URL(`${apiBaseUrl}/api/enrichment`);
    target.searchParams.set("title", title);
    if (doi && doi !== "Non registrato") target.searchParams.set("doi", doi);
    if (year && year !== "Non registrato") target.searchParams.set("year", year);
    return authenticatedJson(target, token, signal, 9000);
  }

  async function fetchResolvedAbstract(candidateId, issueNumber, title, token, signal) {
    if (!issueNumber) return null;
    const target = new URL(`${apiBaseUrl}/api/resolved-abstract`);
    target.searchParams.set("candidate", candidateId);
    target.searchParams.set("issue", String(issueNumber));
    target.searchParams.set("title", title);
    return authenticatedJson(target, token, signal, 7000);
  }

  async function fetchBroadWebFallback(candidateId, issueNumber, title, doi, year, token, signal) {
    if (!issueNumber) return null;
    const target = new URL(`${apiBaseUrl}/api/free-web-search`);
    target.searchParams.set("candidate", candidateId);
    target.searchParams.set("issue", String(issueNumber));
    target.searchParams.set("title", title);
    if (doi && doi !== "Non registrato") target.searchParams.set("doi", doi);
    if (year && year !== "Non registrato") target.searchParams.set("year", year);
    return authenticatedJson(target, token, signal, 10000);
  }

  function needsIdentityEnrichment() {
    const stage = clean(byId("selected-candidate-stage")?.textContent).toLowerCase();
    const blocked = byId("candidate-detail")?.dataset.identityBlocked === "true";
    return blocked || stage.includes("metadat");
  }

  async function refreshReadingSurface() {
    const detail = byId("candidate-detail");
    if (!detail || detail.hidden || !apiBaseUrl) return;
    ensureReadingSurface();

    const candidateId = clean(byId("selected-candidate-id")?.textContent);
    const title = clean(byId("selected-candidate-title")?.textContent);
    const doi = clean(byId("selected-candidate-doi")?.textContent);
    const year = clean(byId("selected-candidate-year")?.textContent);
    const issueNumber = selectedIssueNumber();
    const token = sessionToken();
    if (!candidateId || !title || candidateId === "—" || title === "—" || !token) return;

    const candidateChanged = candidateId !== activeCandidateId;
    if (!candidateChanged && byId("candidate-abstract-text")?.dataset.loaded === "true") return;
    if (candidateChanged) {
      activeCandidateId = candidateId;
      activeController?.abort("candidate_changed");
      activeController = new AbortController();
      const panel = byId("candidate-abstract-panel");
      if (panel) {
        delete panel.dataset.evidenceMode;
        delete panel.dataset.synthesisKind;
      }
      const text = byId("candidate-abstract-text");
      if (text) delete text.dataset.loaded;
    }
    const signal = activeController?.signal;
    if (!signal) return;

    renderByline();
    const cacheKey = [candidateId, issueNumber || "", title, doi, year].join("|");
    const cachedAbstract = abstractCache.get(cacheKey);
    if (cachedAbstract?.abstract) {
      renderAbstract(cachedAbstract);
      const text = byId("candidate-abstract-text");
      if (text) text.dataset.loaded = "true";
      return;
    }

    const context = await fetchContext(candidateId, issueNumber, token, signal).catch(() => null);
    if (signal.aborted || activeCandidateId !== candidateId) return;
    if (context) {
      renderReviewSupport(context);
      promoteSynthesis(context);
      setArticleUrl(context.bestUrl || context.openAccessUrl || context.fullTextUrl || context.abstractArticleUrl);
      document.dispatchEvent(new CustomEvent("curator:candidate-context", { detail: { candidateId, context } }));
    } else {
      promoteSynthesis(null);
    }

    if (context?.abstractCoverageStatus === "available" && context?.abstractArticleUrl) {
      const located = await fetchLocatorAbstract(candidateId, issueNumber, title, doi, year, token, signal).catch(() => null);
      if (signal.aborted || activeCandidateId !== candidateId) return;
      if (renderAbstract(located)) {
        abstractCache.set(cacheKey, located);
        const text = byId("candidate-abstract-text");
        if (text) text.dataset.loaded = "true";
        if (needsIdentityEnrichment()) void fetchEnrichment(title, doi, year, token, signal);
        return;
      }
      annotateAbstractFailure(located || { matchType: "needs_web_search" });
    }

    renderLoadingIfNeeded();
    const enriched = await fetchEnrichment(title, doi, year, token, signal).catch(() => null);
    if (signal.aborted || activeCandidateId !== candidateId) return;
    if (renderAbstract(enriched)) {
      abstractCache.set(cacheKey, enriched);
      const text = byId("candidate-abstract-text");
      if (text) text.dataset.loaded = "true";
      return;
    }
    annotateAbstractFailure(enriched || { matchType: "unavailable" });

    const resolved = await fetchResolvedAbstract(candidateId, issueNumber, title, token, signal).catch(() => null);
    if (signal.aborted || activeCandidateId !== candidateId) return;
    if (renderAbstract(resolved)) {
      abstractCache.set(cacheKey, resolved);
      const text = byId("candidate-abstract-text");
      if (text) text.dataset.loaded = "true";
      return;
    }
    annotateAbstractFailure(resolved || { matchType: "unavailable" });

    const hasSubstantiveSynthesis = byId("candidate-abstract-panel")?.dataset.evidenceMode === "synthesis";
    if (!hasSubstantiveSynthesis) {
      const broad = await fetchBroadWebFallback(candidateId, issueNumber, title, doi, year, token, signal).catch(() => null);
      if (signal.aborted || activeCandidateId !== candidateId) return;
      if (renderAbstract(broad)) {
        abstractCache.set(cacheKey, broad);
        const text = byId("candidate-abstract-text");
        if (text) text.dataset.loaded = "true";
        return;
      }
      annotateAbstractFailure(broad || { matchType: "unavailable" });
    }

    const text = byId("candidate-abstract-text");
    if (text) text.dataset.loaded = "true";
  }

  function observeCandidateChanges() {
    const detail = byId("candidate-detail");
    const id = byId("selected-candidate-id");
    if (!detail || !id) return;
    let queued = false;
    const queueRefresh = () => {
      if (queued) return;
      queued = true;
      queueMicrotask(() => {
        queued = false;
        refreshReadingSurface();
      });
    };
    const observer = new MutationObserver(queueRefresh);
    observer.observe(detail, { attributes: true, attributeFilter: ["hidden"] });
    observer.observe(id, { childList: true, characterData: true, subtree: true });
    observer.observe(byId("candidate-provenance") || detail, { childList: true, subtree: true });
    observer.observe(byId("selected-candidate-issue") || detail, { attributes: true, attributeFilter: ["href"] });
    queueRefresh();
  }

  function loadReadingStyles() {
    if (document.querySelector('link[data-curator-reading="true"]')) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "./curator-reading.css";
    link.dataset.curatorReading = "true";
    document.head.append(link);
  }

  function initialise() {
    loadReadingStyles();
    ensureReadingSurface();
    observeCandidateChanges();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialise, { once: true });
  else initialise();
})();
