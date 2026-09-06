"use strict";

(() => {
  const SESSION_KEY = "criminal-infiltration-curator-session";
  const config = window.CURATOR_APP_CONFIG || {};
  const apiBaseUrl = String(config.apiBaseUrl || "").replace(/\/$/, "");
  const cache = new Map();
  let activeCandidateId = "";
  let activeController = null;
  let restoringHref = false;

  const byId = (id) => document.getElementById(id);

  function sessionToken() {
    try {
      return sessionStorage.getItem(SESSION_KEY) || "";
    } catch {
      return "";
    }
  }

  function safeHttpsUrl(value) {
    try {
      const url = new URL(String(value || ""));
      return url.protocol === "https:" ? url.toString() : "";
    } catch {
      return "";
    }
  }

  function selectedIssueNumber() {
    const href = byId("selected-candidate-issue")?.href || "";
    const match = href.match(/\/issues\/(\d+)(?:[/?#]|$)/);
    return match ? Number(match[1]) : null;
  }

  function ensureActionContainer() {
    const detail = byId("candidate-detail");
    if (!detail) return null;
    let actions = detail.querySelector(".candidate-heading-actions");
    if (actions) return actions;
    const heading = detail.querySelector(".candidate-detail-heading");
    if (!heading) return null;
    actions = document.createElement("div");
    actions.className = "candidate-heading-actions";
    const audit = byId("selected-candidate-issue");
    if (audit) actions.append(audit);
    heading.append(actions);
    return actions;
  }

  function ensureArticleLink() {
    let link = byId("selected-candidate-article");
    if (link) return link;
    const actions = ensureActionContainer();
    if (!actions) return null;
    link = document.createElement("a");
    link.id = "selected-candidate-article";
    link.className = "candidate-article-action";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Apri articolo ↗";
    link.hidden = true;
    actions.prepend(link);
    return link;
  }

  function ensureStatusNode() {
    let status = byId("selected-candidate-retrieval-status");
    const actions = ensureActionContainer();
    if (!status) {
      status = document.createElement("small");
      status.id = "selected-candidate-retrieval-status";
      status.className = "candidate-retrieval-status";
      status.hidden = true;
    }
    if (actions && !status.isConnected) actions.append(status);
    return status;
  }

  function ensureAccessNode() {
    let status = byId("selected-candidate-access-status");
    const actions = ensureActionContainer();
    if (!status) {
      status = document.createElement("small");
      status.id = "selected-candidate-access-status";
      status.className = "candidate-retrieval-status candidate-access-status";
      status.hidden = true;
    }
    if (actions && !status.isConnected) actions.append(status);
    return status;
  }

  function statusLabel(payload) {
    const labels = {
      open_access_landing: "Copia open access risolta",
      landing_page: "Pagina articolo risolta",
      doi_only: "DOI risolto",
      source_link_only: "Fonte originale risolta",
      unresolved: "Paper non risolto",
    };
    let base;
    if (payload?.resolutionStatus === "full_text") {
      base = payload?.accessStatus === "open"
        ? "Full text pubblico verificato"
        : "Locator full text risolto · accesso non verificato";
    } else {
      base = labels[payload?.resolutionStatus] || "Retrieval verificato";
    }
    return payload?.checkedAt ? `${base} · ${payload.checkedAt}` : base;
  }

  function accessLabel(payload) {
    const labels = {
      open: "OPEN",
      restricted: "RESTRICTED",
      unknown: "ACCESSO DA VERIFICARE",
    };
    return labels[payload?.accessStatus] || "";
  }

  function accessTitle(payload) {
    const detail = String(payload?.accessEvidenceDetail || "").trim();
    const source = String(payload?.accessEvidenceSource || "").trim();
    const checked = String(payload?.accessCheckedAt || "").trim();
    return [source, detail, checked ? `verificato ${checked}` : ""].filter(Boolean).join(" · ");
  }

  function preferredActionLabel(payload) {
    if (payload?.bestUrlKind === "full_text") {
      return payload?.accessStatus === "open"
        ? "Apri full text verificato ↗"
        : "Apri locator full text ↗";
    }
    if (payload?.bestUrlKind === "open_access") return "Apri copia OA ↗";
    return "Apri articolo ↗";
  }

  function clearResolvedLink() {
    const link = ensureArticleLink();
    if (link) {
      delete link.dataset.resolvedUrl;
      delete link.dataset.resolvedKind;
      delete link.dataset.accessStatus;
    }
    const status = ensureStatusNode();
    if (status) {
      status.textContent = "";
      status.hidden = true;
    }
    const access = ensureAccessNode();
    if (access) {
      access.textContent = "";
      access.removeAttribute("title");
      access.hidden = true;
    }
  }

  function applyResolvedLink(payload) {
    const status = ensureStatusNode();
    if (status) {
      status.textContent = statusLabel(payload);
      status.dataset.state = payload?.resolutionStatus || "unknown";
      status.hidden = false;
    }

    const access = ensureAccessNode();
    const label = accessLabel(payload);
    if (access && label) {
      access.textContent = label;
      access.dataset.state = payload.accessStatus;
      const title = accessTitle(payload);
      if (title) access.title = title;
      else access.removeAttribute("title");
      access.hidden = false;
    }

    const link = ensureArticleLink();
    const bestUrl = safeHttpsUrl(payload?.bestUrl);
    if (!link || !bestUrl) return;
    link.dataset.resolvedUrl = bestUrl;
    link.dataset.resolvedKind = payload?.bestUrlKind || "";
    link.dataset.accessStatus = payload?.accessStatus || "";
    restoringHref = true;
    link.href = bestUrl;
    link.textContent = preferredActionLabel(payload);
    link.hidden = false;
    restoringHref = false;
  }

  async function loadRetrieval(candidateId, issueNumber) {
    const key = `${candidateId}|${issueNumber}`;
    if (cache.has(key)) return cache.get(key);
    const token = sessionToken();
    if (!apiBaseUrl || !token) return null;
    const target = new URL(`${apiBaseUrl}/api/retrieval`);
    target.searchParams.set("candidate", candidateId);
    target.searchParams.set("issue", String(issueNumber));
    activeController?.abort();
    activeController = new AbortController();
    const response = await fetch(target, {
      headers: { Authorization: `Bearer ${token}` },
      signal: activeController.signal,
    });
    if (!response.ok) throw new Error("retrieval_record_unavailable");
    const payload = await response.json();
    cache.set(key, payload);
    return payload;
  }

  async function refreshResolvedLink() {
    const candidateId = byId("selected-candidate-id")?.textContent?.trim() || "";
    const detail = byId("candidate-detail");
    if (!candidateId || candidateId === "—" || !detail || detail.hidden) return;
    const issueNumber = selectedIssueNumber();
    if (!issueNumber) return;

    ensureArticleLink();
    ensureStatusNode();
    ensureAccessNode();
    if (candidateId !== activeCandidateId) {
      activeCandidateId = candidateId;
      clearResolvedLink();
    }

    try {
      const payload = await loadRetrieval(candidateId, issueNumber);
      if (candidateId !== activeCandidateId || !payload) return;
      applyResolvedLink(payload);
    } catch (error) {
      if (error?.name === "AbortError") return;
      if (candidateId !== activeCandidateId) return;
      const status = ensureStatusNode();
      if (status) {
        status.textContent = "Retrieval persistente non disponibile";
        status.dataset.state = "unavailable";
        status.hidden = false;
      }
    }
  }

  function preserveResolvedHref(mutations) {
    if (restoringHref) return;
    for (const mutation of mutations) {
      const link = mutation.target;
      if (!(link instanceof HTMLAnchorElement) || link.id !== "selected-candidate-article") continue;
      const resolved = safeHttpsUrl(link.dataset.resolvedUrl);
      if (!resolved || link.href === resolved) continue;
      restoringHref = true;
      link.href = resolved;
      if (link.dataset.resolvedKind === "full_text") {
        link.textContent = link.dataset.accessStatus === "open"
          ? "Apri full text verificato ↗"
          : "Apri locator full text ↗";
      } else if (link.dataset.resolvedKind === "open_access") {
        link.textContent = "Apri copia OA ↗";
      } else {
        link.textContent = "Apri articolo ↗";
      }
      restoringHref = false;
    }
  }

  function initialise() {
    const detail = byId("candidate-detail");
    const id = byId("selected-candidate-id");
    const issue = byId("selected-candidate-issue");
    if (!detail || !id || !issue) return;

    const selectionObserver = new MutationObserver(() => queueMicrotask(refreshResolvedLink));
    selectionObserver.observe(detail, { attributes: true, attributeFilter: ["hidden"] });
    selectionObserver.observe(id, { childList: true, characterData: true, subtree: true });
    selectionObserver.observe(issue, { attributes: true, attributeFilter: ["href"] });

    const actionObserver = new MutationObserver(preserveResolvedHref);
    actionObserver.observe(detail, { attributes: true, attributeFilter: ["href"], subtree: true });
    queueMicrotask(refreshResolvedLink);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialise, { once: true });
  } else {
    initialise();
  }
})();

// Identity-resolution and guided-decision layer. This remains non-decisional:
// it explains the record state and reshapes existing governed controls without
// choosing a scientific outcome on behalf of the curator.
(() => {
  const byId = (id) => document.getElementById(id);
  const PRIMARY_DECISIONS = new Set([
    "eligible_core",
    "eligible_contextual",
    "maybe_full_text_needed",
    "not_eligible",
  ]);
  const EXCEPTION_DECISIONS = new Set(["duplicate", "not_academic", "not_retrievable"]);
  let activeCandidateId = "";
  let currentIdentity = null;

  function normalise(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function isMissing(value) {
    const text = normalise(value).toLowerCase();
    return !text || text === "—" || text === "non registrato" || text === "non registrata" || text === "non registrati";
  }

  function meaningfulNote(value) {
    const text = normalise(value);
    if (!text) return false;
    return !/^(none|no|nessuno|not recorded|non registrato|—)$/i.test(text);
  }

  function provenanceMap() {
    const result = {};
    for (const row of byId("candidate-provenance")?.querySelectorAll(":scope > div") || []) {
      const key = normalise(row.querySelector("dt")?.textContent);
      const value = normalise(row.querySelector("dd")?.textContent);
      if (key) result[key] = value;
    }
    return result;
  }

  function candidateFacts() {
    return {
      candidateId: normalise(byId("selected-candidate-id")?.textContent),
      authors: normalise(byId("selected-candidate-authors")?.textContent),
      year: normalise(byId("selected-candidate-year")?.textContent),
      venue: normalise(byId("selected-candidate-venue")?.textContent),
      doi: normalise(byId("selected-candidate-doi")?.textContent),
      stage: normalise(byId("selected-candidate-stage")?.textContent),
      provenance: provenanceMap(),
      resolutionStatus: normalise(byId("selected-candidate-retrieval-status")?.dataset.state),
      accessStatus: normalise(byId("selected-candidate-access-status")?.dataset.state),
    };
  }

  function identityAssessment() {
    const facts = candidateFacts();
    const provenance = facts.provenance;
    const verification = normalise(provenance["Verification status"]).toLowerCase();
    const duplicateNote = normalise(provenance["Possible duplicate note"]);
    const metadataConflict = normalise(provenance["Metadata conflict"]);
    const requiredAction = normalise(provenance["Required human action"] || provenance["Pilot note"]);
    const missing = [];
    if (isMissing(facts.authors)) missing.push("autori");
    if (isMissing(facts.year)) missing.push("anno");
    if (isMissing(facts.venue)) missing.push("sede editoriale");
    const doiPresent = !isMissing(facts.doi);
    const duplicateRisk = meaningfulNote(duplicateNote);
    const conflictPresent = meaningfulNote(metadataConflict);
    const manifestationConflict = conflictPresent && /manifest|version|preprint|working paper|accepted|future|publication|published|reprint|date|doi/i.test(metadataConflict);
    const metadataStage = /metadata|metadat/i.test(facts.stage);
    const partialVerification = verification.includes("partial") || verification.includes("unresolved");
    const positiveVerification = verification.includes("verified");
    const retrievalResolved = facts.resolutionStatus && !["unresolved", "unavailable", "unknown"].includes(facts.resolutionStatus);

    let state = "partial";
    if (duplicateRisk) state = "duplicate_risk";
    else if (manifestationConflict) state = "manifestation_ambiguity";
    else if (metadataStage || partialVerification || missing.length >= 2) state = "metadata_repair";
    else if (positiveVerification || (doiPresent && missing.length === 0 && retrievalResolved)) state = "verified";

    const labels = {
      verified: "Identità verificata",
      partial: "Identità parziale",
      metadata_repair: "Metadati da riparare",
      manifestation_ambiguity: "Manifestazione da risolvere",
      duplicate_risk: "Rischio duplicato",
    };
    const summaries = {
      verified: "Il record è sufficientemente identificato per separare la verifica bibliografica dallo screening scientifico.",
      partial: "Il record è leggibile, ma almeno un segnale d’identità resta più debole del livello desiderato.",
      metadata_repair: "La scheda è ancora nell’identity gate: i metadati devono essere riparati prima di registrare uno screening scientifico.",
      manifestation_ambiguity: "Il lavoro è riconoscibile, ma versione, data o manifestazione non sono ancora abbastanza risolte per trattarlo come record stabile.",
      duplicate_risk: "Esiste un segnale di possibile equivalenza con un altro record. Va confrontata l’identità del lavoro prima di usare l’esito duplicate.",
    };
    const reasons = [];
    if (verification) reasons.push(`verification: ${verification}`);
    if (doiPresent) reasons.push("DOI presente");
    else reasons.push("DOI non registrato");
    if (retrievalResolved) reasons.push(`retrieval: ${facts.resolutionStatus}`);
    if (missing.length) reasons.push(`campi da verificare: ${missing.join(", ")}`);
    if (duplicateRisk) reasons.push(`duplicate note: ${duplicateNote}`);
    if (conflictPresent) reasons.push(`metadata conflict: ${metadataConflict}`);

    return {
      ...facts,
      state,
      label: labels[state],
      summary: summaries[state],
      reasons,
      duplicateNote,
      metadataConflict,
      requiredAction,
      missing,
      doiPresent,
      blocksScreening: metadataStage || state === "metadata_repair" || state === "manifestation_ambiguity",
    };
  }

  function makeFact(label, state, title = "") {
    const fact = document.createElement("span");
    fact.className = "identity-fact";
    fact.dataset.state = state;
    fact.textContent = label;
    if (title) fact.title = title;
    return fact;
  }

  function safeExistingLink(id, label) {
    const source = byId(id);
    if (!(source instanceof HTMLAnchorElement) || source.hidden || !source.href) return null;
    const link = document.createElement("a");
    link.className = "identity-action";
    link.href = source.href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = label;
    return link;
  }

  function ensureIdentityPanel() {
    const detail = byId("candidate-detail");
    if (!detail) return null;
    let panel = byId("candidate-identity-panel");
    if (panel) return panel;
    panel = document.createElement("section");
    panel.id = "candidate-identity-panel";
    panel.className = "candidate-identity-panel";
    panel.innerHTML = `
      <div class="identity-panel-heading">
        <div>
          <p class="workspace-label">Identity resolution</p>
          <h4 id="candidate-identity-title">Identità da verificare</h4>
        </div>
        <span id="candidate-identity-state" class="identity-state-chip">—</span>
      </div>
      <p id="candidate-identity-summary" class="identity-summary"></p>
      <div id="candidate-identity-facts" class="identity-facts" aria-label="Segnali di identità"></div>
      <p id="candidate-identity-reason" class="identity-reason"></p>
      <div id="candidate-identity-actions" class="identity-actions"></div>
      <p class="identity-boundary">Diagnostica preparatoria: non è una decisione di eligibility, duplicate o canonicalizzazione.</p>
    `;
    detail.querySelector(".candidate-metadata")?.insertAdjacentElement("afterend", panel);
    return panel;
  }

  function renderIdentity() {
    const panel = ensureIdentityPanel();
    if (!panel) return;
    currentIdentity = identityAssessment();
    panel.dataset.state = currentIdentity.state;
    byId("candidate-detail").dataset.identityState = currentIdentity.state;
    byId("candidate-detail").dataset.identityBlocked = String(currentIdentity.blocksScreening);
    byId("candidate-identity-title").textContent = currentIdentity.label;
    const state = byId("candidate-identity-state");
    state.textContent = currentIdentity.blocksScreening ? "IDENTITY GATE" : "SCREENING READY";
    state.dataset.state = currentIdentity.state;
    byId("candidate-identity-summary").textContent = currentIdentity.summary;

    const facts = byId("candidate-identity-facts");
    facts.replaceChildren(
      makeFact("Autori", isMissing(currentIdentity.authors) ? "warning" : "positive"),
      makeFact("Anno", isMissing(currentIdentity.year) ? "warning" : "positive"),
      makeFact("Sede", isMissing(currentIdentity.venue) ? "warning" : "positive"),
      makeFact("DOI", currentIdentity.doiPresent ? "positive" : "neutral"),
      makeFact(
        currentIdentity.resolutionStatus ? `Retrieval · ${currentIdentity.resolutionStatus}` : "Retrieval da verificare",
        currentIdentity.resolutionStatus && !["unresolved", "unavailable", "unknown"].includes(currentIdentity.resolutionStatus)
          ? "positive"
          : "neutral",
      ),
    );

    const reasonParts = [...currentIdentity.reasons];
    if (currentIdentity.requiredAction) reasonParts.push(`azione: ${currentIdentity.requiredAction}`);
    byId("candidate-identity-reason").textContent = reasonParts.join(" · ") || "Nessun segnale aggiuntivo registrato.";

    const actions = byId("candidate-identity-actions");
    actions.replaceChildren();
    const article = safeExistingLink("selected-candidate-article", "Apri fonte migliore ↗");
    const doi = safeExistingLink("selected-candidate-doi-link", "Verifica DOI ↗");
    const audit = safeExistingLink("selected-candidate-issue", "Audit record ↗");
    for (const link of [article, doi, audit]) if (link) actions.append(link);
    const recalc = document.createElement("button");
    recalc.type = "button";
    recalc.className = "identity-action identity-recalc";
    recalc.textContent = "Ricalcola identità";
    recalc.addEventListener("click", refreshGuidedSurface);
    actions.append(recalc);

    document.dispatchEvent(new CustomEvent("curator:identity-state", { detail: currentIdentity }));
  }

  function decisionLabelFor(code, fallback) {
    const labels = {
      eligible_core: "Core",
      eligible_contextual: "Contestuale",
      maybe_full_text_needed: "Serve altro testo",
      not_eligible: "Fuori perimetro",
      duplicate: "Duplicato",
      not_academic: "Non accademico",
      not_retrievable: "Non reperibile",
    };
    return labels[code] || fallback || code;
  }

  function ensureDecisionComposer() {
    const form = byId("decision-form");
    const decision = byId("decision");
    if (!form || !decision) return null;
    decision.required = false;
    decision.closest("label")?.classList.add("identity-native-decision-field");
    let composer = byId("guided-decision-composer");
    if (composer) return composer;
    composer = document.createElement("section");
    composer.id = "guided-decision-composer";
    composer.className = "guided-decision-composer";
    composer.innerHTML = `
      <div class="guided-decision-heading">
        <div>
          <p class="workspace-label">Decision gate</p>
          <h4 id="guided-decision-title">Dall’evidenza all’esito</h4>
        </div>
        <span id="guided-decision-gate" class="identity-state-chip">—</span>
      </div>
      <div class="decision-progress" aria-label="Progressione della review">
        <span id="decision-step-identity">1 · Identità</span>
        <span id="decision-step-evidence">2 · Evidenza</span>
        <span id="decision-step-outcome">3 · Esito</span>
      </div>
      <p id="guided-decision-copy" class="guided-decision-copy"></p>
      <div id="guided-primary-decisions" class="guided-decision-grid"></div>
      <details id="guided-exception-decisions" class="guided-exception-decisions">
        <summary>Gestione record eccezionale</summary>
        <p>Usa questi esiti solo dopo aver verificato la condizione specifica.</p>
        <div id="guided-exception-grid" class="guided-decision-grid guided-decision-grid-exception"></div>
      </details>
      <p id="guided-decision-message" class="guided-decision-message" role="status" aria-live="polite" hidden></p>
      <p class="identity-boundary">Le card impostano il medesimo valore governato del select originale; non costituiscono una raccomandazione automatica.</p>
    `;
    form.querySelector(".decision-form-heading")?.insertAdjacentElement("afterend", composer);

    form.addEventListener(
      "submit",
      (event) => {
        if (currentIdentity?.blocksScreening) {
          event.preventDefault();
          event.stopImmediatePropagation();
          showDecisionMessage("Completa prima l’identity gate: questa scheda non è ancora pronta per uno screening scientifico.", "warning");
          byId("candidate-identity-panel")?.scrollIntoView({ behavior: "smooth", block: "center" });
          return;
        }
        if (!decision.value) {
          event.preventDefault();
          event.stopImmediatePropagation();
          showDecisionMessage("Scegli un esito curatoriale prima dell’invio.", "warning");
          composer.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      },
      true,
    );
    decision.addEventListener("change", syncDecisionSelection);
    return composer;
  }

  function showDecisionMessage(text, state = "neutral") {
    const message = byId("guided-decision-message");
    if (!message) return;
    message.textContent = text;
    message.dataset.state = state;
    message.hidden = false;
  }

  function clearDecisionMessage() {
    const message = byId("guided-decision-message");
    if (!message) return;
    message.textContent = "";
    message.hidden = true;
    delete message.dataset.state;
  }

  function makeDecisionChoice(option, contextual = false) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "guided-decision-choice";
    button.dataset.value = option.value;
    if (contextual) button.dataset.contextual = "true";
    const title = document.createElement("strong");
    title.textContent = decisionLabelFor(option.value, option.textContent);
    const description = document.createElement("span");
    description.textContent = option.title || option.textContent;
    button.append(title, description);
    button.addEventListener("click", () => {
      if (currentIdentity?.blocksScreening) {
        showDecisionMessage("L’esito resta disabilitato finché l’identità bibliografica non è risolta.", "warning");
        return;
      }
      const select = byId("decision");
      select.value = option.value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      clearDecisionMessage();
    });
    return button;
  }

  function buildDecisionChoices() {
    ensureDecisionComposer();
    const select = byId("decision");
    const primary = byId("guided-primary-decisions");
    const exception = byId("guided-exception-grid");
    if (!select || !primary || !exception) return;
    const options = Array.from(select.options).filter((option) => option.value);
    primary.replaceChildren(
      ...options.filter((option) => PRIMARY_DECISIONS.has(option.value)).map((option) => makeDecisionChoice(option)),
    );
    const duplicateContext = currentIdentity?.state === "duplicate_risk";
    exception.replaceChildren(
      ...options
        .filter((option) => EXCEPTION_DECISIONS.has(option.value))
        .map((option) => makeDecisionChoice(option, duplicateContext && option.value === "duplicate")),
    );
    const details = byId("guided-exception-decisions");
    if (details && duplicateContext) details.open = true;
    syncDecisionSelection();
  }

  function syncDecisionSelection() {
    const value = byId("decision")?.value || "";
    for (const choice of document.querySelectorAll(".guided-decision-choice")) {
      choice.dataset.selected = String(choice.dataset.value === value);
      choice.setAttribute("aria-pressed", String(choice.dataset.value === value));
    }
    const outcome = byId("decision-step-outcome");
    if (outcome) outcome.dataset.state = value ? "ready" : "waiting";
  }

  function evidenceReady() {
    const source = normalise(byId("candidate-abstract-source")?.textContent).toLowerCase();
    const aidVisible = byId("candidate-reading-aid-panel") && !byId("candidate-reading-aid-panel").hidden;
    return Boolean(source && !source.includes("da recuperare") && !source.includes("in corso")) || aidVisible;
  }

  function applyIdentityToDecision() {
    const composer = ensureDecisionComposer();
    if (!composer || !currentIdentity) return;
    composer.dataset.identityState = currentIdentity.state;
    composer.dataset.blocked = String(currentIdentity.blocksScreening);
    const gate = byId("guided-decision-gate");
    gate.textContent = currentIdentity.blocksScreening ? "BLOCCATO DALL’IDENTITÀ" : "SCREENING APERTO";
    gate.dataset.state = currentIdentity.state;
    const identityStep = byId("decision-step-identity");
    identityStep.dataset.state = currentIdentity.blocksScreening ? "warning" : "ready";
    const evidenceStep = byId("decision-step-evidence");
    evidenceStep.dataset.state = evidenceReady() ? "ready" : "waiting";
    const copy = byId("guided-decision-copy");
    if (currentIdentity.blocksScreening) {
      copy.textContent =
        "Questa scheda è ancora un problema di identificazione, non di eligibility. Verifica fonte, DOI e conflitti; poi fai rientrare il record nello screening.";
    } else if (currentIdentity.state === "duplicate_risk") {
      copy.textContent =
        "Prima confronta l’identità del lavoro con il possibile duplicato. Se non è lo stesso lavoro, continua normalmente con lo screening; nessun esito è preselezionato.";
    } else {
      copy.textContent =
        "Scegli l’esito dopo aver esaminato l’evidenza. Gli esiti principali sono separati dalla gestione eccezionale del record per ridurre errori di classificazione.";
    }
    const submit = byId("submit-decision");
    if (submit && !/Invio|registrata/i.test(submit.textContent || "")) {
      submit.disabled = currentIdentity.blocksScreening;
      submit.title = currentIdentity.blocksScreening
        ? "Risolvi prima l’identità bibliografica."
        : "";
    }
    for (const choice of document.querySelectorAll(".guided-decision-choice")) {
      choice.disabled = currentIdentity.blocksScreening;
    }
    buildDecisionChoices();
  }

  function refreshGuidedSurface() {
    const detail = byId("candidate-detail");
    const candidateId = normalise(byId("selected-candidate-id")?.textContent);
    if (!detail || detail.hidden || !candidateId || candidateId === "—") return;
    const changed = candidateId !== activeCandidateId;
    activeCandidateId = candidateId;
    if (changed) clearDecisionMessage();
    renderIdentity();
    buildDecisionChoices();
    applyIdentityToDecision();
  }

  function injectStyles() {
    if (byId("curator-identity-styles")) return;
    const style = document.createElement("style");
    style.id = "curator-identity-styles";
    style.textContent = `
      .candidate-identity-panel{margin:18px 30px 2px;border:1px solid var(--line);border-left:4px solid var(--green);border-radius:14px;padding:18px 20px;background:#fff;box-shadow:0 8px 22px rgb(23 33 31 / 5%)}
      .candidate-identity-panel[data-state="metadata_repair"],.candidate-identity-panel[data-state="manifestation_ambiguity"]{border-left-color:#b4861d;background:#fffaf0}
      .candidate-identity-panel[data-state="duplicate_risk"]{border-left-color:var(--rust);background:#fff9f5}
      .identity-panel-heading,.guided-decision-heading{display:flex;gap:18px;align-items:flex-start;justify-content:space-between}
      .identity-panel-heading h4,.guided-decision-heading h4{margin:3px 0 0;font-family:Georgia,"Times New Roman",serif;font-size:1.25rem;font-weight:500}
      .identity-state-chip{display:inline-flex;flex:0 0 auto;align-items:center;border:1px solid rgb(24 63 56 / 22%);border-radius:999px;padding:6px 9px;background:var(--green-soft);color:var(--green);font-size:.58rem;font-weight:820;letter-spacing:.04em}
      .identity-state-chip[data-state="metadata_repair"],.identity-state-chip[data-state="manifestation_ambiguity"]{border-color:#dcc17b;background:#fff4cf;color:#6c5510}
      .identity-state-chip[data-state="duplicate_risk"]{border-color:#d7a08f;background:#fbe9e2;color:#7a321f}
      .identity-summary{max-width:82ch;margin:13px 0 11px;font-size:.82rem;line-height:1.55}
      .identity-facts{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}
      .identity-fact{display:inline-flex;border:1px solid var(--line);border-radius:999px;padding:4px 8px;background:var(--paper-deep);color:var(--ink-soft);font-size:.58rem;font-weight:760}
      .identity-fact[data-state="positive"]{border-color:rgb(24 63 56 / 20%);background:var(--green-soft);color:var(--green)}
      .identity-fact[data-state="warning"]{border-color:#dcc17b;background:#fff4cf;color:#6c5510}
      .identity-reason{margin:0;color:var(--ink-soft);font-size:.66rem;line-height:1.5;overflow-wrap:anywhere}
      .identity-actions{display:flex;flex-wrap:wrap;gap:7px;margin-top:13px}
      .identity-action{min-height:32px;border:1px solid var(--line);border-radius:999px;padding:6px 10px;background:var(--surface);color:var(--green);font:inherit;font-size:.62rem;font-weight:760;text-decoration:none;cursor:pointer}
      .identity-recalc{min-height:32px;align-self:auto;background:transparent;color:var(--ink-soft)}
      .identity-boundary{margin:12px 0 0;color:var(--ink-soft);font-size:.59rem;line-height:1.45}
      .guided-decision-composer{margin:0 0 20px;border:1px solid var(--line);border-radius:14px;padding:18px 20px;background:var(--paper-deep)}
      .guided-decision-composer[data-blocked="true"]{border-color:#dcc17b;background:#fffaf0}
      .decision-progress{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:15px 0 14px}
      .decision-progress span{border-top:3px solid var(--line);padding-top:6px;color:var(--ink-soft);font-size:.59rem;font-weight:760}
      .decision-progress span[data-state="ready"]{border-color:var(--green);color:var(--green)}
      .decision-progress span[data-state="warning"]{border-color:#b4861d;color:#6c5510}
      .guided-decision-copy{max-width:86ch;margin:0 0 14px;color:var(--ink-soft);font-size:.73rem;line-height:1.5}
      .guided-decision-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
      .guided-decision-choice{display:flex;min-height:76px;flex-direction:column;align-items:flex-start;justify-content:flex-start;border:1px solid var(--line);border-radius:10px;padding:11px 12px;background:#fff;color:var(--ink);text-align:left;cursor:pointer}
      .guided-decision-choice strong{font-family:Georgia,"Times New Roman",serif;font-size:.92rem;font-weight:500}
      .guided-decision-choice span{margin-top:4px;color:var(--ink-soft);font-size:.61rem;line-height:1.35}
      .guided-decision-choice:hover,.guided-decision-choice[data-selected="true"]{border-color:var(--green);box-shadow:0 0 0 2px rgb(24 63 56 / 8%)}
      .guided-decision-choice[data-selected="true"]{background:var(--green-soft)}
      .guided-decision-choice[data-contextual="true"]{border-color:#d7a08f;background:#fff9f5}
      .guided-decision-choice:disabled{cursor:not-allowed;opacity:.48}
      .guided-exception-decisions{margin-top:10px;border-top:1px solid var(--line);padding-top:9px}
      .guided-exception-decisions summary{color:var(--green);font-size:.65rem;font-weight:780;cursor:pointer}
      .guided-exception-decisions>p{margin:7px 0 9px;color:var(--ink-soft);font-size:.62rem}
      .guided-decision-grid-exception{grid-template-columns:repeat(3,minmax(0,1fr))}
      .guided-decision-message{margin:12px 0 0;border-left:3px solid var(--rust);padding:8px 10px;background:#fff;color:var(--ink-soft);font-size:.68rem}
      .guided-decision-message[data-state="warning"]{border-left-color:#b4861d;background:#fff8e7}
      .identity-native-decision-field{position:absolute!important;width:1px!important;height:1px!important;overflow:hidden!important;clip-path:inset(50%)!important;white-space:nowrap!important}
      @media(max-width:920px){.candidate-identity-panel{margin:15px 18px 2px}.guided-decision-grid-exception{grid-template-columns:1fr}.guided-decision-grid{grid-template-columns:1fr 1fr}}
      @media(max-width:640px){.candidate-identity-panel{margin:12px 14px 2px;padding:15px}.identity-panel-heading,.guided-decision-heading{flex-direction:column;gap:8px}.guided-decision-composer{padding:15px}.guided-decision-grid{grid-template-columns:1fr}.decision-progress{gap:4px}.decision-progress span{font-size:.54rem}.identity-actions{display:grid;grid-template-columns:1fr 1fr}.identity-action{text-align:center}}
    `;
    document.head.append(style);
  }

  function observe() {
    const detail = byId("candidate-detail");
    const id = byId("selected-candidate-id");
    const provenance = byId("candidate-provenance");
    const decision = byId("decision");
    if (!detail || !id || !provenance || !decision) return;
    const observer = new MutationObserver(() => queueMicrotask(refreshGuidedSurface));
    observer.observe(detail, { attributes: true, attributeFilter: ["hidden"] });
    observer.observe(id, { childList: true, characterData: true, subtree: true });
    observer.observe(provenance, { childList: true, subtree: true });
    for (const node of [
      byId("selected-candidate-authors"),
      byId("selected-candidate-year"),
      byId("selected-candidate-venue"),
      byId("selected-candidate-doi"),
      byId("selected-candidate-stage"),
      byId("selected-candidate-retrieval-status"),
      byId("selected-candidate-access-status"),
      byId("candidate-abstract-source"),
      byId("candidate-reading-aid-panel"),
    ]) {
      if (node) observer.observe(node, { childList: true, characterData: true, subtree: true, attributes: true, attributeFilter: ["hidden", "data-state"] });
    }
    observer.observe(decision, { childList: true });
    document.addEventListener("change", (event) => {
      if (event.target === decision) syncDecisionSelection();
    });
    queueMicrotask(refreshGuidedSurface);
  }

  function initialise() {
    injectStyles();
    ensureIdentityPanel();
    ensureDecisionComposer();
    observe();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialise, { once: true });
  } else {
    initialise();
  }
})();
