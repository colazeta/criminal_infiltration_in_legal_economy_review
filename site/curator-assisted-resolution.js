"use strict";

(() => {
  const SESSION_KEY = "criminal-infiltration-curator-session";
  const ASSIST_VERSION = "CILE-ASSIST-v2-abstention";
  const config = window.CURATOR_APP_CONFIG || {};
  const apiBaseUrl = String(config.apiBaseUrl || "").replace(/\/$/, "");
  const byId = (id) => document.getElementById(id);

  let currentContext = null;
  let currentCandidateId = "";
  let currentRecommendation = null;
  let recomputeQueued = false;

  function clean(value) {
    return String(value || "")
      .replace(/^`|`$/g, "")
      .replace(/^<|>$/g, "")
      .replace(/\*\*/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function normalise(value) {
    return clean(value)
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  }

  function safeHttps(value) {
    try {
      const url = new URL(clean(value));
      return url.protocol === "https:" ? url.toString() : "";
    } catch {
      return "";
    }
  }

  function node(tag, options = {}) {
    const element = document.createElement(tag);
    if (options.id) element.id = options.id;
    if (options.className) element.className = options.className;
    if (options.text !== undefined) element.textContent = options.text;
    return element;
  }

  function cell(tag, text, options = {}) {
    const element = node(tag, { text });
    if (options.colSpan) element.colSpan = options.colSpan;
    if (options.scope) element.scope = options.scope;
    return element;
  }

  function selectedCandidateId() {
    return clean(byId("selected-candidate-id")?.textContent);
  }

  function selectedIssueNumber() {
    const href = byId("selected-candidate-issue")?.href || "";
    const match = href.match(/\/issues\/(\d+)(?:[/?#]|$)/);
    return match ? Number(match[1]) : null;
  }

  function sessionToken() {
    try {
      return sessionStorage.getItem(SESSION_KEY) || "";
    } catch {
      return "";
    }
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

  // Existing assisted-resolution panel remains a hidden technical surface. The
  // operating interface uses the separate decision-assist panel below.
  function ensureResolutionPanel() {
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

  function hideResolutionPanel() {
    const panel = ensureResolutionPanel();
    if (!panel) return;
    panel.hidden = true;
    delete panel.dataset.state;
  }

  function renderResolution(payload) {
    const panel = ensureResolutionPanel();
    if (!panel || !payload) return hideResolutionPanel();
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
      source.textContent = `Apri ${payload["Best assisted source"] || "fonte assistita"} ↗`;
    } else {
      source.hidden = true;
      source.removeAttribute("href");
    }
    document.dispatchEvent(new CustomEvent("curator:assisted-resolution", {
      detail: { resolutionClass, standaloneAbstractStatus: payload["Standalone abstract status"] || "" },
    }));
  }

  function ensureAssistPanel() {
    let panel = byId("candidate-decision-assist-panel");
    if (panel) return panel;
    const form = byId("decision-form");
    const detail = byId("candidate-detail");
    if (!detail) return null;

    panel = node("section", { id: "candidate-decision-assist-panel", className: "decision-form" });
    panel.hidden = true;
    panel.dataset.assistVersion = ASSIST_VERSION;

    const heading = node("div", { className: "decision-form-heading" });
    heading.append(
      node("strong", { text: "ASSISTENZA SCREENING" }),
      node("code", { id: "assist-version", text: ASSIST_VERSION }),
    );

    const summaryTable = document.createElement("table");
    summaryTable.id = "assist-summary-table";
    summaryTable.border = "1";
    summaryTable.cellPadding = "4";
    summaryTable.cellSpacing = "0";
    summaryTable.width = "100%";
    const summaryBody = document.createElement("tbody");

    const statusRow = document.createElement("tr");
    statusRow.append(
      cell("th", "PROPOSTA", { scope: "row" }),
      cell("td", "—"),
      cell("th", "CONFIDENZA", { scope: "row" }),
      cell("td", "—"),
      cell("th", "EVIDENZA SUFFICIENTE", { scope: "row" }),
      cell("td", "—"),
    );
    statusRow.children[1].id = "assist-proposal";
    statusRow.children[3].id = "assist-confidence";
    statusRow.children[5].id = "assist-sufficiency";

    const judgmentHead = document.createElement("tr");
    judgmentHead.append(cell("th", "GIUDIZIO DELL’ASSISTENTE", { colSpan: 6 }));
    const judgmentRow = document.createElement("tr");
    judgmentRow.append(cell("td", "—", { colSpan: 6 }));
    judgmentRow.firstElementChild.id = "assist-judgment";

    const decisiveHead = document.createElement("tr");
    decisiveHead.append(cell("th", "MOTIVO DECISIVO", { colSpan: 6 }));
    const decisiveRow = document.createElement("tr");
    decisiveRow.append(cell("td", "—", { colSpan: 6 }));
    decisiveRow.firstElementChild.id = "assist-decisive";

    summaryBody.append(statusRow, judgmentHead, judgmentRow, decisiveHead, decisiveRow);
    summaryTable.append(summaryBody);

    const details = document.createElement("details");
    details.id = "assist-details";
    const detailsSummary = document.createElement("summary");
    detailsSummary.textContent = "VEDI TEST, CONTROARGOMENTO ED EVIDENZA";
    details.append(detailsSummary);

    const testTable = document.createElement("table");
    testTable.id = "assist-four-part-test";
    testTable.border = "1";
    testTable.cellPadding = "3";
    testTable.cellSpacing = "0";
    testTable.width = "100%";
    const testHead = document.createElement("thead");
    const headRow = document.createElement("tr");
    for (const label of ["#", "CRITERIO CILE", "ESITO", "RAZIONALE"]) headRow.append(cell("th", label));
    testHead.append(headRow);
    const testBody = document.createElement("tbody");
    testBody.id = "assist-test-body";
    testTable.append(testHead, testBody);

    const reasoningTable = document.createElement("table");
    reasoningTable.border = "1";
    reasoningTable.cellPadding = "3";
    reasoningTable.cellSpacing = "0";
    reasoningTable.width = "100%";
    const reasoningBody = document.createElement("tbody");
    for (const [label, id] of [
      ["ALTERNATIVA PIÙ PLAUSIBILE", "assist-countercase"],
      ["COSA MI FAREBBE CAMBIARE IDEA", "assist-change-mind"],
      ["EVIDENZA UTILIZZATA", "assist-evidence"],
      ["LETTURA SOSTANZIALE", "assist-substantive-reading"],
    ]) {
      const head = document.createElement("tr");
      head.append(cell("th", label));
      const row = document.createElement("tr");
      row.append(cell("td", "—"));
      row.firstElementChild.id = id;
      reasoningBody.append(head, row);
    }
    reasoningTable.append(reasoningBody);
    details.append(testTable, reasoningTable);

    const status = node("div", { id: "assist-status", className: "decision-result" });
    status.hidden = true;

    const actions = node("div", { className: "decision-submit-row" });
    const boundary = node("span", { text: "PROPOSTA NON CANONICA · LA DECISIONE RESTA UMANA" });
    const buttons = node("span");
    const deepen = node("button", { id: "assist-deepen", className: "classic-button", text: "APPROFONDISCI" });
    deepen.type = "button";
    const apply = node("button", { id: "assist-apply", className: "classic-button", text: "APPLICA AL FORM" });
    apply.type = "button";
    buttons.append(deepen, document.createTextNode(" "), apply);
    actions.append(boundary, buttons);

    panel.append(heading, summaryTable, details, status, actions);
    if (form) form.insertAdjacentElement("beforebegin", panel);
    else detail.append(panel);

    deepen.addEventListener("click", deepenEvidence);
    apply.addEventListener("click", applyRecommendation);
    return panel;
  }

  function evidenceSnapshot() {
    const panel = byId("candidate-abstract-panel");
    const evidenceMode = panel?.dataset.evidenceMode || "";
    const text = clean(byId("candidate-abstract-text")?.textContent);
    const source = clean(byId("candidate-abstract-source")?.textContent);
    const note = clean(byId("candidate-abstract-note")?.textContent);
    const aid = currentContext?.reviewSupport?.aid || null;
    const guidance = currentContext?.reviewSupport?.guidance || null;
    const synopsis = clean(aid?.["Review synopsis"]);
    const substantiveText = evidenceMode === "abstract" ? text : ""; // Generated notes cannot corroborate themselves.
    return {
      evidenceMode,
      text,
      source,
      note,
      aid,
      guidance,
      synopsis,
      substantiveText: clean(substantiveText),
      normalised: normalise(substantiveText),
    };
  }

  function criterion(number, label, state, rationale) {
    return { number, label, state, rationale };
  }

  function recommendationLabel(kind) {
    const labels = {
      core: "CORE",
      contextual: "CONTEXTUAL",
      full_text: "SERVE ALTRO TESTO",
      not_eligible: "NON ELEGGIBILE",
      not_academic: "NON ACCADEMICO / RUMORE",
      identity: "RISOLVERE IDENTITÀ",
    };
    return labels[kind] || "VALUTAZIONE APERTA";
  }

  function confidenceLabel(value) {
    return { high: "ALTA", medium: "MEDIA", low: "BASSA" }[value] || "—";
  }

  function buildRecommendation() {
    const snapshot = evidenceSnapshot();
    const detail = byId("candidate-detail");
    const blocked = detail?.dataset.identityBlocked === "true" || detail?.dataset.scholarIdentityBlocked === "true"
      || detail?.dataset.identityState === "duplicate_risk" || detail?.dataset.scholarIdentityState === "manifestation_ambiguity";
    const criteria = [
      "Attore/interesse criminale identificabile",
      "Entità o contesto dell’economia legale",
      "Relazione sostenuta: accesso/partecipazione/influenza/controllo/embeddedness",
      "Analisi sostanziale della relazione",
    ].map((label, index) => criterion(index + 1, label, "INCERTO",
      "Occorre un giudizio sul passo della fonte. La presenza di parole chiave, anche in una negazione, non dimostra il criterio."));
    const base = {
      candidateId: selectedCandidateId(), kind: "full_text", decision: "maybe_full_text_needed",
      confidence: "low", sufficient: false, criteria,
      exclusionReason: "", topic: "", secondaryCollection: "",
      screeningStage: snapshot.evidenceMode === "abstract" ? "title_abstract" : "",
      judgment: "Valutazione aperta. Questo controllo preparatorio non attribuisce eleggibilità da parole chiave o note di triage.",
      decisive: "Documentare separatamente i quattro criteri con passi identificabili della fonte e una valutazione umana.",
      countercase: "Un segnale lessicale può essere negato, incidentale o riferito a un altro lavoro. Anche rumore di retrieval non significa fonte non accademica.",
      changeMind: "Lettura attribuita di una fonte verificata, con motivazione e locator per ciascun criterio.",
      evidenceBasis: evidenceBasis(snapshot),
      substantiveReading: substantiveReading(snapshot, "", ""), formRationale: "",
    };
    if (blocked) return { ...base, kind: "identity", decision: "",
      decisive: "Prima viene l’identity gate: verificare opera e versione." };
    if (snapshot.evidenceMode === "metadata") base.decisive = "Il codebook vieta di decidere eligibility dal titolo. Recuperare la fonte.";
    return base;
  }

  function evidenceBasis(snapshot) {
    const kind = clean(snapshot.aid?.["Aid kind"]);
    const source = clean(snapshot.aid?.Source);
    if (snapshot.evidenceMode === "abstract") {
      return `Abstract originale mostrato nella console${snapshot.source ? ` · ${snapshot.source}` : ""}.`;
    }
    if (snapshot.evidenceMode === "synthesis") {
      return `Sintesi per lo screening${source ? ` · ${source}` : ""}${kind ? ` · ${kind}` : ""}.`;
    }
    if (snapshot.synopsis) {
      return `Review synopsis materializzata${source ? ` · ${source}` : ""}${kind ? ` · ${kind}` : ""}.`;
    }
    return "Metadati materializzati soltanto; evidenza sostanziale non ancora sufficiente.";
  }

  function substantiveReading(snapshot, focus, approach) {
    const parts = [];
    if (snapshot.synopsis) parts.push(`Sintesi del contributo: ${snapshot.synopsis}`);
    else if (snapshot.evidenceMode === "abstract" && snapshot.text) parts.push(`Abstract: ${snapshot.text}`);
    if (focus) parts.push(`Focus specifico per la review: ${focus}`);
    if (approach) parts.push(`Verifica consigliata: ${approach}`);
    return parts.join(" ") || "Lettura sostanziale non ancora disponibile oltre i metadati.";
  }

  function renderRecommendation(recommendation) {
    const panel = ensureAssistPanel();
    if (!panel || !recommendation) return;
    currentRecommendation = recommendation;
    panel.hidden = false;
    panel.dataset.recommendation = recommendation.kind;
    panel.dataset.confidence = recommendation.confidence;
    byId("assist-proposal").textContent = recommendationLabel(recommendation.kind);
    byId("assist-confidence").textContent = confidenceLabel(recommendation.confidence);
    byId("assist-sufficiency").textContent = recommendation.sufficient ? "SÌ" : "NO";
    byId("assist-judgment").textContent = recommendation.judgment;
    byId("assist-decisive").textContent = recommendation.decisive;
    byId("assist-countercase").textContent = recommendation.countercase;
    byId("assist-change-mind").textContent = recommendation.changeMind;
    byId("assist-evidence").textContent = recommendation.evidenceBasis;
    byId("assist-substantive-reading").textContent = recommendation.substantiveReading;

    const body = byId("assist-test-body");
    body.replaceChildren();
    for (const item of recommendation.criteria) {
      const row = document.createElement("tr");
      row.append(
        cell("td", String(item.number)),
        cell("td", item.label),
        cell("td", item.state),
        cell("td", item.rationale),
      );
      body.append(row);
    }

    const apply = byId("assist-apply");
    apply.disabled = !recommendation.decision;
    apply.title = recommendation.decision
      ? "Precompila il modulo governato. Non invia né conferma la decisione."
      : "La raccomandazione non può ancora essere trasformata in una decisione.";
  }

  function queueRecompute() {
    if (recomputeQueued) return;
    recomputeQueued = true;
    queueMicrotask(() => {
      recomputeQueued = false;
      const id = selectedCandidateId();
      const detail = byId("candidate-detail");
      if (!id || id === "—" || !detail || detail.hidden) {
        const panel = ensureAssistPanel();
        if (panel) panel.hidden = true;
        return;
      }
      if (currentCandidateId && currentCandidateId !== id) currentContext = null;
      currentCandidateId = id;
      renderRecommendation(buildRecommendation());
    });
  }

  function setField(id, value) {
    const control = byId(id);
    if (!control || value === undefined || value === null) return;
    control.value = value;
    control.dispatchEvent(new Event("input", { bubbles: true }));
    control.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function applyRecommendation() {
    const recommendation = currentRecommendation;
    if (!recommendation?.decision) return;
    const snapshot = evidenceSnapshot();
    const stage = recommendation.screeningStage || screeningStage(snapshot);
    if (stage) setField("screening-stage", stage);
    setField("decision", recommendation.decision);
    setField("confidence", recommendation.confidence);
    if (recommendation.exclusionReason) setField("exclusion-reason", recommendation.exclusionReason);
    if (recommendation.topic) setField("topic-code", recommendation.topic);
    if (recommendation.secondaryCollection) setField("secondary-collection", recommendation.secondaryCollection);
    setField("evidence-basis", recommendation.evidenceBasis);
    const rationale = `${recommendation.judgment} Motivo decisivo: ${recommendation.decisive}`;
    setField("decision-rationale", rationale.slice(0, 2000));

    const status = byId("assist-status");
    const missing = [];
    if (!stage) missing.push("stage");
    if ((recommendation.decision === "eligible_core" || recommendation.decision === "eligible_contextual") && !recommendation.topic) missing.push("tema governato");
    if (status) {
      status.hidden = false;
      status.textContent = missing.length
        ? `Proposta applicata. Completa manualmente: ${missing.join(", ")}. La conferma resta intenzionalmente non selezionata.`
        : "Proposta applicata al modulo. Controlla i campi, conferma esplicitamente e salva soltanto se condividi la valutazione.";
    }
    const confirmation = byId("explicit-confirmation");
    if (confirmation) confirmation.checked = false;
    byId("decision-form")?.scrollIntoView({ behavior: "auto", block: "start" });
  }

  async function deepenEvidence() {
    const status = byId("assist-status");
    const button = byId("assist-deepen");
    const candidateId = selectedCandidateId();
    const issueNumber = selectedIssueNumber();
    const title = clean(byId("selected-candidate-title")?.textContent);
    const doi = clean(byId("selected-candidate-doi")?.textContent);
    const year = clean(byId("selected-candidate-year")?.textContent);
    const token = sessionToken();
    byId("assist-details")?.setAttribute("open", "");

    if (!apiBaseUrl || !token || !candidateId || !issueNumber || !title) {
      if (status) {
        status.hidden = false;
        status.textContent = "Approfondimento automatico non disponibile in questa sessione; usa il link ARTICOLO per la verifica manuale.";
      }
      return;
    }

    button.disabled = true;
    button.textContent = "RICERCA…";
    if (status) {
      status.hidden = false;
      status.textContent = "Cerco evidenza aggiuntiva sul paper aperto. Nessuna decisione viene registrata.";
    }
    try {
      const target = new URL(`${apiBaseUrl}/api/free-web-search`);
      target.searchParams.set("candidate", candidateId);
      target.searchParams.set("issue", String(issueNumber));
      target.searchParams.set("title", title);
      if (doi && doi !== "Non registrato") target.searchParams.set("doi", doi);
      if (year && year !== "Non registrato") target.searchParams.set("year", year);
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort("assist_timeout"), 12000);
      const response = await fetch(target, {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      });
      clearTimeout(timer);
      const payload = response.ok ? await response.json() : null;
      if (clean(payload?.abstract)) {
        const panel = byId("candidate-abstract-panel");
        const abstractTitle = byId("candidate-abstract-title");
        const abstractText = byId("candidate-abstract-text");
        const abstractSource = byId("candidate-abstract-source");
        const abstractNote = byId("candidate-abstract-note");
        if (panel) panel.dataset.evidenceMode = "abstract";
        if (abstractTitle) abstractTitle.textContent = "Abstract";
        if (abstractText) abstractText.textContent = clean(payload.abstract);
        if (abstractSource) abstractSource.textContent = payload.abstractSource || payload.provider || "Fonte verificata";
        if (abstractNote) abstractNote.textContent = "Abstract recuperato su richiesta del curatore; non persistito nel corpus pubblico.";
        if (payload.articleUrl) {
          const article = byId("selected-candidate-article");
          const safe = safeHttps(payload.articleUrl);
          if (article && safe) {
            article.href = safe;
            article.hidden = false;
          }
        }
        if (status) status.textContent = "Evidenza aggiuntiva recuperata. Ho ricalcolato la raccomandazione sul nuovo abstract.";
        queueRecompute();
      } else if (status) {
        status.textContent = "La ricerca aggiuntiva non ha restituito un abstract affidabile. Mantengo la raccomandazione sulla migliore evidenza già disponibile.";
      }
    } catch {
      if (status) status.textContent = "Approfondimento interrotto o non disponibile. Mantengo la raccomandazione sulla migliore evidenza già disponibile.";
    } finally {
      button.disabled = false;
      button.textContent = "APPROFONDISCI";
    }
  }

  function consumeCandidateContext(event) {
    const candidateId = clean(event?.detail?.candidateId);
    const selected = selectedCandidateId();
    if (!candidateId || candidateId !== selected) return;
    currentCandidateId = candidateId;
    currentContext = event?.detail?.context || null;
    renderResolution(currentContext?.assistedResolution || null);
    queueRecompute();
  }

  function initialise() {
    ensureResolutionPanel();
    ensureAssistPanel();
    document.addEventListener("curator:candidate-context", consumeCandidateContext);

    const id = byId("selected-candidate-id");
    const detail = byId("candidate-detail");
    const abstractPanel = byId("candidate-abstract-panel") || detail;
    if (id) {
      const idObserver = new MutationObserver(() => {
        currentContext = null;
        hideResolutionPanel();
        queueRecompute();
      });
      idObserver.observe(id, { childList: true, characterData: true, subtree: true });
    }
    if (detail) {
      const detailObserver = new MutationObserver(queueRecompute);
      detailObserver.observe(detail, { attributes: true, attributeFilter: ["hidden", "data-identity-blocked", "data-identity-state", "data-scholar-identity-blocked", "data-scholar-identity-state"] });
    }
    if (abstractPanel) {
      const evidenceObserver = new MutationObserver(queueRecompute);
      evidenceObserver.observe(abstractPanel, { childList: true, characterData: true, subtree: true, attributes: true, attributeFilter: ["data-evidence-mode"] });
    }
    queueRecompute();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialise, { once: true });
  else initialise();
})();
