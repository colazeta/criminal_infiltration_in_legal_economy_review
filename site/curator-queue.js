"use strict";

(() => {
  const SESSION_KEY = "criminal-infiltration-curator-session";
  const PAGE_SIZE = 12;
  const config = window.CURATOR_APP_CONFIG || {};
  const apiBaseUrl = String(config.apiBaseUrl || "").replace(/\/$/, "");

  let queuePage = 1;
  let resetPageRequested = false;
  let candidatePromise = null;
  let candidateMap = new Map();
  let listObserver = null;

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

  function provenanceValue(candidate, label) {
    const rows = Array.isArray(candidate?.provenance) ? candidate.provenance : [];
    const match = rows.find((row) => String(row?.label || "").trim() === label);
    return String(match?.value || "").trim();
  }

  function triageCode(candidate) {
    if (!candidate) return "standard";
    if (candidate.provenanceKind === "daily") {
      const assessment = provenanceValue(candidate, "Intake assessment");
      if (assessment === "plausible_core") return "priority_core";
      if (assessment === "plausible_contextual" || assessment === "uncertain") return "boundary";
    }
    const legacyScope = provenanceValue(candidate, "Legacy scope label");
    if (
      candidate.provenanceKind === "legacy" &&
      candidate.stageLabel === "stage:legacy-rejection-review" &&
      legacyScope === "outside_scope"
    ) {
      return "legacy_fast_recheck";
    }
    return "standard";
  }

  function ensureGridHeader() {
    const list = byId("candidate-list");
    if (!list || byId("candidate-grid-header")) return;
    const header = document.createElement("div");
    header.id = "candidate-grid-header";
    header.className = "candidate-grid-header";
    for (const label of ["ID", "TITOLO", "AUTORI", "ANNO / SEDE", "STAGE"]) {
      const cell = document.createElement("span");
      cell.textContent = label;
      header.append(cell);
    }
    list.insertAdjacentElement("beforebegin", header);
  }

  function enhanceCard(card) {
    if (!(card instanceof HTMLElement) || card.dataset.queueEnhanced === "true") return;
    const candidateId = cardCandidateId(card);
    if (!candidateId) return;
    card.dataset.candidateId = candidateId;
    card.dataset.queueEnhanced = "true";

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
    citation.textContent = citationParts.join(" · ") || "Anno e sede da verificare";

    const doi = document.createElement("span");
    doi.className = "queue-card-doi";
    doi.textContent = candidate?.doi ? `DOI ${candidate.doi}` : "DOI non registrato";
    if (candidate?.doi) doi.title = candidate.doi;

    const chips = document.createElement("span");
    chips.className = "queue-card-chips";

    card.dataset.triage = triageCode(candidate);
    oldMeta.insertAdjacentElement("afterend", citation);
    citation.insertAdjacentElement("afterend", doi);
    doi.insertAdjacentElement("afterend", chips);
  }

  function ensureTriageFilter() {
    const controls = document.querySelector(".candidate-controls");
    if (!controls || byId("candidate-triage-filter")) return;
    const label = document.createElement("label");
    const caption = document.createElement("span");
    caption.textContent = "PRIORITÀ";
    const select = document.createElement("select");
    select.id = "candidate-triage-filter";
    const options = [
      ["", "TUTTE LE PRIORITÀ"],
      ["priority_core", "PRIORITÀ CORE"],
      ["boundary", "CONFINE DA VALUTARE"],
      ["legacy_fast_recheck", "RIESAME RAPIDO"],
      ["standard", "CODA STANDARD"],
    ];
    for (const [value, text] of options) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = text;
      select.append(option);
    }
    select.title = "Vista derivata dalla provenienza registrata; non è una decisione scientifica.";
    select.addEventListener("change", () => {
      resetPageRequested = true;
      applyPagination();
    });
    label.append(caption, select);
    controls.append(label);
  }

  function allCards() {
    const list = byId("candidate-list");
    return list ? Array.from(list.querySelectorAll(":scope > .candidate-card")) : [];
  }

  function currentCards() {
    const triage = String(byId("candidate-triage-filter")?.value || "");
    const cards = allCards();
    return triage ? cards.filter((card) => card.dataset.triage === triage) : cards;
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
    previous.textContent = "← PRECEDENTI";
    previous.addEventListener("click", () => {
      if (queuePage <= 1) return;
      queuePage -= 1;
      applyPagination();
      list.scrollTo({ top: 0 });
    });

    const info = document.createElement("span");
    info.id = "candidate-page-info";
    info.className = "candidate-page-info";

    const next = document.createElement("button");
    next.type = "button";
    next.id = "candidate-page-next";
    next.className = "candidate-page-button";
    next.textContent = "SUCCESSIVI →";
    next.addEventListener("click", () => {
      const pages = Math.max(1, Math.ceil(currentCards().length / PAGE_SIZE));
      if (queuePage >= pages) return;
      queuePage += 1;
      applyPagination();
      list.scrollTo({ top: 0 });
    });

    pager.append(previous, info, next);
    list.insertAdjacentElement("afterend", pager);
    return pager;
  }

  function applyPagination() {
    const all = allCards();
    const cards = currentCards();
    const matching = new Set(cards);
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
    for (const card of all) card.hidden = !matching.has(card);
    for (const [index, card] of cards.entries()) card.hidden = index < start || index >= end;

    const pager = ensurePager();
    if (pager) pager.hidden = total <= PAGE_SIZE;
    const previous = byId("candidate-page-previous");
    const next = byId("candidate-page-next");
    if (previous) previous.disabled = queuePage <= 1;
    if (next) next.disabled = queuePage >= pages;
    const info = byId("candidate-page-info");
    if (info) info.textContent = total ? `${start + 1}–${end} / ${total}` : "0 RISULTATI";
    const count = byId("candidate-result-count");
    if (count) count.textContent = total ? `${start + 1}–${end} / ${total}` : "0 RECORD";
  }

  async function refreshQueue() {
    await loadCandidates();
    ensureGridHeader();
    ensureTriageFilter();
    for (const card of allCards()) enhanceCard(card);
    applyPagination();
  }

  function observeList() {
    const list = byId("candidate-list");
    if (!list || listObserver) return;
    listObserver = new MutationObserver(() => queueMicrotask(refreshQueue));
    listObserver.observe(list, { childList: true });
  }

  function initialise() {
    loadQueueStyles();
    ensureGridHeader();
    ensureTriageFilter();
    observeList();
    queueMicrotask(refreshQueue);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialise, { once: true });
  } else {
    initialise();
  }
})();
