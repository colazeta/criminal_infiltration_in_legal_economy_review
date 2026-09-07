"use strict";

(() => {
  const RESOLUTION_HEADING = "## Abstract resolution — assisted";
  const READING_HEADING = "## Reading aid — preparatory";
  const byId = (id) => document.getElementById(id);
  const issueCache = new Map();
  const originalFetch = window.fetch.bind(window);
  let activeIssueKey = "";
  let refreshQueued = false;

  function clean(value) {
    return String(value || "")
      .replace(/^`|`$/g, "")
      .replace(/^<|>$/g, "")
      .replace(/\*\*/g, "")
      .trim();
  }

  function safeHttps(value) {
    try {
      const url = new URL(clean(value));
      return url.protocol === "https:" ? url.toString() : "";
    } catch {
      return "";
    }
  }

  function issueInfo() {
    const link = byId("selected-candidate-issue");
    if (!(link instanceof HTMLAnchorElement)) return null;
    const match = link.href.match(/github\.com\/([^/]+)\/([^/]+)\/issues\/(\d+)/);
    if (!match) return null;
    return { owner: match[1], repo: match[2], number: Number(match[3]) };
  }

  function issueKey(info) {
    return info ? `${info.owner}/${info.repo}#${info.number}` : "";
  }

  function issueKeyFromRequest(input) {
    try {
      const raw = typeof input === "string" || input instanceof URL ? String(input) : String(input?.url || "");
      const url = new URL(raw, window.location.href);
      if (url.hostname !== "api.github.com") return "";
      const match = url.pathname.match(/^\/repos\/([^/]+)\/([^/]+)\/issues\/(\d+)$/);
      if (!match) return "";
      return `${decodeURIComponent(match[1])}/${decodeURIComponent(match[2])}#${Number(match[3])}`;
    } catch {
      return "";
    }
  }

  function section(body, heading) {
    const source = String(body || "").replace(/\r\n/g, "\n");
    const start = source.indexOf(heading);
    if (start < 0) return "";
    const remainder = source.slice(start + heading.length).replace(/^\s*\n/, "");
    const next = remainder.search(/^##\s/m);
    return (next >= 0 ? remainder.slice(0, next) : remainder).trim();
  }

  function fields(source) {
    const result = {};
    for (const line of String(source || "").split("\n")) {
      const match = line.match(/^- ([^:]+):\s*(.*)$/);
      if (match) result[match[1].trim()] = clean(match[2]);
    }
    return result;
  }

  function parseIssuePayload(payload) {
    const body = String(payload?.body || "");
    const resolution = section(body, RESOLUTION_HEADING);
    const aid = section(body, READING_HEADING);
    return {
      candidateMarker: body.match(/<!--\s*curator-candidate:([^\s]+)\s*-->/)?.[1] || "",
      resolution: resolution ? fields(resolution) : null,
      aid: aid ? fields(aid) : null,
    };
  }

  function node(tag, options = {}) {
    const element = document.createElement(tag);
    if (options.id) element.id = options.id;
    if (options.className) element.className = options.className;
    if (options.text !== undefined) element.textContent = options.text;
    return element;
  }

  function stateLabel(value) {
    const labels = {
      full_text_or_intro_ready: "TESTO PRONTO",
      publisher_summary_ready: "SUMMARY PRONTO",
      metadata_only: "RETRIEVAL PRIORITARIO",
      known_noise: "RUMORE NOTO",
    };
    return labels[value] || "STATO ASSISTITO";
  }

  function stateTitle(value) {
    const labels = {
      full_text_or_intro_ready: "Reviewable dal testo esatto",
      publisher_summary_ready: "Reviewable dalla fonte editoriale",
      metadata_only: "Serve ancora evidenza sostanziale",
      known_noise: "Non spendere altro retrieval effort",
    };
    return labels[value] || "Risoluzione assistita";
  }

  function abstractLabel(value) {
    if (value === "not_applicable_noise") return "Abstract non applicabile al record di rumore";
    if (value === "not_verified_after_targeted_search") return "Abstract standalone non verificato dopo ricerca mirata";
    return value || "Stato abstract non registrato";
  }

  function aidLabel(value) {
    const labels = {
      verified_abstract_source: "Sintesi da fonte con abstract verificato",
      publisher_summary: "Summary dell’editore",
      full_text_intro: "Sintesi da full text / introduzione",
      review_synopsis: "Sintesi generata da fonti verificate",
      metadata_warning: "Sintesi dai metadati verificati",
    };
    return labels[value] || "Sintesi preparatoria";
  }

  function injectStyles() {
    if (byId("curator-assisted-resolution-styles")) return;
    const style = node("style", { id: "curator-assisted-resolution-styles" });
    style.textContent = `
      .candidate-assisted-resolution{margin:0;border:1px solid #8b8b8b;border-top:0;padding:9px 10px;background:#fff;box-shadow:none;border-radius:0}
      .assisted-resolution-heading{display:flex;gap:10px;align-items:flex-start;justify-content:space-between}
      .assisted-resolution-heading h4{margin:1px 0 0;font:700 12px Arial,sans-serif}
      .assisted-resolution-chip{border:1px solid #777;padding:2px 5px;background:#eee;color:#111;font:700 10px Arial,sans-serif;border-radius:0}
      .assisted-resolution-abstract,.assisted-resolution-action,.assisted-resolution-note,.assisted-resolution-boundary{margin:5px 0 0;font:11px/1.35 Arial,sans-serif}
      .assisted-resolution-note,.assisted-resolution-boundary,.assisted-resolution-abstract{color:#555}
      .assisted-resolution-source{display:inline-block;margin-top:6px;font:700 11px Arial,sans-serif}
    `;
    document.head.append(style);
  }

  function ensurePanel() {
    let panel = byId("candidate-assisted-resolution-panel");
    if (panel) return panel;
    const detail = byId("candidate-detail");
    if (!detail) return null;
    panel = node("section", { id: "candidate-assisted-resolution-panel", className: "candidate-assisted-resolution" });
    panel.hidden = true;
    const heading = node("div", { className: "assisted-resolution-heading" });
    const titleGroup = node("div");
    titleGroup.append(
      node("p", { className: "workspace-label", text: "Abstract resolution" }),
      node("h4", { id: "candidate-assisted-resolution-title", text: "Risoluzione assistita" }),
    );
    heading.append(
      titleGroup,
      node("span", { id: "candidate-assisted-resolution-chip", className: "assisted-resolution-chip", text: "—" }),
    );
    const abstractState = node("p", { id: "candidate-assisted-resolution-abstract", className: "assisted-resolution-abstract" });
    const action = node("p", { id: "candidate-assisted-resolution-action", className: "assisted-resolution-action" });
    const note = node("p", { id: "candidate-assisted-resolution-note", className: "assisted-resolution-note" });
    const source = node("a", { id: "candidate-assisted-resolution-source", className: "assisted-resolution-source", text: "Apri la fonte assistita ↗" });
    source.target = "_blank";
    source.rel = "noopener noreferrer";
    const boundary = node("p", {
      className: "assisted-resolution-boundary",
      text: "Stato preparatorio: non è una decisione scientifica e non trasforma una sintesi in abstract dell’autore.",
    });
    panel.append(heading, abstractState, action, note, source, boundary);
    const form = byId("decision-form");
    if (form) form.insertAdjacentElement("beforebegin", panel);
    else detail.append(panel);
    return panel;
  }

  function hidePanel() {
    const panel = ensurePanel();
    if (!panel) return;
    panel.hidden = true;
    delete panel.dataset.state;
  }

  function renderResolution(payload) {
    const panel = ensurePanel();
    if (!panel || !payload) return hidePanel();
    const resolutionClass = payload["Resolution class"] || "";
    panel.hidden = false;
    panel.dataset.state = resolutionClass;
    byId("candidate-assisted-resolution-title").textContent = stateTitle(resolutionClass);
    byId("candidate-assisted-resolution-chip").textContent = stateLabel(resolutionClass);
    byId("candidate-assisted-resolution-abstract").textContent = abstractLabel(payload["Standalone abstract status"]);
    byId("candidate-assisted-resolution-action").textContent = payload["Next action"] || "Verifica la fonte assistita prima della decisione.";
    byId("candidate-assisted-resolution-note").textContent = payload.Note || "";
    const source = byId("candidate-assisted-resolution-source");
    const url = safeHttps(payload["Source URL"]);
    if (url) {
      source.href = url;
      source.hidden = false;
      const label = payload["Best assisted source"] || "fonte assistita";
      source.textContent = `Apri ${label} ↗`;
    } else {
      source.hidden = true;
      source.removeAttribute("href");
    }
    document.dispatchEvent(new CustomEvent("curator:assisted-resolution", {
      detail: { resolutionClass, standaloneAbstractStatus: payload["Standalone abstract status"] || "" },
    }));
  }

  function actualAbstractVisible() {
    const note = clean(byId("candidate-abstract-note")?.textContent).toLowerCase();
    return note.includes("abstract recuperato") || note.includes("abstract mostrato solo nella console autenticata");
  }

  function mainSurfaceNeedsSynthesis() {
    if (actualAbstractVisible()) return false;
    const text = clean(byId("candidate-abstract-text")?.textContent).toLowerCase();
    if (!text || text.includes("ricerca modulare gratuita") || text.includes("seleziona una scheda")) return false;
    const missingSignals = [
      "la cascata automatica gratuita",
      "l’abstract non è stato trovato",
      "la verifica multi-source non è stata completata",
      "la ricerca dell’abstract non ha ancora prodotto",
      "abstract standalone non verificato",
    ];
    return missingSignals.some((signal) => text.includes(signal)) || byId("candidate-abstract-panel")?.dataset.evidenceMode === "synthesis";
  }

  function promoteAidToMainSurface(aid) {
    const panel = byId("candidate-abstract-panel");
    const title = byId("candidate-abstract-title");
    const source = byId("candidate-abstract-source");
    const text = byId("candidate-abstract-text");
    const note = byId("candidate-abstract-note");
    if (!panel || !title || !source || !text || !note) return;

    if (actualAbstractVisible()) {
      panel.dataset.evidenceMode = "abstract";
      title.textContent = "Abstract";
      return;
    }

    const synopsis = clean(aid?.["Review synopsis"]);
    if (!synopsis || !mainSurfaceNeedsSynthesis()) return;

    const kind = clean(aid["Aid kind"]);
    const sourceLabel = clean(aid.Source) || "fonte verificata";
    const sourceUrl = safeHttps(aid["Source URL"]);
    const limitation = clean(aid.Note);
    panel.dataset.evidenceMode = "synthesis";
    panel.dataset.synthesisKind = kind || "review_synopsis";
    title.textContent = "Sintesi per lo screening";
    source.textContent = `${aidLabel(kind)} · ${sourceLabel}`;
    text.textContent = synopsis;
    note.textContent = limitation
      ? `Sintesi sostitutiva, non abstract dell’autore. ${limitation}`
      : "Sintesi sostitutiva generata da evidenza verificata; non è l’abstract dell’autore.";

    const article = byId("selected-candidate-article");
    if (sourceUrl && article instanceof HTMLAnchorElement && article.hidden) {
      article.href = sourceUrl;
      article.hidden = false;
    }
  }

  function renderCurrentFromCache() {
    const detail = byId("candidate-detail");
    const candidateId = clean(byId("selected-candidate-id")?.textContent);
    const info = issueInfo();
    const key = issueKey(info);
    activeIssueKey = key;
    if (!detail || detail.hidden || !candidateId || candidateId === "—" || !key) return hidePanel();
    const cached = issueCache.get(key);
    if (!cached || cached.candidateMarker !== candidateId) return hidePanel();
    renderResolution(cached.resolution);
    promoteAidToMainSurface(cached.aid);
  }

  function queueRefresh() {
    if (refreshQueued) return;
    refreshQueued = true;
    queueMicrotask(() => {
      refreshQueued = false;
      renderCurrentFromCache();
    });
  }

  window.fetch = async function curatorAssistedResolutionFetch(input, init) {
    const key = issueKeyFromRequest(input);
    const response = await originalFetch(input, init);
    if (key && response.ok) {
      response.clone().json().then((payload) => {
        const parsed = parseIssuePayload(payload);
        issueCache.set(key, parsed);
        if (activeIssueKey === key || issueKey(issueInfo()) === key) queueRefresh();
      }).catch(() => {});
    }
    return response;
  };

  function initialise() {
    injectStyles();
    ensurePanel();
    const detail = byId("candidate-detail");
    const id = byId("selected-candidate-id");
    const issue = byId("selected-candidate-issue");
    if (!detail || !id || !issue) return;
    const observer = new MutationObserver(queueRefresh);
    observer.observe(detail, { attributes: true, childList: true, characterData: true, subtree: true });
    observer.observe(id, { childList: true, characterData: true, subtree: true });
    observer.observe(issue, { attributes: true, attributeFilter: ["href"] });
    queueRefresh();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialise, { once: true });
  } else {
    initialise();
  }
})();
