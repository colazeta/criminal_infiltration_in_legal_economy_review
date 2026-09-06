"use strict";

(() => {
  const HEADING = "## Abstract resolution — assisted";
  const byId = (id) => document.getElementById(id);
  let controller = null;
  let activeKey = "";

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

  function section(body) {
    const source = String(body || "").replace(/\r\n/g, "\n");
    const start = source.indexOf(HEADING);
    if (start < 0) return "";
    const remainder = source.slice(start + HEADING.length).replace(/^\s*\n/, "");
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
      .candidate-assisted-resolution{margin:2px 30px 20px;border:1px solid var(--line);border-left:4px solid #876b2b;border-radius:14px;padding:16px 18px;background:#fffdf7;box-shadow:0 7px 18px rgb(23 33 31 / 4%)}
      .candidate-assisted-resolution[data-state="full_text_or_intro_ready"]{border-left-color:var(--green);background:#f8fcfa}
      .candidate-assisted-resolution[data-state="publisher_summary_ready"]{border-left-color:#55746d;background:#fbfdfc}
      .candidate-assisted-resolution[data-state="metadata_only"]{border-left-color:#b4861d;background:#fffaf0}
      .candidate-assisted-resolution[data-state="known_noise"]{border-left-color:var(--rust);background:#fff8f4}
      .assisted-resolution-heading{display:flex;gap:16px;align-items:flex-start;justify-content:space-between}
      .assisted-resolution-heading h4{margin:3px 0 0;font-family:Georgia,"Times New Roman",serif;font-size:1.08rem;font-weight:500}
      .assisted-resolution-chip{display:inline-flex;flex:0 0 auto;border:1px solid var(--line);border-radius:999px;padding:5px 8px;background:#fff;color:var(--ink-soft);font-size:.57rem;font-weight:820;letter-spacing:.035em}
      .candidate-assisted-resolution[data-state="full_text_or_intro_ready"] .assisted-resolution-chip{background:var(--green-soft);color:var(--green)}
      .candidate-assisted-resolution[data-state="metadata_only"] .assisted-resolution-chip{background:#fff4cf;color:#6c5510}
      .candidate-assisted-resolution[data-state="known_noise"] .assisted-resolution-chip{background:#fbe9e2;color:#7a321f}
      .assisted-resolution-abstract{margin:11px 0 5px;color:var(--ink-soft);font-size:.64rem;font-weight:760}
      .assisted-resolution-action{margin:0;max-width:92ch;font-size:.77rem;line-height:1.5}
      .assisted-resolution-note{margin:7px 0 0;color:var(--ink-soft);font-size:.66rem;line-height:1.45}
      .assisted-resolution-source{display:inline-flex;margin-top:11px;color:var(--green);font-size:.63rem;font-weight:760;text-decoration:none}
      .assisted-resolution-boundary{margin:10px 0 0;color:var(--ink-soft);font-size:.58rem;line-height:1.4}
      @media(max-width:920px){.candidate-assisted-resolution{margin:2px 18px 18px}}
      @media(max-width:640px){.candidate-assisted-resolution{margin:2px 14px 16px;padding:14px}.assisted-resolution-heading{flex-direction:column;gap:7px}}
    `;
    document.head.append(style);
  }

  function ensurePanel() {
    let panel = byId("candidate-assisted-resolution-panel");
    if (panel) return panel;
    const detail = byId("candidate-detail");
    if (!detail) return null;
    panel = node("section", {
      id: "candidate-assisted-resolution-panel",
      className: "candidate-assisted-resolution",
    });
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
      text: "Questo stato descrive la reviewability del record e la prossima azione di retrieval. Non è un abstract, una decisione di eligibility o una decisione di esclusione.",
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

  function render(payload) {
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

  async function refresh() {
    const candidateId = clean(byId("selected-candidate-id")?.textContent);
    const detail = byId("candidate-detail");
    const issue = issueInfo();
    if (!candidateId || candidateId === "—" || !detail || detail.hidden || !issue) return hidePanel();
    const key = `${candidateId}|${issue.owner}/${issue.repo}#${issue.number}`;
    if (key === activeKey && !byId("candidate-assisted-resolution-panel")?.hidden) return;
    activeKey = key;
    controller?.abort();
    controller = new AbortController();
    try {
      const response = await fetch(`https://api.github.com/repos/${encodeURIComponent(issue.owner)}/${encodeURIComponent(issue.repo)}/issues/${issue.number}`, {
        signal: controller.signal,
        headers: {
          Accept: "application/vnd.github+json",
          "X-GitHub-Api-Version": "2022-11-28",
        },
      });
      if (!response.ok) throw new Error(`issue_${response.status}`);
      const body = String((await response.json())?.body || "");
      if (activeKey !== key) return;
      const parsed = section(body);
      render(parsed ? fields(parsed) : null);
    } catch (error) {
      if (error?.name === "AbortError" || activeKey !== key) return;
      hidePanel();
    }
  }

  function initialise() {
    injectStyles();
    ensurePanel();
    const detail = byId("candidate-detail");
    const id = byId("selected-candidate-id");
    const issue = byId("selected-candidate-issue");
    if (!detail || !id || !issue) return;
    const observer = new MutationObserver(() => queueMicrotask(refresh));
    observer.observe(detail, { attributes: true, attributeFilter: ["hidden"] });
    observer.observe(id, { childList: true, characterData: true, subtree: true });
    observer.observe(issue, { attributes: true, attributeFilter: ["href"] });
    queueMicrotask(refresh);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialise, { once: true });
  } else {
    initialise();
  }
})();
