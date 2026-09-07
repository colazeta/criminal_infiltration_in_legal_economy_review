"use strict";

(() => {
  const SESSION_KEY = "criminal-infiltration-curator-session";
  const ASSIST_VERSION = "CILE-ASSIST-v1";
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

  const PATTERNS = Object.freeze({
    criminal: /\b(mafia|mafias|mafia-type|camorra|cosa nostra|ndrangheta|organized crime|organised crime|criminal organi[sz]ation|criminal group|criminal network|criminal firms?|mafia-related|mafia affiliated)\b/i,
    legalEconomy: /\b(firms?|companies|company|business(?:es)?|enterprises?|public procurement|procurement|contracts?|markets?|sectors?|industr(?:y|ies)|corporate|ownership|shareholders?|legitimate (?:business|industry|economy)|legal economy|real estate|construction|waste|hospitality|assets?|professions?)\b/i,
    relation: /\b(infiltrat\w*|influence\w*|control\w*|ownership|participat\w*|embedded\w*|interlock\w*|penetrat\w*|takeover|entry into|criminal-linked|linked to organi[sz]ed crime|mafia-related firms?|criminal firms?)\b/i,
    sustained: /\b(sustained|durable|long[- ]term|stable|structural|systematic|embedded\w*|control\w*|ownership|interlock\w*)\b/i,
    analytical: /\b(analy[sz]\w*|examin\w*|stud(?:y|ies|ied)|estimat\w*|evaluat\w*|test\w*|investigat\w*|assess\w*|empirical|evidence|data|model\w*|case analysis|network\w*|classifier|effect\w*|impact\w*|determinant\w*|dynamics)\b/i,
    contextual: /\b(concept\w*|theor\w*|framework|method\w*|risk assessment|indicator\w*|detection|screening|typolog\w*|definition|measurement|beneficial ownership)\b/i,
    adjacent: /\b(money laundering|laundering|shell compan\w*|corruption|bribery|violence|drug trafficking|illicit capital|tax evasion|fraud|professional facilitation)\b/i,
    explicitNegative: /\b(outside (?:the )?scope|not (?:an )?infiltration|no infiltration relation|does not (?:analyse|analyze|examine)|mention only|adjacent phenomenon|no criminal actor|no legal[- ]economy link)\b/i,
    conceptualTopic: /\b(concept\w*|theor\w*|definition|defin\w*|framework)\b/i,
    transplantationTopic: /\b(migrat\w*|transplant\w*|relocat\w*|territorial expansion|new territor\w*|establish\w* in new)\b/i,
  });

  function signal(text, pattern) {
    return pattern.test(text);
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
    const substantiveText = evidenceMode === "abstract" || evidenceMode === "synthesis" ? text : synopsis;
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

  function topicSuggestion(text) {
    if (signal(text, PATTERNS.transplantationTopic)) return "criminal_transplantation";
    if (signal(text, PATTERNS.conceptualTopic)) return "conceptual_foundations";
    return "";
  }

  function screeningStage(snapshot) {
    if (snapshot.evidenceMode === "abstract") return "title_abstract";
    if (clean(snapshot.aid?.["Aid kind"]) === "full_text_intro") return "full_text";
    return "";
  }

  function buildRecommendation() {
    const candidateId = selectedCandidateId();
    const detail = byId("candidate-detail");
    const snapshot = evidenceSnapshot();
    const evidence = snapshot.normalised;
    const resolutionClass = clean(currentContext?.assistedResolution?.["Resolution class"]);
    const priorSignal = normalise(snapshot.guidance?.["Prior triage signal"]);
    const focus = clean(snapshot.guidance?.["Candidate-specific focus"]);
    const approach = clean(snapshot.guidance?.approach);
    const identityBlocked = detail?.dataset.identityBlocked === "true" || detail?.dataset.scholarIdentityBlocked === "true";
    const duplicateRisk = detail?.dataset.identityState === "duplicate_risk" || detail?.dataset.scholarIdentityState === "manifestation_ambiguity";

    const criminalYes = Boolean(evidence && signal(evidence, PATTERNS.criminal));
    const legalYes = Boolean(evidence && signal(evidence, PATTERNS.legalEconomy));
    const relationYes = Boolean(evidence && signal(evidence, PATTERNS.relation));
    const sustainedYes = Boolean(evidence && (signal(evidence, PATTERNS.sustained) || /infiltrat\w*/i.test(evidence)));
    const analyticalYes = Boolean(evidence && signal(evidence, PATTERNS.analytical));
    const contextualSignal = Boolean(evidence && signal(evidence, PATTERNS.contextual));
    const adjacentSignal = Boolean(evidence && signal(evidence, PATTERNS.adjacent));
    const explicitNegative = Boolean(evidence && signal(evidence, PATTERNS.explicitNegative));
    const substantiveEvidence = snapshot.evidenceMode === "abstract" || snapshot.evidenceMode === "synthesis" || Boolean(snapshot.synopsis);

    const criteria = [
      criterion(1, "Attore/interesse criminale identificabile", criminalYes ? "SÌ" : substantiveEvidence ? "INCERTO" : "INCERTO",
        criminalYes ? "L’evidenza disponibile identifica esplicitamente un attore o interesse criminale." : "L’evidenza corrente non basta a confermare in modo esplicito un attore/interesse criminale."),
      criterion(2, "Entità o contesto dell’economia legale", legalYes ? "SÌ" : substantiveEvidence ? "INCERTO" : "INCERTO",
        legalYes ? "L’evidenza colloca l’analisi in imprese, mercati, procurement, asset o altri contesti dell’economia legale." : "Il collegamento con un’entità o contesto dell’economia legale non è ancora sufficientemente esplicito."),
      criterion(3, "Relazione sostenuta: accesso/partecipazione/influenza/controllo/embeddedness", relationYes && sustainedYes ? "SÌ" : "INCERTO",
        relationYes && sustainedYes ? "Sono presenti segnali espliciti di infiltrazione, influenza, controllo, ownership o embeddedness, non soltanto prossimità tematica." : "Non considero ancora dimostrata una relazione sostenuta: è il principale punto da verificare nel testo."),
      criterion(4, "Analisi sostanziale della relazione", analyticalYes && relationYes ? "SÌ" : "INCERTO",
        analyticalYes && relationYes ? "La relazione criminalità–economia legale appare oggetto di analisi, studio, stima o valutazione sostanziale." : "Non è ancora chiaro se la relazione sia davvero analizzata o soltanto menzionata/contestualizzata."),
    ];

    const base = {
      candidateId,
      kind: "full_text",
      decision: "maybe_full_text_needed",
      confidence: "medium",
      sufficient: false,
      criteria,
      exclusionReason: "",
      topic: "",
      secondaryCollection: "",
      screeningStage: screeningStage(snapshot),
      judgment: "L’evidenza disponibile non consente ancora di chiudere in modo difendibile il four-part test. Propongo di trattare il record come caso da approfondire, concentrando la verifica sulla relazione sostenuta con l’economia legale e sulla sua centralità analitica.",
      decisive: "Il punto decisivo non è la presenza del tema criminale in sé, ma se accesso, partecipazione, influenza, controllo o embeddedness nell’economia legale costituiscano una relazione sostenuta e realmente analizzata.",
      countercase: "Se il full text dimostra chiaramente tutti e quattro i criteri, il record dovrebbe passare al nucleo core; se invece resta soltanto un fenomeno adiacente o una menzione, l’esito dovrebbe essere di esclusione o, quando giustificato, contestuale.",
      changeMind: "Mi basta evidenza esplicita sulla natura sostenuta della relazione e sul fatto che essa sia un oggetto sostanziale dell’analisi.",
      evidenceBasis: evidenceBasis(snapshot),
      substantiveReading: substantiveReading(snapshot, focus, approach),
      formRationale: "",
    };

    if (identityBlocked || duplicateRisk) {
      return {
        ...base,
        kind: "identity",
        decision: "",
        confidence: "low",
        judgment: "Non formulerei ancora una proposta di screening: l’identità bibliografica o la manifestazione del lavoro è ancora abbastanza incerta da poter contaminare la decisione scientifica.",
        decisive: "Prima viene l’identity gate: devo sapere quale lavoro o manifestazione stiamo effettivamente valutando.",
        countercase: "Una volta risolta l’identità, il four-part test può essere applicato normalmente alla migliore evidenza disponibile.",
        changeMind: "La risoluzione del conflitto bibliografico o del rischio duplicato sblocca immediatamente lo screening.",
      };
    }

    if (resolutionClass === "known_noise") {
      return {
        ...base,
        kind: "not_academic",
        decision: "not_academic",
        confidence: "high",
        sufficient: true,
        exclusionReason: "NOT_ACADEMIC_SOURCE",
        judgment: "Il record è già classificato nel layer di retrieval come rumore noto. Non spenderei ulteriore tempo di screening sostanziale salvo un conflitto con i metadati correnti.",
        decisive: "Il problema qui è il tipo di record, non il four-part infiltration test.",
        countercase: "Riaprirei la valutazione soltanto se emergesse che il record rappresenta in realtà una pubblicazione accademica distinta e correttamente identificata.",
        changeMind: "Una manifestazione accademica verificata dello stesso lavoro renderebbe necessario rimuovere il trattamento da rumore e procedere allo screening normale.",
      };
    }

    if (criminalYes && legalYes && relationYes && sustainedYes && analyticalYes) {
      const strongSource = snapshot.evidenceMode === "abstract" || clean(snapshot.aid?.["Aid kind"]) === "full_text_intro";
      const confidence = strongSource ? "high" : "medium";
      const topic = topicSuggestion(evidence);
      return {
        ...base,
        kind: "core",
        decision: "eligible_core",
        confidence,
        sufficient: true,
        topic,
        judgment: "Ritengo il lavoro un candidato convincente per il nucleo core. L’evidenza disponibile identifica un attore criminale, un contesto dell’economia legale, una relazione di infiltrazione/influenza/controllo sufficientemente sostenuta e un’analisi sostanziale di quella relazione. Non sembra quindi un semplice paper su criminalità organizzata, riciclaggio o corruzione in senso generico.",
        decisive: "Il motivo decisivo è che la relazione tra attore criminale ed economia legale appare essa stessa oggetto dell’analisi, e non un dettaglio incidentale o soltanto un contesto di sfondo.",
        countercase: "L’alternativa più plausibile sarebbe contextual se il full text mostrasse che imprese o mercati sono usati soltanto come contesto/metodo e non come relazione di infiltrazione direttamente analizzata.",
        changeMind: "Cambierei la raccomandazione se il full text riducesse infiltrazione/influenza/controllo a una menzione, a un proxy non validato o a un fenomeno episodico senza relazione sostenuta.",
      };
    }

    if (priorSignal.includes("plausible_contextual") && criminalYes && legalYes && contextualSignal && !(relationYes && sustainedYes && analyticalYes)) {
      const topic = topicSuggestion(evidence);
      return {
        ...base,
        kind: "contextual",
        decision: "eligible_contextual",
        confidence: "medium",
        sufficient: true,
        topic,
        judgment: "La mia lettura preliminare è contestuale: il lavoro sembra offrire un contributo concettuale, metodologico o comparativo utile alla review, ma l’evidenza disponibile non dimostra ancora una relazione diretta e sostenuta di infiltrazione nell’economia legale.",
        decisive: "Il valore per la review sembra risiedere nel modo in cui il lavoro definisce, misura o rende osservabile il fenomeno, più che in evidenza diretta di infiltrazione.",
        countercase: "Potrebbe diventare core se il full text mostra che la relazione sostenuta con imprese, mercati o procurement è direttamente analizzata e non soltanto strumentale al metodo.",
        changeMind: "Un’evidenza diretta di accesso/partecipazione/influenza/controllo analizzata come oggetto centrale mi farebbe alzare la proposta a core; l’assenza di un contributo specifico alla review la farebbe invece scendere fuori perimetro.",
      };
    }

    if (explicitNegative || (adjacentSignal && !relationYes && snapshot.evidenceMode === "abstract")) {
      return {
        ...base,
        kind: "not_eligible",
        decision: "not_eligible",
        confidence: explicitNegative ? "high" : "medium",
        sufficient: true,
        exclusionReason: explicitNegative ? "NO_INFILTRATION_RELATION" : "ADJACENT_PHENOMENON_ONLY",
        secondaryCollection: adjacentSignal ? "broader_aml" : "",
        judgment: "L’evidenza disponibile punta fuori dal perimetro core: il lavoro tratta un fenomeno adiacente o esplicitamente non dimostra la relazione di infiltrazione richiesta dal codebook. Non userei la semplice presenza di criminalità economica come sostituto del requisito di accesso/partecipazione/influenza/controllo sostenuti.",
        decisive: "Manca proprio il nesso di infiltrazione sostenuta nell’economia legale, che è il criterio discriminante della review.",
        countercase: "Riconsidererei il record se una sezione del full text mostrasse che la relazione sostenuta è effettivamente analizzata e non soltanto richiamata.",
        changeMind: "Servirebbe evidenza positiva e specifica del criterio 3 insieme a un’analisi sostanziale del criterio 4.",
      };
    }

    if (!substantiveEvidence || snapshot.evidenceMode === "metadata") {
      return {
        ...base,
        confidence: "high",
        judgment: "Non prenderei una scorciatoia sulla base del solo titolo o dei metadati. La proposta corretta è ottenere evidenza sostanziale prima di classificare il paper.",
        decisive: "Il codebook vieta di decidere eligibility dal titolo: senza abstract, sintesi verificata o full text non abbiamo una base sufficiente.",
        countercase: "Nessuna alternativa scientifica è preferibile finché manca evidenza sostanziale; il primo compito è il retrieval.",
        changeMind: "Una sintesi verificata, un abstract o una sezione di full text sufficiente a valutare i quattro criteri.",
      };
    }

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
