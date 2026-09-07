"use strict";

(() => {
  const byId = (id) => document.getElementById(id);

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
      source.textContent = `Apri ${payload["Best assisted source"] || "fonte assistita"} ↗`;
    } else {
      source.hidden = true;
      source.removeAttribute("href");
    }
    document.dispatchEvent(new CustomEvent("curator:assisted-resolution", {
      detail: { resolutionClass, standaloneAbstractStatus: payload["Standalone abstract status"] || "" },
    }));
  }

  function consumeCandidateContext(event) {
    const candidateId = clean(event?.detail?.candidateId);
    const selected = clean(byId("selected-candidate-id")?.textContent);
    if (!candidateId || candidateId !== selected) return;
    renderResolution(event?.detail?.context?.assistedResolution || null);
  }

  function initialise() {
    injectStyles();
    ensurePanel();
    document.addEventListener("curator:candidate-context", consumeCandidateContext);
    const id = byId("selected-candidate-id");
    if (id) {
      const observer = new MutationObserver(hidePanel);
      observer.observe(id, { childList: true, characterData: true, subtree: true });
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialise, { once: true });
  else initialise();
})();
