"use strict";

(() => {
  const SESSION_KEY = "criminal-infiltration-curator-session";
  const PAGE_SIZE = 12;
  const MAX_ENRICHMENT_CONCURRENCY = 3;
  const config = window.CURATOR_APP_CONFIG || {};
  const apiBaseUrl = String(config.apiBaseUrl || "").replace(/\/$/, "");

  let queuePage = 1;
  let resetPageRequested = false;
  let candidatePromise = null;
  let candidateMap = new Map();
  let listObserver = null;
  let viewportObserver = null;
  let activeEnrichments = 0;
  const enrichmentQueue = [];
  const enrichmentPending = new Set();
  const enrichmentCache = new Map();

  const byId = (id) => document.getElementById(id);

  function sessionToken() {
    try {
      return sessionStorage.getItem(SESSION_KEY) || "";
    } catch {
      return "";
    }
  }

  function loadQueueStyles() {
    if (document.querySelector('link[data-curator-queue="true"]')) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "./curator-queue.css";
    link.dataset.curatorQueue = "true";
    document.head.append(link);
  }

  async function loadCandidates() {
    if (candidatePromise) return candidatePromise;
    const token = sessionToken();
    if (!apiBaseUrl || !token) return [];
    candidatePromise = fetch(`${apiBaseUrl}/api/candidates`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("candidate_queue_unavailable");
        const payload = await response.json();
        const rows = Array.isArray(payload.candidates) ? payload.candidates : [];
        candidateMap = new Map(rows.map((row) => [row.candidateId, row]));
        return rows;
      })
      .catch(() => {
        candidatePromise = null;
        return [];
      });
    return candidatePromise;
  }

  function cardCandidateId(card) {
    return card.querySelector("code")?.textContent?.trim() || "";
  }

  function makeText(className, value, fallback = "") {
    const node = document.createElement("span");
    node.className = className;
    node.textContent = value || fallback;
    return node;
  }

  function makeChip(label, state = "neutral", role = "") {
    const chip = document.createElement("span");
    chip.className = "queue-card-chip";
    chip.dataset.state = state;
    if (role) chip.dataset.role = role;
    chip.textContent = label;
    return chip;
  }

  function applyCachedAbstractStatus(card, candidateId) {
    const cached = enrichmentCache.get(candidateId);
    if (!cached) return false;
    renderAbstractBadge(candidateId, cached);
    return true;
  }

  function enhanceCard(card) {
    const candidateId = cardCandidateId(card);
    if (!candidateId) return;
    card.dataset.candidateId = candidateId;

    const candidate = candidateMap.get(candidateId);
    const top = card.querySelector(".candidate-card-top");
    const title = card.querySelector("strong");
    const oldMeta = card.querySelector(".candidate-card-meta");
    if (!top || !title || !oldMeta) return;

    card.classList.add("queue-review-card");
    title.classList.add("queue-card-title");
    const stage = top.querySelector("small");
    if (stage) stage.classList.add("queue-stage-badge");

    oldMeta.className = "queue-card-authors";
    const fallbackAuthors = oldMeta.textContent.split(" · ")[0]?.trim() || "";
    oldMeta.textContent = candidate?.authors || fallbackAuthors || "Autori da verificare";

    card.querySelector(".queue-card-citation")?.remove();
    card.querySelector(".queue-card-doi")?.remove();
    card.querySelector(".queue-card-chips")?.remove();

    const citation = document.createElement("span");
    citation.className = "queue-card-citation";
    const citationParts = [candidate?.year, candidate?.venue].filter(Boolean);
    citation.textContent = citationParts.join(" · ") || "Anno e sede editoriale da verificare";

    const doi = document.createElement("span");
    doi.className = "queue-card-doi";
    doi.textContent = candidate?.doi ? `DOI ${candidate.doi}` : "DOI non registrato";
    if (candidate?.doi) doi.title = candidate.doi;

    const chips = document.createElement("span");
    chips.className = "queue-card-chips";
    chips.append(
      makeChip(candidate?.doi ? "DOI" : "senza DOI", candidate?.doi ? "positive" : "neutral", "doi-status"),
      makeChip("Abstract · verifica", "loading", "abstract-status"),
    );
    if (candidate?.source) chips.append(makeChip(candidate.source, "source", "source"));

    oldMeta.insertAdjacentElement("afterend", citation);
    citation.insertAdjacentElement("afterend", doi);
    doi.insertAdjacentElement("afterend", chips);

    if (!applyCachedAbstractStatus(card, candidateId) && candidate) viewportObserver?.observe(card);
  }

  function currentCards() {
    const list = byId("candidate-list");
    return list ? Array.from(list.querySelectorAll(":scope > .candidate-card")) : [];
  }

  function ensurePager() {
    const list = byId("candidate-list");
    if (!list) return null;
    let pager = byId("candidate-queue-pager");
    if (pager) return pager;

    pager = document.createElement("div");
    pager.id = "candidate-queue-pager";
    pager.className = "candidate-queue-pager";

    const previous = document.createElement("button");
    previous.type = "button";
    previous.id = "candidate-page-previous";
    previous.className = "candidate-page-button";
    previous.textContent = "← Precedenti";
    previous.addEventListener("click", () => {
      if (queuePage <= 1) return;
      queuePage -= 1;
      applyPagination();
      list.scrollTo({ top: 0, behavior: "smooth" });
    });

    const info = document.createElement("span");
    info.id = "candidate-page-info";
    info.className = "candidate-page-info";

    const next = document.createElement("button");
    next.type = "button";
    next.id = "candidate-page-next";
    next.className = "candidate-page-button";
    next.textContent = "Successivi →";
    next.addEventListener("click", () => {
      const pages = Math.max(1, Math.ceil(currentCards().length / PAGE_SIZE));
      if (queuePage >= pages) return;
      queuePage += 1;
      applyPagination();
      list.scrollTo({ top: 0, behavior: "smooth" });
    });

    pager.append(previous, info, next);
    list.insertAdjacentElement("afterend", pager);
    return pager;
  }

  function applyPagination() {
    const cards = currentCards();
    const total = cards.length;
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

    if (resetPageRequested) {
      queuePage = 1;
      resetPageRequested = false;
    } else {
      const selectedIndex = cards.findIndex((card) => card.dataset.selected === "true");
      if (selectedIndex >= 0) queuePage = Math.floor(selectedIndex / PAGE_SIZE) + 1;
    }
    queuePage = Math.min(Math.max(queuePage, 1), pages);

    const start = (queuePage - 1) * PAGE_SIZE;
    const end = Math.min(start + PAGE_SIZE, total);
    for (const [index, card] of cards.entries()) card.hidden = index < start || index >= end;

    const pager = ensurePager();
    if (pager) pager.hidden = total <= PAGE_SIZE;
    const previous = byId("candidate-page-previous");
    const next = byId("candidate-page-next");
    if (previous) previous.disabled = queuePage <= 1;
    if (next) next.disabled = queuePage >= pages;
    const info = byId("candidate-page-info");
    if (info) info.textContent = total ? `${start + 1}–${end} di ${total}` : "0 risultati";

    const count = byId("candidate-result-count");
    if (count) count.textContent = total ? `${start + 1}–${end} di ${total}` : "0 schede";
  }

  function matchLabel(payload) {
    if (payload?.matchType === "doi") return "DOI verificato";
    if (payload?.matchType === "title_year") return "Titolo + anno verificati";
    if (payload?.matchType === "unavailable") return "Servizio non disponibile";
    return "Nessun match affidabile";
  }

  function renderAbstractBadge(candidateId, payload) {
    for (const card of document.querySelectorAll(`.candidate-card[data-candidate-id="${CSS.escape(candidateId)}"]`)) {
      const badge = card.querySelector('[data-role="abstract-status"]');
      if (!badge) continue;
      if (String(payload?.abstract || "").trim()) {
        badge.textContent = "Abstract disponibile";
        badge.dataset.state = "positive";
        badge.title = `${payload.abstractSource || "Fonte bibliografica"} · ${matchLabel(payload)}`;
      } else if (payload?.matchType === "unavailable") {
        badge.textContent = "Abstract non verificato";
        badge.dataset.state = "warning";
        badge.title = "Il servizio bibliografico non ha completato la verifica.";
      } else {
        badge.textContent = "Abstract assente";
        badge.dataset.state = "neutral";
        badge.title = matchLabel(payload || {});
      }
    }
  }

  async function fetchEnrichment(candidate) {
    const token = sessionToken();
    if (!token || !apiBaseUrl) return { matchType: "unavailable", abstract: "" };
    const target = new URL(`${apiBaseUrl}/api/enrichment`);
    target.searchParams.set("title", candidate.title || "");
    if (candidate.doi) target.searchParams.set("doi", candidate.doi);
    if (candidate.year) target.searchParams.set("year", candidate.year);
    const response = await fetch(target, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) return { matchType: "unavailable", abstract: "" };
    return response.json();
  }

  function scheduleEnrichment(card) {
    const candidateId = card.dataset.candidateId || cardCandidateId(card);
    const candidate = candidateMap.get(candidateId);
    if (!candidate || enrichmentCache.has(candidateId) || enrichmentPending.has(candidateId)) return;
    enrichmentPending.add(candidateId);
    enrichmentQueue.push({ candidateId, candidate });
    pumpEnrichmentQueue();
  }

  function pumpEnrichmentQueue() {
    while (activeEnrichments < MAX_ENRICHMENT_CONCURRENCY && enrichmentQueue.length) {
      const task = enrichmentQueue.shift();
      activeEnrichments += 1;
      fetchEnrichment(task.candidate)
        .catch(() => ({ matchType: "unavailable", abstract: "" }))
        .then((payload) => {
          enrichmentCache.set(task.candidateId, payload);
          renderAbstractBadge(task.candidateId, payload);
        })
        .finally(() => {
          enrichmentPending.delete(task.candidateId);
          activeEnrichments -= 1;
          pumpEnrichmentQueue();
        });
    }
  }

  async function refreshQueueCards() {
    const list = byId("candidate-list");
    if (!list) return;
    await loadCandidates();
    for (const card of currentCards()) enhanceCard(card);
    applyPagination();
  }

  function createViewportObserver() {
    const list = byId("candidate-list");
    if (!list || typeof IntersectionObserver === "undefined") return null;
    return new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting || entry.target.hidden) continue;
          viewportObserver?.unobserve(entry.target);
          scheduleEnrichment(entry.target);
        }
      },
      { root: list, rootMargin: "180px 0px", threshold: 0.01 },
    );
  }

  function observeList() {
    const list = byId("candidate-list");
    if (!list) return;
    viewportObserver = createViewportObserver();
    listObserver = new MutationObserver(() => queueMicrotask(refreshQueueCards));
    listObserver.observe(list, { childList: true });
    queueMicrotask(refreshQueueCards);
  }

  function resetPageBeforeFiltering() {
    resetPageRequested = true;
  }

  function wireFilterReset() {
    byId("candidate-search")?.addEventListener("input", resetPageBeforeFiltering, { capture: true });
    byId("candidate-lane-filter")?.addEventListener("change", resetPageBeforeFiltering, { capture: true });
  }

  function initialise() {
    loadQueueStyles();
    wireFilterReset();
    observeList();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialise, { once: true });
  else initialise();
})();
