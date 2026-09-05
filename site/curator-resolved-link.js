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
