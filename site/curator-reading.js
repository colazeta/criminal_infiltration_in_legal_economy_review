"use strict";

(() => {
  const SESSION_KEY = "criminal-infiltration-curator-session";
  const config = window.CURATOR_APP_CONFIG || {};
  const apiBaseUrl = String(config.apiBaseUrl || "").replace(/\/$/, "");
  const cache = new Map();
  let activeCandidateId = "";
  let activeController = null;

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

  function selectedIssueNumber() {
    const href = byId("selected-candidate-issue")?.href || "";
    const match = href.match(/\/issues\/(\d+)(?:[/?#]|$)/);
    return match ? Number(match[1]) : null;
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
      const title = byId("selected-candidate-title");
      title?.insertAdjacentElement("afterend", byline);
    }

    let panel = byId("candidate-abstract-panel");
    if (!panel) {
      panel = document.createElement("section");
      panel.id = "candidate-abstract-panel";
      panel.className = "candidate-abstract-panel";
      panel.setAttribute("aria-labelledby", "candidate-abstract-title");

      const header = document.createElement("div");
      header.className = "candidate-abstract-heading";

      const titleGroup = document.createElement("div");
      const eyebrow = document.createElement("p");
      eyebrow.className = "workspace-label";
      eyebrow.textContent = "Lettura rapida";
      const title = document.createElement("h4");
      title.id = "candidate-abstract-title";
      title.textContent = "Abstract";
      titleGroup.append(eyebrow, title);

      const source = document.createElement("span");
      source.id = "candidate-abstract-source";
      source.className = "candidate-abstract-source";
      source.textContent = "Da recuperare";
      header.append(titleGroup, source);

      const body = document.createElement("p");
      body.id = "candidate-abstract-text";
      body.className = "candidate-abstract-text";
      body.textContent = "Seleziona una scheda per recuperare l’abstract.";

      const note = document.createElement("p");
      note.id = "candidate-abstract-note";
      note.className = "candidate-abstract-note";
      note.textContent = "L’abstract è un ausilio alla revisione e non viene scritto nell’archivio pubblico.";

      panel.append(header, body, note);
      detail.querySelector(".candidate-metadata")?.insertAdjacentElement("afterend", panel);
    }

    return { articleLink, byline, panel };
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

  function matchLabel(payload) {
    if (payload.matchType === "doi") return "DOI verificato";
    if (payload.matchType === "title_year") return "Titolo + anno verificati";
    if (payload.matchType === "resolved_url") return "Paper risolto verificato";
    if (payload.matchType === "resolved_url_none") return "Paper risolto, abstract non esposto";
    if (payload.matchType === "unavailable") return "Servizio non disponibile";
    return "Nessun match affidabile";
  }

  function renderAbstract(payload) {
    const text = byId("candidate-abstract-text");
    const source = byId("candidate-abstract-source");
    const note = byId("candidate-abstract-note");
    if (!text || !source || !note) return;

    const abstract = String(payload?.abstract || "").trim();
    if (abstract) {
      text.textContent = abstract;
      source.textContent = `${payload.abstractSource || "Fonte bibliografica"} · ${matchLabel(payload)}`;
      note.textContent =
        "Abstract recuperato al momento della consultazione e mostrato solo nella console autenticata; non viene persistito nel corpus pubblico.";
    } else {
      text.textContent =
        "Abstract non disponibile né nei metadati bibliografici né nelle manifestazioni online del paper già risolte. Puoi comunque aprire l’articolo o la fonte registrata dalla scheda.";
      source.textContent = matchLabel(payload || {});
      note.textContent =
        "L’assenza dell’abstract non è un giudizio sul paper e non modifica lo stage di revisione.";
    }
    if (payload?.articleUrl) setArticleUrl(payload.articleUrl);
  }

  function renderLoading() {
    const text = byId("candidate-abstract-text");
    const source = byId("candidate-abstract-source");
    const note = byId("candidate-abstract-note");
    if (text) text.textContent = "Recupero dell’abstract in corso…";
    if (source) source.textContent = "OpenAlex / Crossref / paper risolto";
    if (note) note.textContent = "Il match viene controllato prima di mostrare il testo.";
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

    let primary = { matchType: "unavailable", abstract: "" };
    try {
      const response = await fetch(target, {
        headers: { Authorization: `Bearer ${token}` },
        signal,
      });
      if (response.ok) primary = await response.json();
    } catch (error) {
      if (error?.name === "AbortError") throw error;
    }
    let result = primary;
    if (!String(primary?.abstract || "").trim()) {
      try {
        const resolved = await fetchResolvedAbstract(candidateId, issueNumber, title, token, signal);
        if (String(resolved?.abstract || "").trim()) result = resolved;
        else if (primary?.matchType === "unavailable" && resolved) result = resolved;
      } catch (error) {
        if (error?.name === "AbortError") throw error;
      }
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
    if (candidateId === activeCandidateId && byId("candidate-abstract-text")?.dataset.loaded === "true") return;
    activeCandidateId = candidateId;
    const abstractText = byId("candidate-abstract-text");
    if (abstractText) delete abstractText.dataset.loaded;
    renderLoading();

    try {
      const payload = await fetchEnrichment(candidateId, title, doi, year);
      if (activeCandidateId !== candidateId) return;
      renderAbstract(payload || {});
      if (abstractText) abstractText.dataset.loaded = "true";
    } catch (error) {
      if (error?.name === "AbortError") return;
      if (activeCandidateId !== candidateId) return;
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
    observer.observe(byId("selected-candidate-issue") || detail, { attributes: true, attributeFilter: ["href"] });
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

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialise, { once: true });
  else initialise();
})();
