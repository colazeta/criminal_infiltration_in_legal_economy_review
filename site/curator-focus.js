"use strict";

(() => {
  const byId = (id) => document.getElementById(id);
  let scheduled = false;

  function visible(node) {
    return Boolean(node && !node.hidden);
  }

  function setFocusMode() {
    const session = byId("curator-session-panel");
    const consoleNode = byId("editorial-console");
    document.body.classList.toggle(
      "curator-focus-active",
      visible(session) && visible(consoleNode),
    );
  }

  function ensureIdentityLine() {
    const byline = byId("selected-candidate-byline");
    if (!byline) return null;
    let line = byId("candidate-identity-line");
    if (line) return line;

    line = document.createElement("div");
    line.id = "candidate-identity-line";
    line.className = "candidate-identity-line";

    const stage = document.createElement("span");
    stage.id = "focus-stage-pill";
    stage.className = "candidate-identity-pill";

    const doi = document.createElement("a");
    doi.id = "focus-doi-pill";
    doi.className = "candidate-identity-pill";
    doi.target = "_blank";
    doi.rel = "noopener noreferrer";

    line.append(stage, doi);
    byline.insertAdjacentElement("afterend", line);
    return line;
  }

  function syncIdentityLine() {
    const line = ensureIdentityLine();
    if (!line) return;

    const stage = byId("selected-candidate-stage")?.textContent?.trim() || "";
    const stagePill = byId("focus-stage-pill");
    if (stagePill) {
      stagePill.textContent = stage && stage !== "—" ? stage : "Stage non registrato";
      stagePill.hidden = !stage || stage === "—";
    }

    const doiText = byId("selected-candidate-doi")?.textContent?.trim() || "";
    const doiLink = byId("selected-candidate-doi-link");
    const doiPill = byId("focus-doi-pill");
    if (!doiPill) return;
    if (doiText && doiText !== "—" && doiLink?.href) {
      doiPill.textContent = doiText;
      doiPill.href = doiLink.href;
      doiPill.hidden = false;
    } else {
      doiPill.hidden = true;
      doiPill.removeAttribute("href");
    }
  }

  function ensureEvidenceDetails() {
    const panel = document.querySelector(".candidate-decision-panel");
    if (!panel) return null;
    let details = byId("candidate-evidence-details");
    if (details) return details;

    details = document.createElement("details");
    details.id = "candidate-evidence-details";
    details.className = "candidate-evidence-details";
    details.hidden = true;

    const summary = document.createElement("summary");
    summary.textContent = "Dettagli e verifiche";

    const body = document.createElement("div");
    body.id = "candidate-evidence-body";
    body.className = "candidate-evidence-body";

    details.append(summary, body);
    panel.append(details);
    return details;
  }

  function moveIfPresent(target, node) {
    if (!target || !node || target.contains(node)) return;
    target.append(node);
  }

  function organizePaper() {
    setFocusMode();

    const detail = byId("candidate-detail");
    const form = byId("decision-form");
    if (!detail || !form) return;

    const heading = detail.querySelector(".candidate-detail-heading");
    const abstractPanel = byId("candidate-abstract-panel");
    if (heading && abstractPanel && abstractPanel.parentElement === detail) {
      heading.insertAdjacentElement("afterend", abstractPanel);
    }

    const parent = detail.parentElement;
    if (parent && detail.nextElementSibling !== form) {
      detail.insertAdjacentElement("afterend", form);
    }

    syncIdentityLine();

    const details = ensureEvidenceDetails();
    const body = byId("candidate-evidence-body");
    if (!details || !body) return;

    moveIfPresent(body, detail.querySelector(".candidate-metadata"));
    moveIfPresent(body, byId("candidate-consensus-panel"));
    moveIfPresent(body, byId("candidate-assisted-resolution-panel"));
    moveIfPresent(body, byId("candidate-reading-aid-panel"));
    moveIfPresent(body, byId("candidate-review-guidance-panel"));
    moveIfPresent(body, detail.querySelector(".candidate-provenance-details"));

    const candidateVisible = !detail.hidden;
    details.hidden = !candidateVisible;
    if (!candidateVisible) details.open = false;
  }

  function scheduleOrganize() {
    if (scheduled) return;
    scheduled = true;
    queueMicrotask(() => {
      scheduled = false;
      organizePaper();
    });
  }

  function observe() {
    const root = byId("editorial-app") || document.body;
    const observer = new MutationObserver(scheduleOrganize);
    observer.observe(root, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["hidden", "href"],
    });
  }

  function initialise() {
    organizePaper();
    observe();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialise, { once: true });
  } else {
    initialise();
  }
})();
