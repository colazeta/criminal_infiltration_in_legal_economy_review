"use strict";

(() => {
  const SESSION_KEY = "criminal-infiltration-curator-session";
  const config = window.CURATOR_APP_CONFIG || {};
  const apiBaseUrl = String(config.apiBaseUrl || "").replace(/\/$/, "");
  const originalFetch = window.fetch.bind(window);
  const resolutions = new Map();
  const frontiers = new Map();
  let activeCandidateId = "";

  const byId = (id) => document.getElementById(id);

  function clean(value) {
    return String(value ?? "").replace(/\s+/g, " ").trim();
  }

  function selectedCandidateId() {
    return clean(byId("selected-candidate-id")?.textContent);
  }

  function sessionToken() {
    try {
      return sessionStorage.getItem(SESSION_KEY) || "";
    } catch {
      return "";
    }
  }

  function element(tag, options = {}) {
    const node = document.createElement(tag);
    if (options.id) node.id = options.id;
    if (options.className) node.className = options.className;
    if (options.text !== undefined) node.textContent = options.text;
    return node;
  }

  function stateLabel(state) {
    return {
      verified: "Consensus verificato",
      partial: "Consensus parziale",
      conflict: "Conflitto tra fonti",
      manifestation_ambiguity: "Manifestazioni multiple",
    }[state] || "Consensus da verificare";
  }

  function fieldStateLabel(state) {
    return {
      verified: "concorde",
      resolved_conflict: "conflitto risolto",
      conflict: "conflitto",
      missing: "mancante",
    }[state] || clean(state) || "da verificare";
  }

  function fieldDisplayName(field) {
    return {
      title: "Titolo",
      doi: "DOI",
      year: "Anno",
      authors: "Autori",
      venue: "Sede editoriale",
    }[field] || field;
  }

  function isBlocking(resolution) {
    return Boolean(
      resolution
      && (resolution.screeningReady === false
        || resolution.identityState === "conflict"
        || resolution.identityState === "manifestation_ambiguity"),
    );
  }

  function ensureStyles() {
    if (byId("curator-consensus-styles")) return;
    const style = element("style", { id: "curator-consensus-styles" });
    style.textContent = `
      .candidate-consensus-panel{margin:10px 30px 4px;border:1px solid var(--line);border-radius:14px;background:var(--surface);overflow:hidden}
      .candidate-consensus-panel[data-state="conflict"],.candidate-consensus-panel[data-state="manifestation_ambiguity"]{border-color:#d5b15d;background:#fffbf1}
      .consensus-heading{display:flex;gap:18px;align-items:flex-start;justify-content:space-between;padding:16px 18px;border-bottom:1px solid var(--line)}
      .consensus-heading h4{margin:3px 0 0;font-family:Georgia,"Times New Roman",serif;font-size:1.15rem;font-weight:500}
      .consensus-state{display:inline-flex;border:1px solid rgb(24 63 56 / 22%);border-radius:999px;padding:5px 8px;background:var(--green-soft);color:var(--green);font-size:.56rem;font-weight:820;letter-spacing:.04em}
      .consensus-state[data-state="partial"]{background:var(--paper-deep);color:var(--ink-soft)}
      .consensus-state[data-state="conflict"],.consensus-state[data-state="manifestation_ambiguity"]{border-color:#dcc17b;background:#fff4cf;color:#6c5510}
      .consensus-summary{margin:0;padding:13px 18px 8px;color:var(--ink-soft);font-size:.7rem;line-height:1.5}
      .consensus-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;margin:8px 0 0;background:var(--line)}
      .consensus-field{min-width:0;padding:12px 14px;background:var(--surface)}
      .consensus-field[data-state="conflict"]{background:#fff8e7}
      .consensus-field-head{display:flex;gap:8px;align-items:center;justify-content:space-between}
      .consensus-field-head strong{font-size:.67rem}
      .consensus-field-status{border-radius:999px;padding:3px 6px;background:var(--paper-deep);color:var(--ink-soft);font-size:.52rem;font-weight:780;white-space:nowrap}
      .consensus-field-status[data-state="verified"],.consensus-field-status[data-state="resolved_conflict"]{background:var(--green-soft);color:var(--green)}
      .consensus-field-status[data-state="conflict"]{background:#fff0c2;color:#6c5510}
      .consensus-value{margin:7px 0 5px;overflow-wrap:anywhere;font-family:Georgia,"Times New Roman",serif;font-size:.86rem;line-height:1.35}
      .consensus-providers,.consensus-alternatives{margin:0;color:var(--ink-soft);font-size:.56rem;line-height:1.45;overflow-wrap:anywhere}
      .consensus-alternatives{margin-top:5px;color:#765d18}
      .consensus-manifestation{margin:10px 18px 0;border-left:3px solid #b4861d;padding:8px 10px;background:#fff8e7;color:var(--ink-soft);font-size:.62rem;line-height:1.45}
      .consensus-actions{display:flex;gap:8px;align-items:center;justify-content:space-between;padding:12px 18px 14px}
      .consensus-boundary{max-width:76ch;margin:0;color:var(--ink-soft);font-size:.56rem;line-height:1.4}
      .consensus-citation-button{min-height:34px;flex:0 0 auto;border:1px solid var(--green);border-radius:999px;padding:6px 10px;background:var(--surface);color:var(--green);font:inherit;font-size:.59rem;font-weight:780;cursor:pointer}
      .consensus-citation-button:disabled{opacity:.48;cursor:not-allowed}
      .consensus-frontier{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:0 18px 12px}
      .consensus-frontier article{border:1px solid var(--line);border-radius:9px;padding:9px 10px;background:#fff}
      .consensus-frontier strong{display:block;font-family:Georgia,"Times New Roman",serif;font-size:.86rem;font-weight:500}
      .consensus-frontier span{color:var(--ink-soft);font-size:.56rem;line-height:1.35}
      .identity-fact[data-role="scholarly-consensus"][data-state="warning"]{border-color:#dcc17b;background:#fff4cf;color:#6c5510}
      @media(max-width:920px){.candidate-consensus-panel{margin:10px 18px 4px}}
      @media(max-width:640px){.candidate-consensus-panel{margin:10px 14px 4px}.consensus-heading,.consensus-actions{flex-direction:column;align-items:stretch}.consensus-fields,.consensus-frontier{grid-template-columns:1fr}.consensus-citation-button{width:100%}}
    `;
    document.head.append(style);
  }

  function ensurePanel() {
    const detail = byId("candidate-detail");
    if (!detail) return null;
    let panel = byId("candidate-consensus-panel");
    if (panel) return panel;

    panel = element("section", { id: "candidate-consensus-panel", className: "candidate-consensus-panel" });
    panel.hidden = true;
    const heading = element("div", { className: "consensus-heading" });
    const titleGroup = element("div");
    titleGroup.append(
      element("p", { className: "workspace-label", text: "Scholarly consensus" }),
      element("h4", { id: "candidate-consensus-title", text: "Confronto tra fonti" }),
    );
    heading.append(titleGroup, element("span", { id: "candidate-consensus-state", className: "consensus-state", text: "—" }));
    const summary = element("p", { id: "candidate-consensus-summary", className: "consensus-summary" });
    const fields = element("div", { id: "candidate-consensus-fields", className: "consensus-fields" });
    const manifestation = element("p", { id: "candidate-consensus-manifestation", className: "consensus-manifestation" });
    manifestation.hidden = true;
    const frontier = element("div", { id: "candidate-consensus-frontier", className: "consensus-frontier" });
    frontier.hidden = true;
    const actions = element("div", { className: "consensus-actions" });
    actions.append(
      element("p", {
        className: "consensus-boundary",
        text: "Confronto bibliografico preparatorio: nessun valore viene scritto automaticamente nel record canonico e nessun conflitto decide l’eligibility.",
      }),
    );
    const citationButton = element("button", { id: "candidate-citation-frontier-button", className: "consensus-citation-button", text: "Costruisci E2/E3" });
    citationButton.type = "button";
    citationButton.addEventListener("click", buildCitationFrontier);
    actions.append(citationButton);
    panel.append(heading, summary, fields, manifestation, frontier, actions);

    const identity = byId("candidate-identity-panel");
    if (identity) identity.insertAdjacentElement("afterend", panel);
    else detail.querySelector(".candidate-metadata")?.insertAdjacentElement("afterend", panel);
    return panel;
  }

  function alternativesText(field) {
    const alternatives = Array.isArray(field?.alternatives) ? field.alternatives.slice(0, 2) : [];
    if (!alternatives.length) return "";
    return alternatives
      .map((row) => `${clean(row.value) || "—"} [${(row.providers || []).join(", ") || "fonte non indicata"}]`)
      .join(" · ");
  }

  function fieldCard(name, field) {
    const card = element("article", { className: "consensus-field" });
    const state = clean(field?.status) || "missing";
    card.dataset.state = state;
    const head = element("div", { className: "consensus-field-head" });
    head.append(
      element("strong", { text: fieldDisplayName(name) }),
      element("span", { className: "consensus-field-status", text: fieldStateLabel(state) }),
    );
    head.lastElementChild.dataset.state = state;
    const rawValue = field?.value;
    const value = rawValue === null || rawValue === undefined || rawValue === "" ? "—" : clean(rawValue);
    const selected = element("p", { className: "consensus-value", text: value });
    const providers = element("p", {
      className: "consensus-providers",
      text: `Supporto: ${(field?.providers || []).join(" · ") || "nessuna fonte concorde"}${field?.confidence ? ` · confidenza ${field.confidence}` : ""}`,
    });
    card.append(head, selected, providers);
    const alternatives = alternativesText(field);
    if (alternatives) card.append(element("p", { className: "consensus-alternatives", text: `Alternative: ${alternatives}` }));
    return card;
  }

  function renderFrontier(candidateId) {
    const host = byId("candidate-consensus-frontier");
    if (!host) return;
    const frontier = frontiers.get(candidateId);
    if (!frontier) {
      host.hidden = true;
      host.replaceChildren();
      return;
    }
    const backward = frontier?.summary?.backward || {};
    const forward = frontier?.summary?.forward || {};
    const backwardCard = element("article");
    backwardCard.append(
      element("strong", { text: `${Number(backward.total || 0)} backward` }),
      element("span", { text: `${Number(backward.providerAgreement || 0)} confermate da entrambe le fonti · ${Number(backward.providerUnique || 0)} provider-unique` }),
    );
    const forwardCard = element("article");
    forwardCard.append(
      element("strong", { text: `${Number(forward.total || 0)} forward` }),
      element("span", { text: `${Number(forward.providerAgreement || 0)} confermate da entrambe le fonti · ${Number(forward.providerUnique || 0)} provider-unique` }),
    );
    host.replaceChildren(backwardCard, forwardCard);
    host.hidden = false;
  }

  function renderConsensus(candidateId, resolution) {
    if (!candidateId || candidateId !== selectedCandidateId()) return;
    const panel = ensurePanel();
    if (!panel || !resolution) return;
    resolutions.set(candidateId, resolution);
    panel.hidden = false;
    panel.dataset.state = clean(resolution.identityState) || "partial";
    const state = byId("candidate-consensus-state");
    state.textContent = stateLabel(resolution.identityState);
    state.dataset.state = clean(resolution.identityState) || "partial";
    byId("candidate-consensus-title").textContent = isBlocking(resolution) ? "Risolvi il conflitto bibliografico" : "Confronto tra fonti";
    byId("candidate-consensus-summary").textContent =
      `${Number(resolution.providerCount || 0)} fonti contribuiscono al confronto. `
      + `${(resolution.unresolvedConflicts || []).length ? `Conflitti aperti: ${resolution.unresolvedConflicts.join(", ")}. ` : ""}`
      + `Stato: ${stateLabel(resolution.identityState).toLowerCase()}.`;

    const fields = byId("candidate-consensus-fields");
    fields.replaceChildren(...["title", "doi", "year", "authors", "venue"].map((name) => fieldCard(name, resolution.fields?.[name] || {})));

    const manifestation = byId("candidate-consensus-manifestation");
    const reasons = resolution?.manifestation?.reasons || [];
    const manifestations = resolution?.manifestation?.manifestations || [];
    if (resolution.identityState === "manifestation_ambiguity" || reasons.length) {
      manifestation.textContent = `${reasons.join(" · ") || "Più manifestazioni plausibili rilevate."} Manifestazioni identificate: ${manifestations.length}.`;
      manifestation.hidden = false;
    } else {
      manifestation.textContent = "";
      manifestation.hidden = true;
    }

    const doi = clean(resolution?.fields?.doi?.value || byId("selected-candidate-doi")?.textContent);
    const button = byId("candidate-citation-frontier-button");
    button.disabled = !doi || doi === "Non registrato" || !apiBaseUrl || !sessionToken();
    button.title = button.disabled ? "Serve un DOI risolto nella console autenticata." : "Esegue E2 backward ed E3 forward con OpenCitations + Semantic Scholar.";
    renderFrontier(candidateId);
    queueMicrotask(() => applyConsensusGate(candidateId));
  }

  function consensusFact(candidateId) {
    const facts = byId("candidate-identity-facts");
    const resolution = resolutions.get(candidateId);
    if (!facts || !resolution) return;
    facts.querySelector('[data-role="scholarly-consensus"]')?.remove();
    const fact = element("span", {
      className: "identity-fact",
      text: isBlocking(resolution) ? "Consensus · conflitto" : `Consensus · ${clean(resolution.identityState)}`,
    });
    fact.dataset.role = "scholarly-consensus";
    fact.dataset.state = isBlocking(resolution) ? "warning" : resolution.identityState === "verified" ? "positive" : "neutral";
    fact.title = `${Number(resolution.providerCount || 0)} provider nel confronto field-level.`;
    facts.append(fact);
  }

  function applyConsensusGate(candidateId) {
    if (!candidateId || candidateId !== selectedCandidateId()) return;
    const resolution = resolutions.get(candidateId);
    const detail = byId("candidate-detail");
    if (!resolution || !detail) return;
    const blocked = isBlocking(resolution);
    detail.dataset.scholarIdentityState = clean(resolution.identityState) || "partial";
    detail.dataset.scholarIdentityBlocked = String(blocked);
    consensusFact(candidateId);

    const composer = byId("guided-decision-composer");
    const submit = byId("submit-decision");
    const nativeBlocked = detail.dataset.identityBlocked === "true";
    if (composer && blocked) composer.dataset.blocked = "true";
    if (blocked) {
      const gate = byId("guided-decision-gate");
      if (gate) {
        gate.textContent = "BLOCCATO DAL CONSENSUS";
        gate.dataset.state = resolution.identityState;
      }
      const step = byId("decision-step-identity");
      if (step) step.dataset.state = "warning";
      const copy = byId("guided-decision-copy");
      if (copy) copy.textContent = "Le fonti bibliografiche non concordano ancora sull’identità o sulla manifestazione del lavoro. Risolvi questo conflitto prima dello screening scientifico.";
      if (submit && !/Invio|registrata/i.test(submit.textContent || "")) {
        submit.disabled = true;
        submit.title = "Risolvi prima il conflitto bibliografico mostrato nel scholarly consensus.";
      }
      for (const choice of document.querySelectorAll(".guided-decision-choice")) choice.disabled = true;
    } else if (!nativeBlocked) {
      if (composer) composer.dataset.blocked = "false";
      if (submit && !/Invio|registrata/i.test(submit.textContent || "")) {
        submit.disabled = false;
        if (/scholarly consensus/i.test(submit.title || "")) submit.title = "";
      }
      for (const choice of document.querySelectorAll(".guided-decision-choice")) choice.disabled = false;
    }
  }

  async function buildCitationFrontier() {
    const candidateId = selectedCandidateId();
    const resolution = resolutions.get(candidateId);
    const button = byId("candidate-citation-frontier-button");
    if (!candidateId || !resolution || !button || button.disabled) return;
    const title = clean(byId("selected-candidate-title")?.textContent);
    const year = clean(byId("selected-candidate-year")?.textContent);
    const doi = clean(resolution?.fields?.doi?.value || byId("selected-candidate-doi")?.textContent);
    if (!title || !doi || !apiBaseUrl) return;
    button.disabled = true;
    button.textContent = "E2/E3 in corso…";
    try {
      const target = new URL(`${apiBaseUrl}/api/enrichment`);
      target.searchParams.set("title", title);
      target.searchParams.set("doi", doi);
      if (year && year !== "Non registrato") target.searchParams.set("year", year);
      target.searchParams.set("citations", "1");
      const response = await window.fetch(target, {
        headers: { Authorization: `Bearer ${sessionToken()}` },
      });
      if (!response.ok) throw new Error("citation_frontier_unavailable");
      const payload = await response.json();
      if (payload?.citationFrontier) {
        frontiers.set(candidateId, payload.citationFrontier);
        renderFrontier(candidateId);
        button.textContent = "Aggiorna E2/E3";
      } else {
        button.textContent = "E2/E3 non disponibili";
      }
    } catch {
      button.textContent = "Riprova E2/E3";
    } finally {
      button.disabled = false;
    }
  }

  function enrichmentUrl(input) {
    try {
      if (input instanceof URL) return new URL(input.toString());
      if (typeof input === "string") return new URL(input, window.location.href);
      if (input instanceof Request) return new URL(input.url);
    } catch {
      return null;
    }
    return null;
  }

  function enrichRequestUrl(url) {
    if (!url || url.pathname !== "/api/enrichment") return url;
    const authors = clean(byId("selected-candidate-authors")?.textContent);
    const venue = clean(byId("selected-candidate-venue")?.textContent);
    if (authors && !/^Non registrat/i.test(authors) && !url.searchParams.has("authors")) url.searchParams.set("authors", authors);
    if (venue && !/^Non registrat/i.test(venue) && !url.searchParams.has("venue")) url.searchParams.set("venue", venue);
    return url;
  }

  window.fetch = async (input, init) => {
    const url = enrichmentUrl(input);
    const isEnrichment = Boolean(url && url.pathname === "/api/enrichment");
    let requestInput = input;
    if (isEnrichment && !(input instanceof Request)) requestInput = enrichRequestUrl(url).toString();
    const response = await originalFetch(requestInput, init);
    if (isEnrichment && response.ok) {
      const candidateId = selectedCandidateId();
      response.clone().json().then((payload) => {
        if (candidateId && payload?.metadataResolution) renderConsensus(candidateId, payload.metadataResolution);
        if (candidateId && payload?.citationFrontier) {
          frontiers.set(candidateId, payload.citationFrontier);
          renderFrontier(candidateId);
        }
      }).catch(() => {});
    }
    return response;
  };

  function resetForCandidate() {
    const candidateId = selectedCandidateId();
    if (!candidateId || candidateId === "—") return;
    const changed = candidateId !== activeCandidateId;
    activeCandidateId = candidateId;
    if (!changed) return;
    const panel = ensurePanel();
    const resolution = resolutions.get(candidateId);
    if (resolution) renderConsensus(candidateId, resolution);
    else {
      panel.hidden = true;
      panel.removeAttribute("data-state");
    }
  }

  function observe() {
    const detail = byId("candidate-detail");
    const id = byId("selected-candidate-id");
    if (!detail || !id) return;
    const observer = new MutationObserver(() => queueMicrotask(resetForCandidate));
    observer.observe(detail, { attributes: true, attributeFilter: ["hidden"] });
    observer.observe(id, { childList: true, characterData: true, subtree: true });
    document.addEventListener("curator:identity-state", () => {
      const candidateId = selectedCandidateId();
      if (candidateId) queueMicrotask(() => applyConsensusGate(candidateId));
    });
    document.addEventListener("submit", (event) => {
      if (event.target?.id !== "decision-form") return;
      const candidateId = selectedCandidateId();
      const resolution = resolutions.get(candidateId);
      if (!isBlocking(resolution)) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      const message = byId("guided-decision-message");
      if (message) {
        message.textContent = "Risolvi prima il conflitto bibliografico evidenziato nel scholarly consensus.";
        message.dataset.state = "warning";
        message.hidden = false;
      }
      byId("candidate-consensus-panel")?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, true);
    queueMicrotask(resetForCandidate);
  }

  function initialise() {
    ensureStyles();
    ensurePanel();
    observe();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialise, { once: true });
  else initialise();
})();
