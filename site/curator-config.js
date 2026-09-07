"use strict";

// GitHub Pages never receives the curator API origin or reusable credentials.
// The public curator page only links to the isolated, production-verified Worker console.
window.CURATOR_APP_CONFIG = Object.freeze({
  apiBaseUrl: "",
  secureAppUrl: "https://criminal-infiltration-curator.colazeta-research.workers.dev/curate.html",
});

function loadCuratorComponent(src, marker) {
  if (document.querySelector(`script[data-${marker}="true"]`)) return;
  const script = document.createElement("script");
  script.src = src;
  script.async = false;
  script.dataset[marker.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = "true";
  document.head.append(script);
}

// Interceptors load before the reading surface so they can clone and reuse the same
// enrichment / issue responses without issuing duplicate provider or GitHub requests.
loadCuratorComponent("./curator-consensus.js", "curator-consensus");
loadCuratorComponent("./curator-assisted-resolution.js", "curator-assisted-resolution");
loadCuratorComponent("./curator-reading.js", "curator-reading");
loadCuratorComponent("./curator-queue.js", "curator-queue");
loadCuratorComponent("./curator-resolved-link.js", "curator-resolved-link");

// Guided operating layer. The underlying assist remains the reasoning source and
// the governed decision form remains the only submission surface. This layer only
// sequences those two existing capabilities into a classic master-detail workflow.
(() => {
  const GUIDED_VERSION = "CILE-GUIDED-v1";
  const byId = (id) => document.getElementById(id);
  let currentStep = 1;
  let lastCandidateId = "";
  let renderQueued = false;

  function clean(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function node(tag, options = {}) {
    const element = document.createElement(tag);
    if (options.id) element.id = options.id;
    if (options.className) element.className = options.className;
    if (options.text !== undefined) element.textContent = options.text;
    return element;
  }

  function selectedCandidateId() {
    return clean(byId("selected-candidate-id")?.textContent);
  }

  function sourceAssistPanel() {
    return byId("candidate-decision-assist-panel");
  }

  function fieldText(id, fallback = "—") {
    return clean(byId(id)?.textContent) || fallback;
  }

  function proposalReady() {
    const apply = byId("assist-apply");
    return Boolean(apply && !apply.disabled && fieldText("assist-proposal", "") && fieldText("assist-proposal", "") !== "—");
  }

  function identityBlocked() {
    const detail = byId("candidate-detail");
    return detail?.dataset.identityBlocked === "true" || detail?.dataset.scholarIdentityBlocked === "true";
  }

  function criteria() {
    const rows = Array.from(byId("assist-test-body")?.querySelectorAll(":scope > tr") || []);
    return rows.map((row) => {
      const cells = row.querySelectorAll("td");
      return {
        number: clean(cells[0]?.textContent),
        label: clean(cells[1]?.textContent),
        state: clean(cells[2]?.textContent),
        rationale: clean(cells[3]?.textContent),
      };
    }).filter((row) => row.label);
  }

  function isPositiveState(value) {
    return /^(s[iì]|yes|supported|positivo)$/i.test(clean(value));
  }

  function criticalPoint(data) {
    const uncertain = data.criteria.find((row) => !isPositiveState(row.state));
    if (uncertain) {
      return {
        title: `CRITERIO ${uncertain.number || "?"} DA CONTROLLARE · ${uncertain.label.toUpperCase()}`,
        text: uncertain.rationale || "Questo è il primo criterio che l'evidenza disponibile non sostiene in modo pieno.",
        state: uncertain.state || "INCERTO",
      };
    }
    return {
      title: "PUNTO DECISIVO DELLA RACCOMANDAZIONE",
      text: data.decisive,
      state: "COERENTE",
    };
  }

  function assistData() {
    const detail = byId("candidate-detail");
    const abstractPanel = byId("candidate-abstract-panel");
    const evidenceMode = clean(abstractPanel?.dataset.evidenceMode || "").toUpperCase() || "NON RISOLTA";
    const sourcePanel = sourceAssistPanel();
    const recommendation = clean(sourcePanel?.dataset.recommendation || "");
    const confidence = fieldText("assist-confidence");
    const sufficiency = fieldText("assist-sufficiency");
    const data = {
      proposal: fieldText("assist-proposal"),
      confidence,
      sufficiency,
      judgment: fieldText("assist-judgment"),
      decisive: fieldText("assist-decisive"),
      countercase: fieldText("assist-countercase"),
      changeMind: fieldText("assist-change-mind"),
      evidence: fieldText("assist-evidence"),
      substantive: fieldText("assist-substantive-reading"),
      criteria: criteria(),
      recommendation,
      evidenceMode,
      blocked: identityBlocked(),
      proposalReady: proposalReady(),
      sourceStatus: fieldText("assist-status", ""),
      formOpen: detail?.dataset.assistFlow === "review",
    };
    data.critical = criticalPoint(data);
    return data;
  }

  function injectStyles() {
    if (byId("curator-guided-workflow-styles")) return;
    const style = node("style", { id: "curator-guided-workflow-styles" });
    style.textContent = `
      .curator-page #candidate-detail.assist-guided-ready #candidate-decision-assist-panel{display:none!important}
      .curator-page #candidate-detail.assist-guided-ready:not([data-assist-evidence-open="true"]) #candidate-abstract-panel{display:none!important}
      .curator-page #candidate-detail.assist-guided-ready[data-assist-flow="guided"] #decision-form{display:none!important}
      .curator-page #candidate-guided-assist-panel{margin:0;border:0;border-bottom:1px solid #707070;background:#fff;color:#000;font:10px Arial,Helvetica,sans-serif}
      .curator-page .guided-assist-title{display:flex;min-height:22px;align-items:center;justify-content:space-between;gap:8px;padding:3px 6px;border-bottom:1px solid #707070;background:#d4d0c8}
      .curator-page .guided-assist-title strong{font:bold 10px Arial,Helvetica,sans-serif}
      .curator-page .guided-assist-title code{color:#444;font:8px "Courier New",Courier,monospace}
      .curator-page .guided-assist-steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border-bottom:1px solid #707070;background:#eee}
      .curator-page .guided-assist-step{min-height:22px;border:0;border-right:1px solid #999;border-radius:0;padding:3px 5px;background:#e7e7e7;color:#000;font:bold 9px Arial,Helvetica,sans-serif;text-align:left;cursor:pointer;box-shadow:none}
      .curator-page .guided-assist-step:last-child{border-right:0}
      .curator-page .guided-assist-step[data-active="true"]{background:#000080;color:#fff}
      .curator-page .guided-assist-step[data-complete="true"]:not([data-active="true"]){background:#d4d0c8}
      .curator-page .guided-assist-pane{display:none;padding:0;background:#fff}
      .curator-page .guided-assist-pane[data-active="true"]{display:block}
      .curator-page .guided-assist-statusline{display:grid;grid-template-columns:minmax(180px,.8fr) minmax(120px,.45fr) minmax(160px,.65fr);border-bottom:1px solid #999;background:#f7f7f7}
      .curator-page .guided-assist-statusline>div{min-width:0;padding:4px 6px;border-right:1px solid #aaa}
      .curator-page .guided-assist-statusline>div:last-child{border-right:0}
      .curator-page .guided-assist-label{display:block;margin:0 0 1px;color:#555;font:bold 8px Arial,Helvetica,sans-serif}
      .curator-page .guided-assist-value{display:block;overflow:hidden;color:#000;font:bold 11px Arial,Helvetica,sans-serif;text-overflow:ellipsis;white-space:nowrap}
      .curator-page .guided-assist-proposal{color:#000080;font-size:13px}
      .curator-page .guided-assist-section{padding:6px 8px;border-bottom:1px solid #bbb}
      .curator-page .guided-assist-section:last-child{border-bottom:0}
      .curator-page .guided-assist-section h4{margin:0 0 3px;color:#222;font:bold 9px Arial,Helvetica,sans-serif}
      .curator-page .guided-assist-section p{max-width:none;margin:0;color:#000;font:11px/1.4 Arial,Helvetica,sans-serif}
      .curator-page .guided-assist-instruction{background:#ffffdf}
      .curator-page .guided-assist-critical{border-left:5px solid #000080;background:#fff}
      .curator-page .guided-assist-critical[data-state="warning"]{border-left-color:#8b6508;background:#fff9dc}
      .curator-page .guided-assist-critical strong{display:block;margin-bottom:3px;font:bold 10px Arial,Helvetica,sans-serif}
      .curator-page .guided-test-table{width:100%;border-collapse:collapse;table-layout:fixed;background:#fff}
      .curator-page .guided-test-table th,.curator-page .guided-test-table td{border:1px solid #999;padding:3px 4px;vertical-align:top;text-align:left;font:9px/1.25 Arial,Helvetica,sans-serif}
      .curator-page .guided-test-table th{background:#d4d0c8;font-weight:bold}
      .curator-page .guided-test-table th:nth-child(1),.curator-page .guided-test-table td:nth-child(1){width:26px;text-align:center}
      .curator-page .guided-test-table th:nth-child(3),.curator-page .guided-test-table td:nth-child(3){width:68px;font-weight:bold}
      .curator-page .guided-assist-countercase{display:grid;grid-template-columns:1fr 1fr;gap:0;border-top:1px solid #999}
      .curator-page .guided-assist-countercase>div{padding:5px 7px;border-right:1px solid #999}
      .curator-page .guided-assist-countercase>div:last-child{border-right:0}
      .curator-page .guided-assist-countercase h4{margin:0 0 2px;font:bold 8px Arial,Helvetica,sans-serif}
      .curator-page .guided-assist-countercase p{margin:0;font:9px/1.35 Arial,Helvetica,sans-serif}
      .curator-page .guided-action-row{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:4px;padding:4px 6px;border-top:1px solid #707070;background:#d4d0c8}
      .curator-page .guided-action-buttons{display:flex;flex-wrap:wrap;gap:3px}
      .curator-page .guided-action-button{min-height:22px;border:1px solid #555;border-radius:0;padding:2px 8px;background:#e6e6e6;color:#000080;font:bold 9px Arial,Helvetica,sans-serif;box-shadow:none;cursor:pointer}
      .curator-page .guided-action-button[data-primary="true"]{background:#000080;color:#fff;border-color:#000}
      .curator-page .guided-action-button:disabled{color:#777;background:#ddd;cursor:not-allowed}
      .curator-page .guided-action-help{color:#444;font:8px Arial,Helvetica,sans-serif}
      .curator-page .guided-assist-result{margin:0;padding:4px 6px;border-top:1px solid #999;background:#ffffdf;color:#111;font:9px/1.3 Arial,Helvetica,sans-serif}
      .curator-page .guided-assist-footer{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border-top:1px solid #999;background:#eee}
      .curator-page .guided-assist-footer span{min-width:0;overflow:hidden;padding:2px 5px;border-right:1px solid #aaa;color:#333;font:8px "Courier New",Courier,monospace;text-overflow:ellipsis;white-space:nowrap}
      .curator-page .guided-assist-footer span:last-child{border-right:0}
      .curator-page #candidate-detail.assist-guided-ready[data-assist-flow="review"] #decision-form{border-top:2px solid #000080!important}
      @media(max-width:760px){
        .curator-page .guided-assist-statusline{grid-template-columns:1fr}
        .curator-page .guided-assist-statusline>div{border-right:0;border-bottom:1px solid #aaa}
        .curator-page .guided-assist-countercase{grid-template-columns:1fr}
        .curator-page .guided-assist-countercase>div{border-right:0;border-bottom:1px solid #999}
        .curator-page .guided-assist-footer{grid-template-columns:1fr}
      }
    `;
    document.head.append(style);
  }

  function ensurePanel() {
    let panel = byId("candidate-guided-assist-panel");
    if (panel) return panel;
    const detail = byId("candidate-detail");
    const metadata = detail?.querySelector(".candidate-metadata");
    if (!detail || !metadata) return null;

    panel = node("section", { id: "candidate-guided-assist-panel" });
    panel.hidden = true;
    panel.dataset.version = GUIDED_VERSION;

    const title = node("div", { className: "guided-assist-title" });
    title.append(
      node("strong", { text: "ASSISTENTE DI SCREENING" }),
      node("code", { text: GUIDED_VERSION }),
    );

    const steps = node("div", { className: "guided-assist-steps" });
    for (const [step, label] of [[1, "1 · VALUTAZIONE"], [2, "2 · PUNTO CRITICO"], [3, "3 · DECISIONE"]]) {
      const button = node("button", { className: "guided-assist-step", text: label });
      button.type = "button";
      button.dataset.step = String(step);
      button.addEventListener("click", () => setStep(step));
      steps.append(button);
    }

    const pane1 = node("div", { id: "guided-assist-pane-1", className: "guided-assist-pane" });
    const statusline = node("div", { className: "guided-assist-statusline" });
    for (const [label, id, extra] of [
      ["LA MIA PROPOSTA", "guided-proposal", "guided-assist-proposal"],
      ["CONFIDENZA", "guided-confidence", ""],
      ["EVIDENZA SUFFICIENTE", "guided-sufficiency", ""],
    ]) {
      const item = node("div");
      item.append(
        node("span", { className: "guided-assist-label", text: label }),
        node("span", { id, className: `guided-assist-value ${extra}`.trim(), text: "—" }),
      );
      statusline.append(item);
    }
    const judgment = node("div", { className: "guided-assist-section" });
    judgment.append(
      node("h4", { text: "COME LEGGO QUESTO PAPER" }),
      node("p", { id: "guided-judgment", text: "—" }),
    );
    const instruction = node("div", { className: "guided-assist-section guided-assist-instruction" });
    instruction.append(
      node("h4", { text: "COSA TI CHIEDO DI FARE" }),
      node("p", { id: "guided-instruction", text: "Leggi la valutazione; nel passo successivo ti mostro soltanto il punto che merita davvero controllo." }),
    );
    pane1.append(statusline, judgment, instruction);

    const pane2 = node("div", { id: "guided-assist-pane-2", className: "guided-assist-pane" });
    const critical = node("div", { id: "guided-critical", className: "guided-assist-section guided-assist-critical" });
    critical.append(
      node("strong", { id: "guided-critical-title", text: "PUNTO DA CONTROLLARE" }),
      node("p", { id: "guided-critical-text", text: "—" }),
    );
    const testHost = node("div", { className: "guided-assist-section" });
    testHost.append(node("h4", { text: "TEST CILE IN QUATTRO PUNTI" }));
    const table = node("table", { className: "guided-test-table" });
    const thead = document.createElement("thead");
    const head = document.createElement("tr");
    for (const label of ["#", "CRITERIO", "ESITO", "PERCHÉ"]) head.append(node("th", { text: label }));
    thead.append(head);
    const tbody = document.createElement("tbody");
    tbody.id = "guided-test-body";
    table.append(thead, tbody);
    testHost.append(table);
    const counter = node("div", { className: "guided-assist-countercase" });
    const counterA = node("div");
    counterA.append(node("h4", { text: "CONTROARGOMENTO PIÙ FORTE" }), node("p", { id: "guided-countercase", text: "—" }));
    const counterB = node("div");
    counterB.append(node("h4", { text: "COSA MI FAREBBE CAMBIARE IDEA" }), node("p", { id: "guided-change-mind", text: "—" }));
    counter.append(counterA, counterB);
    pane2.append(critical, testHost, counter);

    const pane3 = node("div", { id: "guided-assist-pane-3", className: "guided-assist-pane" });
    const decisionSummary = node("div", { className: "guided-assist-section" });
    decisionSummary.append(
      node("h4", { text: "LA DECISIONE CHE TI PROPONGO" }),
      node("p", { id: "guided-decision-summary", text: "—" }),
    );
    const evidenceSummary = node("div", { className: "guided-assist-section" });
    evidenceSummary.append(
      node("h4", { text: "BASE DI EVIDENZA" }),
      node("p", { id: "guided-evidence", text: "—" }),
    );
    const action = node("div", { className: "guided-action-row" });
    const help = node("span", { className: "guided-action-help", text: "ACCETTA prepara il form; nessuna decisione viene salvata senza la tua conferma." });
    const buttonGroup = node("span", { className: "guided-action-buttons" });
    const showEvidence = node("button", { id: "guided-show-evidence", className: "guided-action-button", text: "MOSTRA EVIDENZA" });
    showEvidence.type = "button";
    showEvidence.addEventListener("click", toggleEvidence);
    const deepen = node("button", { id: "guided-deepen", className: "guided-action-button", text: "APPROFONDISCI" });
    deepen.type = "button";
    deepen.addEventListener("click", deepen);
    const edit = node("button", { id: "guided-edit", className: "guided-action-button", text: "MODIFICA" });
    edit.type = "button";
    edit.addEventListener("click", openFormForEdit);
    const accept = node("button", { id: "guided-accept", className: "guided-action-button", text: "ACCETTA E PREPARA" });
    accept.type = "button";
    accept.dataset.primary = "true";
    accept.addEventListener("click", acceptRecommendation);
    buttonGroup.append(showEvidence, deepen, edit, accept);
    action.append(help, buttonGroup);
    const result = node("p", { id: "guided-result", className: "guided-assist-result", text: "" });
    result.hidden = true;
    pane3.append(decisionSummary, evidenceSummary, action, result);

    const nav = node("div", { className: "guided-action-row" });
    const navHelp = node("span", { id: "guided-nav-help", className: "guided-action-help", text: "PASSO 1 DI 3" });
    const navButtons = node("span", { className: "guided-action-buttons" });
    const back = node("button", { id: "guided-back", className: "guided-action-button", text: "← INDIETRO" });
    back.type = "button";
    back.addEventListener("click", () => setStep(currentStep - 1));
    const next = node("button", { id: "guided-next", className: "guided-action-button", text: "AVANTI →" });
    next.type = "button";
    next.addEventListener("click", () => setStep(currentStep + 1));
    navButtons.append(back, next);
    nav.append(navHelp, navButtons);

    const footer = node("div", { className: "guided-assist-footer" });
    footer.append(
      node("span", { id: "guided-footer-evidence", text: "EVIDENZA: —" }),
      node("span", { id: "guided-footer-identity", text: "IDENTITÀ: —" }),
      node("span", { id: "guided-footer-form", text: "FORM: CHIUSO" }),
    );

    panel.append(title, steps, pane1, pane2, pane3, nav, footer);
    metadata.insertAdjacentElement("afterend", panel);
    return panel;
  }

  function toggleEvidence() {
    const detail = byId("candidate-detail");
    if (!detail) return;
    const next = detail.dataset.assistEvidenceOpen !== "true";
    detail.dataset.assistEvidenceOpen = String(next);
    const button = byId("guided-show-evidence");
    if (button) button.textContent = next ? "NASCONDI EVIDENZA" : "MOSTRA EVIDENZA";
    if (next) byId("candidate-abstract-panel")?.scrollIntoView({ behavior: "auto", block: "nearest" });
    updateFooter(assistData());
  }

  function setStep(step) {
    const bounded = Math.min(3, Math.max(1, Number(step) || 1));
    currentStep = bounded;
    for (const button of document.querySelectorAll("#candidate-guided-assist-panel .guided-assist-step")) {
      const value = Number(button.dataset.step);
      button.dataset.active = String(value === currentStep);
      button.dataset.complete = String(value < currentStep);
    }
    for (let index = 1; index <= 3; index += 1) {
      const pane = byId(`guided-assist-pane-${index}`);
      if (pane) pane.dataset.active = String(index === currentStep);
    }
    const back = byId("guided-back");
    const next = byId("guided-next");
    if (back) back.disabled = currentStep === 1;
    if (next) {
      next.disabled = currentStep === 3;
      next.hidden = currentStep === 3;
    }
    const help = byId("guided-nav-help");
    if (help) help.textContent = `PASSO ${currentStep} DI 3`;
  }

  function renderCriteria(data) {
    const body = byId("guided-test-body");
    if (!body) return;
    body.replaceChildren();
    if (!data.criteria.length) {
      const row = document.createElement("tr");
      const cell = node("td", { text: "Il four-part test non è ancora disponibile per questo record." });
      cell.colSpan = 4;
      row.append(cell);
      body.append(row);
      return;
    }
    for (const item of data.criteria) {
      const row = document.createElement("tr");
      for (const value of [item.number, item.label, item.state, item.rationale]) row.append(node("td", { text: value || "—" }));
      body.append(row);
    }
  }

  function instructionText(data) {
    if (data.blocked) return "Prima della decisione devi soltanto risolvere il problema di identità indicato nella scheda. Non ti chiedo di fare screening finché quel gate resta aperto.";
    if (/^NO$/i.test(data.sufficiency)) return "Non ti chiedo di decidere al buio. Vai al passo 2: ti mostro cosa manca; poi puoi chiedermi APPROFONDISCI con un solo comando.";
    if (/ALTA|HIGH/i.test(data.confidence)) return "Non serve rileggere tutto da zero. Nel passo 2 controlla il punto decisivo e il controargomento; se ti convincono, accetta la proposta.";
    return "La proposta è utilizzabile ma non forte. Nel passo 2 controlla il criterio incerto e il controargomento prima di decidere.";
  }

  function decisionSummary(data) {
    if (data.blocked) return `Non propongo ancora un'approvazione operativa: l'identità del record deve essere risolta prima dello screening.`;
    if (!data.proposalReady) return `La mia posizione attuale è ${data.proposal}. Non posso ancora trasformarla in campi di decisione: l'evidenza o i campi governati sono incompleti.`;
    return `Propongo ${data.proposal}, con confidenza ${data.confidence}. Se condividi il ragionamento, ACCETTA E PREPARA compilerà il form governato; tu vedrai e confermerai ogni campo prima del salvataggio.`;
  }

  function updateFooter(data) {
    const detail = byId("candidate-detail");
    const evidence = byId("guided-footer-evidence");
    const identity = byId("guided-footer-identity");
    const form = byId("guided-footer-form");
    if (evidence) evidence.textContent = `EVIDENZA: ${data.evidenceMode}`;
    if (identity) identity.textContent = `IDENTITÀ: ${data.blocked ? "GATE APERTO" : "OK"}`;
    if (form) form.textContent = `FORM: ${detail?.dataset.assistFlow === "review" ? "APERTO" : "CHIUSO"}`;
  }

  function render() {
    const panel = ensurePanel();
    const detail = byId("candidate-detail");
    const candidateId = selectedCandidateId();
    const source = sourceAssistPanel();
    if (!panel || !detail || detail.hidden || !candidateId || candidateId === "—" || !source || source.hidden) {
      if (panel) panel.hidden = true;
      return;
    }

    const candidateChanged = candidateId !== lastCandidateId;
    lastCandidateId = candidateId;
    if (candidateChanged) {
      currentStep = 1;
      detail.dataset.assistFlow = "guided";
      detail.dataset.assistEvidenceOpen = "false";
      const result = byId("guided-result");
      if (result) {
        result.hidden = true;
        result.textContent = "";
      }
    }

    const data = assistData();
    detail.classList.add("assist-guided-ready");
    panel.hidden = false;
    panel.dataset.recommendation = data.recommendation;
    panel.dataset.confidence = data.confidence;

    byId("guided-proposal").textContent = data.proposal;
    byId("guided-confidence").textContent = data.confidence;
    byId("guided-sufficiency").textContent = data.sufficiency;
    byId("guided-judgment").textContent = data.judgment;
    byId("guided-instruction").textContent = instructionText(data);
    byId("guided-critical-title").textContent = data.critical.title;
    byId("guided-critical-text").textContent = data.critical.text;
    const critical = byId("guided-critical");
    if (critical) critical.dataset.state = isPositiveState(data.critical.state) || data.critical.state === "COERENTE" ? "ok" : "warning";
    byId("guided-countercase").textContent = data.countercase;
    byId("guided-change-mind").textContent = data.changeMind;
    byId("guided-decision-summary").textContent = decisionSummary(data);
    byId("guided-evidence").textContent = data.evidence;
    renderCriteria(data);

    const accept = byId("guided-accept");
    if (accept) {
      accept.disabled = data.blocked || !data.proposalReady;
      accept.title = data.blocked
        ? "Risolvi prima l'identità del record."
        : data.proposalReady
          ? "Prepara il form governato senza salvarlo."
          : "La proposta non è ancora trasformabile in una decisione.";
    }
    const evidenceButton = byId("guided-show-evidence");
    if (evidenceButton) evidenceButton.textContent = detail.dataset.assistEvidenceOpen === "true" ? "NASCONDI EVIDENZA" : "MOSTRA EVIDENZA";

    updateFooter(data);
    setStep(currentStep);
  }

  function showResult(text) {
    const result = byId("guided-result");
    if (!result) return;
    result.textContent = text;
    result.hidden = false;
  }

  function acceptRecommendation() {
    const data = assistData();
    if (data.blocked) {
      showResult("NON POSSO PREPARARE LA DECISIONE: risolvi prima il gate di identità.");
      return;
    }
    const sourceApply = byId("assist-apply");
    if (!sourceApply || sourceApply.disabled) {
      showResult("LA PROPOSTA NON È ANCORA APPLICABILE: completa l'evidenza o i campi governati indicati dall'assistente.");
      return;
    }
    sourceApply.click();
    const detail = byId("candidate-detail");
    if (detail) detail.dataset.assistFlow = "review";
    const sourceStatus = fieldText("assist-status", "Proposta preparata nel form.");
    showResult(`${sourceStatus} Ora controlla il form sotto: la conferma finale resta tua.`);
    updateFooter(assistData());
    queueMicrotask(() => byId("decision-form")?.scrollIntoView({ behavior: "auto", block: "start" }));
  }

  function openFormForEdit() {
    const detail = byId("candidate-detail");
    if (!detail) return;
    detail.dataset.assistFlow = "review";
    showResult("MODIFICA MANUALE: il form è aperto senza applicare la proposta dell'assistente.");
    updateFooter(assistData());
    queueMicrotask(() => byId("decision-form")?.scrollIntoView({ behavior: "auto", block: "start" }));
  }

  function deepen() {
    const sourceDeepen = byId("assist-deepen");
    if (!sourceDeepen || sourceDeepen.disabled) {
      showResult("APPROFONDIMENTO NON DISPONIBILE IN QUESTA SESSIONE.");
      return;
    }
    setStep(2);
    showResult("APPROFONDIMENTO IN CORSO: cerco evidenza aggiuntiva sul paper aperto. La decisione non viene modificata automaticamente.");
    sourceDeepen.click();
  }

  function queueRender() {
    if (renderQueued) return;
    renderQueued = true;
    queueMicrotask(() => {
      renderQueued = false;
      render();
    });
  }

  function observe() {
    const detail = byId("candidate-detail");
    if (!detail) return;
    const observer = new MutationObserver(queueRender);
    observer.observe(detail, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: [
        "hidden",
        "data-recommendation",
        "data-confidence",
        "data-identity-blocked",
        "data-identity-state",
        "data-scholar-identity-blocked",
        "data-scholar-identity-state",
        "data-evidence-mode",
        "disabled",
      ],
    });
  }

  function initialise() {
    injectStyles();
    ensurePanel();
    observe();
    queueRender();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialise, { once: true });
  else initialise();
})();
