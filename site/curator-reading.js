"use strict";

(() => {
  const SESSION_KEY = "criminal-infiltration-curator-session";
  const config = window.CURATOR_APP_CONFIG || {};
  const apiBaseUrl = String(config.apiBaseUrl || "").replace(/\/$/, "");
  const cache = new Map();
  const supportCache = new Map();
  let activeCandidateId = "";
  let activeController = null;
  let supportController = null;

  const byId = (id) => document.getElementById(id);

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

  function selectedIssueInfo() {
    const href = byId("selected-candidate-issue")?.href || "";
    try {
      const url = new URL(href);
      if (url.hostname !== "github.com") return null;
      const match = url.pathname.match(/^\/([^/]+)\/([^/]+)\/issues\/(\d+)(?:\/|$)/);
      if (!match) return null;
      return {
        owner: match[1],
        repo: match[2],
        number: Number(match[3]),
        href: url.toString(),
      };
    } catch {
      return null;
    }
  }

  function selectedIssueNumber() {
    return selectedIssueInfo()?.number || null;
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
      const created = createPanel(
        "candidate-abstract-panel",
        "candidate-abstract-title",
        "Lettura rapida",
        "Abstract",
      );
      abstractPanel = created.panel;
      created.source.id = "candidate-abstract-source";
      created.source.textContent = "Da recuperare";
      created.body.id = "candidate-abstract-text";
      created.body.textContent = "Seleziona una scheda per recuperare l’abstract.";
      created.note.id = "candidate-abstract-note";
      created.note.textContent =
        "L’abstract è un ausilio alla revisione e non viene scritto nell’archivio pubblico.";
      detail.querySelector(".candidate-metadata")?.insertAdjacentElement("afterend", abstractPanel);
    }

    let aidPanel = byId("candidate-reading-aid-panel");
    if (!aidPanel) {
      const created = createPanel(
        "candidate-reading-aid-panel",
        "candidate-reading-aid-title",
        "Supporto preparatorio",
        "Lettura assistita",
      );
      aidPanel = created.panel;
      created.source.id = "candidate-reading-aid-kind";
      created.body.id = "candidate-reading-aid-text";
      created.note.id = "candidate-reading-aid-note";
      aidPanel.hidden = true;
      abstractPanel.insertAdjacentElement("afterend", aidPanel);
    }

    let guidancePanel = byId("candidate-review-guidance-panel");
    if (!guidancePanel) {
      const created = createPanel(
        "candidate-review-guidance-panel",
        "candidate-review-guidance-title",
        "Prima di decidere",
        "Come trattare questa scheda",
      );
      guidancePanel = created.panel;
      created.source.id = "candidate-review-gate";
      created.body.id = "candidate-review-guidance-text";
      created.note.id = "candidate-review-guidance-note";
      guidancePanel.hidden = true;
      aidPanel.insertAdjacentElement("afterend", guidancePanel);
    }

    return { articleLink, byline, abstractPanel, aidPanel, guidancePanel };
  }

  function provenanceArticleUrl() {
    const doiLink = byId("selected-candidate-doi-link");
    if (doiLink && !doiLink.hidden) {
      const safe = safeHttpsUrl(doiLink.href);
      if (safe) return safe;
    }
    const provenance = byId("candidate-provenance");
    if (!provenance) return "";
    for (const row of provenance.querySelectorAll("div")) {
      const label = row.querySelector("dt")?.textContent?.trim().toLowerCase() || "";
      const value = row.querySelector("dd")?.textContent?.trim() || "";
      if (!label.startsWith("source link")) continue;
      const safe = safeHttpsUrl(value);
      if (safe) return safe;
    }
    return "";
  }

  function renderByline() {
    const authors = byId("selected-candidate-authors")?.textContent?.trim() || "";
    const year = byId("selected-candidate-year")?.textContent?.trim() || "";
    const venue = byId("selected-candidate-venue")?.textContent?.trim() || "";
    const parts = [authors, year, venue].filter((value) => value && !/^Non registrat/.test(value));
    const byline = byId("selected-candidate-byline");
    if (byline) byline.textContent = parts.join(" · ");
  }

  function setArticleUrl(value) {
    const link = byId("selected-candidate-article");
    if (!link) return;
    const safe = safeHttpsUrl(value);
    link.hidden = !safe;
    if (safe) link.href = safe;
    else link.removeAttribute("href");
  }

  function providerTrace(payload) {
    const providers = Array.isArray(payload?.providersTried) ? payload.providersTried.filter(Boolean) : [];
    return providers.length ? providers.join(" · ") : "";
  }

  function matchLabel(payload) {
    if (payload.matchType === "doi") return "DOI verificato";
    if (payload.matchType === "title_year") return "Titolo + anno verificati";
    if (payload.matchType === "free_page_reader") return "Pagina DOI letta con Jina Reader";
    if (payload.matchType === "free_web_search") return "Ricerca web gratuita verificata";
    if (payload.matchType === "resolved_url") return "Paper risolto verificato";
    if (payload.matchType === "resolved_url_none") return "Paper risolto, abstract non esposto";
    if (payload.matchType === "needs_resolved_document") return "Fonti scholarly completate";
    if (payload.matchType === "needs_web_search") return "Ricerca web gratuita/assistita necessaria";
    if (payload.matchType === "web_search_exhausted") return "Ricerca web gratuita completata senza abstract";
    if (payload.matchType === "unavailable") return "Servizio non disponibile";
    return "Nessun match affidabile";
  }

  function renderAbstract(payload) {
    const text = byId("candidate-abstract-text");
    const source = byId("candidate-abstract-source");
    const note = byId("candidate-abstract-note");
    if (!text || !source || !note) return;

    const abstract = String(payload?.abstract || "").trim();
    const trace = providerTrace(payload);
    if (abstract) {
      text.textContent = abstract;
      source.textContent = `${payload.abstractSource || payload.provider || "Fonte verificata"} · ${matchLabel(payload)}`;
      note.textContent = trace
        ? `Fonti interrogate: ${trace}. Abstract mostrato solo nella console autenticata e non persistito nel corpus pubblico.`
        : "Abstract recuperato al momento della consultazione e mostrato solo nella console autenticata; non viene persistito nel corpus pubblico.";
    } else if (payload?.matchType === "needs_web_search") {
      text.textContent =
        "La cascata automatica gratuita non ha ancora esposto un abstract affidabile. Usa la lettura assistita qui sotto: il record resta da verificare e non viene classificato come abstract assente.";
      source.textContent = "Abstract ancora da risolvere";
      note.textContent = trace
        ? `Già interrogati: ${trace}. Una synopsis preparatoria non sostituisce l’abstract dell’autore.`
        : "Una synopsis preparatoria non sostituisce l’abstract dell’autore.";
    } else if (payload?.matchType === "web_search_exhausted") {
      text.textContent =
        "L’abstract non è stato trovato dopo la catena automatica gratuita configurata. Questo significa non trovato, non inesistente.";
      source.textContent = "Ricerca gratuita completata";
      note.textContent = trace ? `Fonti interrogate: ${trace}.` : "La ricerca gratuita non ha prodotto un abstract affidabile.";
    } else if (payload?.matchType === "unavailable") {
      text.textContent =
        "La verifica multi-source non è stata completata per un problema tecnico. Non interpretiamo questo stato come assenza dell’abstract.";
      source.textContent = "Verifica incompleta";
      note.textContent = "Riprova la scheda: il risultato non modifica lo stage editoriale.";
    } else {
      text.textContent =
        "La ricerca dell’abstract non ha ancora prodotto un match affidabile. Il record resta da cercare, non viene classificato automaticamente come abstract assente.";
      source.textContent = matchLabel(payload || {});
      note.textContent = trace ? `Fonti interrogate: ${trace}.` : "La ricerca deve essere completata prima di dichiarare l’abstract non disponibile.";
    }
    if (payload?.articleUrl) setArticleUrl(payload.articleUrl);
  }

  function renderLoading() {
    const text = byId("candidate-abstract-text");
    const source = byId("candidate-abstract-source");
    const note = byId("candidate-abstract-note");
    if (text) text.textContent = "Ricerca modulare gratuita dell’abstract in corso…";
    if (source) {
      source.textContent =
        "OpenAlex · Crossref · Semantic Scholar · DataCite · Unpaywall · CORE · Europe PMC · paper risolto · Jina Reader · Tavily Basic";
    }
    if (note) {
      note.textContent =
        "Le fonti a costo zero vengono interrogate per capacità: prima registri scholarly e paper risolto, poi lettura DOI gratuita, infine search credit-based sul solo paper aperto.";
    }
  }

  function stripMarkdown(value) {
    return String(value || "")
      .replace(/^`|`$/g, "")
      .replace(/^<|>$/g, "")
      .replace(/\*\*/g, "")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, "$1")
      .trim();
  }

  function markdownSection(body, heading) {
    const source = String(body || "").replace(/\r\n/g, "\n");
    const marker = `## ${heading}`;
    const start = source.indexOf(marker);
    if (start < 0) return "";
    const remainder = source.slice(start + marker.length).replace(/^\s*\n/, "");
    const next = remainder.search(/^##\s/m);
    return (next >= 0 ? remainder.slice(0, next) : remainder).trim();
  }

  function bulletFields(section) {
    const fields = {};
    for (const line of String(section || "").split("\n")) {
      const match = line.match(/^- ([^:]+):\s*(.*)$/);
      if (match) fields[match[1].trim()] = stripMarkdown(match[2]);
    }
    return fields;
  }

  function approachText(section) {
    const match = String(section || "").match(/\*\*How to approach this record:\*\*\s*(.+?)(?=\n\n|$)/s);
    return match ? stripMarkdown(match[1].replace(/\s+/g, " ")) : "";
  }

  function parseReviewSupport(body) {
    const aidSection = markdownSection(body, "Reading aid — preparatory");
    const guidanceSection = markdownSection(body, "Review guidance — preparatory");
    return {
      aid: aidSection ? bulletFields(aidSection) : null,
      guidance: guidanceSection ? {
        ...bulletFields(guidanceSection),
        approach: approachText(guidanceSection),
      } : null,
    };
  }

  async function fetchReviewSupport(signal) {
    const issue = selectedIssueInfo();
    if (!issue) return { aid: null, guidance: null };
    const key = `${issue.owner}/${issue.repo}#${issue.number}`;
    if (supportCache.has(key)) return supportCache.get(key);
    const target = `https://api.github.com/repos/${encodeURIComponent(issue.owner)}/${encodeURIComponent(issue.repo)}/issues/${issue.number}`;
    const response = await fetch(target, {
      signal,
      headers: {
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
      },
    });
    if (!response.ok) throw new Error(`review_support_${response.status}`);
    const payload = await response.json();
    const parsed = parseReviewSupport(payload?.body || "");
    supportCache.set(key, parsed);
    return parsed;
  }

  function aidKindLabel(kind) {
    const labels = {
      verified_abstract_source: "Abstract/source verificata",
      publisher_summary: "Summary dell’editore",
      full_text_intro: "Introduzione/full text",
      review_synopsis: "Synopsis preparatoria",
      metadata_warning: "Avviso metadati",
    };
    return labels[kind] || kind || "Supporto preparatorio";
  }

  function renderReviewSupport(payload) {
    ensureReadingSurface();
    const aidPanel = byId("candidate-reading-aid-panel");
    const aidKind = byId("candidate-reading-aid-kind");
    const aidText = byId("candidate-reading-aid-text");
    const aidNote = byId("candidate-reading-aid-note");
    const guidancePanel = byId("candidate-review-guidance-panel");
    const gate = byId("candidate-review-gate");
    const guidanceText = byId("candidate-review-guidance-text");
    const guidanceNote = byId("candidate-review-guidance-note");

    if (payload?.aid) {
      aidPanel.hidden = false;
      aidKind.textContent = aidKindLabel(payload.aid["Aid kind"]);
      aidText.textContent = payload.aid["Review synopsis"] || "Synopsis non disponibile.";
      const source = payload.aid.Source || "fonte verificata";
      const checked = payload.aid["Last checked"] || "data non registrata";
      const note = payload.aid.Note || "";
      aidNote.replaceChildren();
      const sourceUrl = safeHttpsUrl(payload.aid["Source URL"]);
      const prefix = document.createTextNode(`Fonte: ${source} · verificata: ${checked}. `);
      aidNote.append(prefix);
      if (sourceUrl) {
        const link = document.createElement("a");
        link.href = sourceUrl;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "Apri la fonte ↗";
        aidNote.append(link, document.createTextNode(note ? ` · ${note}` : ""));
      } else if (note) {
        aidNote.append(document.createTextNode(note));
      }
    } else {
      aidPanel.hidden = true;
    }

    if (payload?.guidance) {
      guidancePanel.hidden = false;
      gate.textContent = payload.guidance["Current gate"] || "Gate da verificare";
      const focus = payload.guidance["Candidate-specific focus"] || "Applica il codebook corrente.";
      const approach = payload.guidance.approach || "Applica il four-part infiltration test senza forzare una decisione binaria.";
      guidanceText.textContent = `${focus} ${approach}`;
      const stage = payload.guidance["Suggested screening stage"] || "non registrato";
      const triage = payload.guidance["Prior triage signal"] || "nessuno";
      guidanceNote.textContent =
        `Stage suggerito: ${stage}. Segnale precedente: ${triage}. ` +
        "La guida non decide per te: eligible_core richiede tutti e quattro gli elementi; se l’evidenza non basta usa maybe_full_text_needed; AML adiacente resta separato dal corpus infiltration.";
    } else {
      guidancePanel.hidden = false;
      gate.textContent = "Guida non sincronizzata";
      guidanceText.textContent =
        "La scheda non espone ancora la review guidance governata. Usa il four-part test e non assumere che il segnale di intake equivalga a una decisione.";
      guidanceNote.textContent = "La decisione resta sempre umana e attribuita.";
    }
  }

  async function refreshReviewSupport(candidateId) {
    supportController?.abort();
    supportController = new AbortController();
    const signal = supportController.signal;
    try {
      const payload = await fetchReviewSupport(signal);
      if (activeCandidateId !== candidateId) return;
      renderReviewSupport(payload);
    } catch (error) {
      if (error?.name === "AbortError" || activeCandidateId !== candidateId) return;
      renderReviewSupport({ aid: null, guidance: null });
    }
  }

  async function fetchResolvedAbstract(candidateId, issueNumber, title, token, signal) {
    if (!issueNumber) return null;
    const target = new URL(`${apiBaseUrl}/api/resolved-abstract`);
    target.searchParams.set("candidate", candidateId);
    target.searchParams.set("issue", String(issueNumber));
    target.searchParams.set("title", title);
    const response = await fetch(target, {
      headers: { Authorization: `Bearer ${token}` },
      signal,
    });
    if (!response.ok) return null;
    return response.json();
  }

  async function fetchFreeWebSearch(candidateId, issueNumber, title, doi, year, token, signal) {
    if (!issueNumber) return null;
    const target = new URL(`${apiBaseUrl}/api/free-web-search`);
    target.searchParams.set("candidate", candidateId);
    target.searchParams.set("issue", String(issueNumber));
    target.searchParams.set("title", title);
    if (doi && doi !== "Non registrato") target.searchParams.set("doi", doi);
    if (year && year !== "Non registrato") target.searchParams.set("year", year);
    const response = await fetch(target, {
      headers: { Authorization: `Bearer ${token}` },
      signal,
    });
    if (!response.ok) return null;
    return response.json();
  }

  async function fetchEnrichment(candidateId, title, doi, year) {
    const issueNumber = selectedIssueNumber();
    const key = [candidateId, issueNumber || "", title, doi, year].join("|");
    if (cache.has(key)) return cache.get(key);
    if (!apiBaseUrl) return null;
    const token = sessionToken();
    if (!token) return null;

    activeController?.abort();
    activeController = new AbortController();
    const signal = activeController.signal;
    const target = new URL(`${apiBaseUrl}/api/enrichment`);
    target.searchParams.set("title", title);
    if (doi && doi !== "Non registrato") target.searchParams.set("doi", doi);
    if (year && year !== "Non registrato") target.searchParams.set("year", year);

    let primary = { matchType: "unavailable", abstract: "", providersTried: [] };
    try {
      const response = await fetch(target, {
        headers: { Authorization: `Bearer ${token}` },
        signal,
      });
      if (response.ok) primary = await response.json();
    } catch (error) {
      if (error?.name === "AbortError") throw error;
    }
    if (String(primary?.abstract || "").trim()) {
      cache.set(key, primary);
      return primary;
    }

    let result = primary;
    try {
      const resolved = await fetchResolvedAbstract(candidateId, issueNumber, title, token, signal);
      if (String(resolved?.abstract || "").trim()) {
        result = {
          ...resolved,
          providersTried: [...(primary.providersTried || []), "paper/repository resolved"],
          providerErrors: primary.providerErrors || [],
          providerPlan: primary.providerPlan || [],
          searchStatus: "found",
        };
        cache.set(key, result);
        return result;
      }
      if (resolved) {
        result = {
          ...primary,
          articleUrl: resolved.articleUrl || primary.articleUrl,
          providersTried: [...(primary.providersTried || []), "paper/repository resolved"],
          providerErrors: primary.providerErrors || [],
          matchType: "needs_web_search",
          searchStatus: "needs_web_search",
        };
      }
    } catch (error) {
      if (error?.name === "AbortError") throw error;
    }

    try {
      const freeWeb = await fetchFreeWebSearch(candidateId, issueNumber, title, doi, year, token, signal);
      if (freeWeb) {
        const providers = [...(result.providersTried || [])];
        for (const provider of freeWeb.providersTried || []) {
          if (!providers.includes(provider)) providers.push(provider);
        }
        result = {
          ...result,
          ...freeWeb,
          articleUrl: freeWeb.articleUrl || result.articleUrl,
          providersTried: providers,
          providerErrors: [...(result.providerErrors || []), ...(freeWeb.providerErrors || [])],
          providerPlan: freeWeb.providerPlan?.length ? freeWeb.providerPlan : result.providerPlan || [],
        };
      }
    } catch (error) {
      if (error?.name === "AbortError") throw error;
    }

    cache.set(key, result);
    return result;
  }

  async function refreshReadingSurface() {
    const detail = byId("candidate-detail");
    if (!detail || detail.hidden) return;
    ensureReadingSurface();

    const candidateId = byId("selected-candidate-id")?.textContent?.trim() || "";
    const title = byId("selected-candidate-title")?.textContent?.trim() || "";
    const doi = byId("selected-candidate-doi")?.textContent?.trim() || "";
    const year = byId("selected-candidate-year")?.textContent?.trim() || "";
    if (!candidateId || !title || candidateId === "—" || title === "—") return;

    renderByline();
    setArticleUrl(provenanceArticleUrl());
    const candidateChanged = candidateId !== activeCandidateId;
    if (candidateChanged) activeCandidateId = candidateId;
    void refreshReviewSupport(candidateId);

    const abstractText = byId("candidate-abstract-text");
    if (!candidateChanged && abstractText?.dataset.loaded === "true") return;
    if (abstractText) delete abstractText.dataset.loaded;
    renderLoading();

    try {
      const payload = await fetchEnrichment(candidateId, title, doi, year);
      if (activeCandidateId !== candidateId) return;
      renderAbstract(payload || {});
      if (abstractText) abstractText.dataset.loaded = "true";
    } catch (error) {
      if (error?.name === "AbortError" || activeCandidateId !== candidateId) return;
      renderAbstract({ matchType: "unavailable" });
      if (abstractText) abstractText.dataset.loaded = "true";
    }
  }

  function observeCandidateChanges() {
    const detail = byId("candidate-detail");
    const id = byId("selected-candidate-id");
    if (!detail || !id) return;
    const observer = new MutationObserver(() => queueMicrotask(refreshReadingSurface));
    observer.observe(detail, { attributes: true, attributeFilter: ["hidden"] });
    observer.observe(id, { childList: true, characterData: true, subtree: true });
    observer.observe(byId("candidate-provenance") || detail, { childList: true, subtree: true });
    observer.observe(byId("selected-candidate-issue") || detail, {
      attributes: true,
      attributeFilter: ["href"],
    });
    queueMicrotask(refreshReadingSurface);
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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialise, { once: true });
  } else {
    initialise();
  }
})();
