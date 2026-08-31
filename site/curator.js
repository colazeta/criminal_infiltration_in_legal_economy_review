"use strict";

const byId = (id) => document.getElementById(id);
const SESSION_KEY = "criminal-infiltration-curator-session";
const CSRF_KEY = "criminal-infiltration-curator-csrf";
const config = window.CURATOR_APP_CONFIG || {};

const state = {
  apiBaseUrl: normaliseApiBase(config.apiBaseUrl),
  secureAppUrl: normaliseAppUrl(config.secureAppUrl),
  token: "",
  csrf: "",
  user: null,
  options: null,
  candidates: [],
  selected: null,
};

function setText(id, value) {
  const element = byId(id);
  if (element) element.textContent = value;
}

function setHidden(id, hidden) {
  const element = byId(id);
  if (element) element.hidden = hidden;
}

function normaliseApiBase(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  try {
    const parsed = new URL(raw);
    const local = parsed.protocol === "http:" && ["127.0.0.1", "localhost"].includes(parsed.hostname);
    if (parsed.protocol !== "https:" && !local) return "";
    return parsed.origin;
  } catch {
    return "";
  }
}

function normaliseAppUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  try {
    const parsed = new URL(raw);
    const local = parsed.protocol === "http:" && ["127.0.0.1", "localhost"].includes(parsed.hostname);
    if (parsed.protocol !== "https:" && !local) return "";
    parsed.hash = "";
    return parsed.toString();
  } catch {
    return "";
  }
}

function safeUrl(value, allowedOrigins) {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" && allowedOrigins.includes(parsed.origin) ? parsed.toString() : "";
  } catch {
    return "";
  }
}

function formatDate(value) {
  if (!value) return "Nessuna esecuzione registrata";
  const parsed = new Date(`${value}T00:00:00Z`);
  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}

function renderQueue(stats) {
  const counts = stats.byStage || {};
  const origins = stats.openByOrigin || {};
  setText("queue-total", Number(stats.open || 0));
  setText("queue-metadata", Number(counts.metadataFix || 0));
  setText("queue-manual", Number(counts.manualReview || 0));
  setText("queue-abstract", Number(counts.abstractReview || 0));
  setText("queue-legacy-rejected", Number(counts.legacyRejectionReview || 0));
  setText(
    "queue-origin-summary",
    `${Number(origins.legacy || 0)} legacy · ${Number(origins.daily || 0)} da intake · ${Number(stats.completed || 0)} completate`,
  );
}

function renderRun(metrics) {
  const status = metrics.summary?.lastRunStatus;
  const labels = { completed: "Completata", partial: "Parziale", failed: "Fallita" };
  setText("last-run-status", labels[status] || "Non ancora eseguita");
  setText("last-run-date", formatDate(metrics.dataThrough));
  const dot = byId("run-health-dot");
  if (dot) dot.dataset.status = status || "none";
}

function renderAggregateUnavailable() {
  for (const id of [
    "queue-total",
    "queue-metadata",
    "queue-manual",
    "queue-abstract",
    "queue-legacy-rejected",
    "queue-origin-summary",
  ]) {
    setText(id, "n.d.");
  }
  setText("last-run-status", "Dati non disponibili");
  setText("last-run-date", "Riprova o consulta GitHub Actions");
}

function storageGet(key) {
  try {
    return sessionStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

function storageSet(key, value) {
  try {
    if (value) sessionStorage.setItem(key, value);
    else sessionStorage.removeItem(key);
  } catch {
    // A private browsing policy may disable storage; the in-memory session still works.
  }
}

function clearSession() {
  state.token = "";
  state.csrf = "";
  state.user = null;
  storageSet(SESSION_KEY, "");
  storageSet(CSRF_KEY, "");
}

function consumeAuthenticationFragment() {
  const fragment = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const token = fragment.get("curator_session") || "";
  const csrf = fragment.get("curator_csrf") || "";
  if (token && csrf) {
    state.token = token;
    state.csrf = csrf;
    storageSet(SESSION_KEY, token);
    storageSet(CSRF_KEY, csrf);
  } else {
    state.token = storageGet(SESSION_KEY);
    state.csrf = storageGet(CSRF_KEY);
  }
  if (window.location.hash) {
    history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
  }
}

function authErrorCopy(code) {
  const messages = {
    authorization_denied: "Autorizzazione GitHub annullata.",
    curator_not_authorized: "L’account GitHub utilizzato non è autorizzato alla curatela.",
    app_not_installed: "La GitHub App non risulta installata su questo repository.",
    invalid_session: "La procedura di accesso è scaduta. Avviala nuovamente.",
  };
  return messages[code] || "L’accesso GitHub non è stato completato.";
}

function consumeAuthenticationError() {
  const url = new URL(window.location.href);
  const code = url.searchParams.get("auth_error");
  if (!code) return;
  showAppMessage(authErrorCopy(code), "error");
  url.searchParams.delete("auth_error");
  history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
}

function loginUrl() {
  if (!state.apiBaseUrl) return "";
  const target = new URL(`${state.apiBaseUrl}/auth/login`);
  const requestedCandidate = new URL(window.location.href).searchParams.get("candidate");
  if (requestedCandidate) target.searchParams.set("candidate", requestedCandidate);
  return target.toString();
}

function secureWorkspaceUrl() {
  if (!state.secureAppUrl) return "";
  const target = new URL(state.secureAppUrl);
  const requestedCandidate = new URL(window.location.href).searchParams.get("candidate");
  if (requestedCandidate) target.searchParams.set("candidate", requestedCandidate);
  return target.toString();
}

function configureSecureWorkspaceLink() {
  const target = secureWorkspaceUrl();
  const link = byId("curator-secure-app");
  if (link) {
    link.hidden = !target;
    if (target) link.href = target;
    else link.removeAttribute("href");
  }
  if (target) {
    setText("curator-unavailable-title", "Apri la console curatoriale isolata");
    setText(
      "curator-unavailable-copy",
      "La sessione autenticata vive su un’origine dedicata. La pagina pubblica non riceve bearer, token anti-CSRF o metadati dei candidati.",
    );
  }
}

function showAppMessage(message, kind = "info", link = null) {
  const host = byId("curator-app-message");
  if (!host) return;
  host.replaceChildren();
  host.dataset.kind = kind;
  const text = document.createElement("p");
  text.textContent = message;
  host.append(text);
  if (link?.href && link?.label) {
    const anchor = document.createElement("a");
    anchor.href = link.href;
    anchor.textContent = link.label;
    anchor.rel = "noopener";
    host.append(anchor);
  }
  host.hidden = false;
}

function clearAppMessage() {
  const host = byId("curator-app-message");
  if (host) {
    host.replaceChildren();
    host.hidden = true;
    delete host.dataset.kind;
  }
}

async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.token) headers.set("Authorization", `Bearer ${state.token}`);
  const mutation = options.method && options.method !== "GET";
  if (mutation && state.csrf) headers.set("X-CSRF-Token", state.csrf);
  const response = await fetch(`${state.apiBaseUrl}${path}`, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401) clearSession();
    const error = new Error(payload.error?.message || "La GitHub App non ha completato la richiesta.");
    error.code = payload.error?.code || "request_failed";
    error.status = response.status;
    throw error;
  }
  return payload;
}

function setAuthenticationView(authenticated) {
  setHidden("curator-login-panel", authenticated || !state.apiBaseUrl);
  setHidden("curator-session-panel", !authenticated);
  setHidden("editorial-console", !authenticated);
  const login = byId("curator-login");
  if (login) login.href = loginUrl() || "#";
  if (authenticated) setText("curator-login-name", state.user?.login || "curatore");
}

function appendOptions(select, rows, placeholder) {
  select.replaceChildren();
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = placeholder;
  select.append(empty);
  for (const row of rows) {
    const option = document.createElement("option");
    option.value = row.code;
    option.textContent = `${row.label} · ${row.code}`;
    if (row.description || row.definition) option.title = row.description || row.definition;
    select.append(option);
  }
}

function initialiseFormOptions(options) {
  appendOptions(byId("screening-stage"), options.screeningStages, "Seleziona lo stage");
  appendOptions(byId("decision"), options.decisions, "Seleziona la decisione");
  appendOptions(byId("exclusion-reason"), options.exclusionReasons, "Seleziona il motivo");
  appendOptions(byId("topic-code"), options.topics, "Seleziona il tema");
  appendOptions(byId("confidence"), options.confidenceLevels, "Seleziona la confidenza");
}

function stageCode(candidate) {
  const map = {
    "stage:metadata-fix": "metadata_fix",
    "stage:manual-review": "manual_review",
    "stage:abstract-review": "abstract_full_text_review",
    "stage:legacy-rejection-review": "legacy_rejection_review",
  };
  return map[candidate.stageLabel] || "unknown";
}

function stageDisplay(candidate) {
  const labels = {
    metadata_fix: "Metadati",
    manual_review: "Revisione manuale",
    abstract_full_text_review: "Abstract / full text",
    legacy_rejection_review: "Rigetto legacy",
    unknown: "Da verificare",
  };
  return labels[stageCode(candidate)];
}

function candidateSearchText(candidate) {
  return [candidate.candidateId, candidate.title, candidate.authors, candidate.year, candidate.venue, candidate.doi]
    .join(" ")
    .toLocaleLowerCase("it");
}

function filteredCandidates() {
  const query = String(byId("candidate-search")?.value || "").trim().toLocaleLowerCase("it");
  const lane = String(byId("candidate-lane-filter")?.value || "");
  return state.candidates.filter((candidate) => {
    const searchMatch = !query || candidateSearchText(candidate).includes(query);
    const laneMatch = !lane || stageCode(candidate) === lane;
    return searchMatch && laneMatch;
  });
}

function candidateButton(candidate) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "candidate-card";
  button.dataset.selected = String(state.selected?.candidateId === candidate.candidateId);
  button.addEventListener("click", () => selectCandidate(candidate));
  const top = document.createElement("span");
  top.className = "candidate-card-top";
  const id = document.createElement("code");
  id.textContent = candidate.candidateId;
  const lane = document.createElement("small");
  lane.textContent = stageDisplay(candidate);
  top.append(id, lane);
  const title = document.createElement("strong");
  title.textContent = candidate.title;
  const meta = document.createElement("span");
  meta.className = "candidate-card-meta";
  meta.textContent = [candidate.authors, candidate.year].filter(Boolean).join(" · ") || "Metadati incompleti";
  button.append(top, title, meta);
  return button;
}

function renderCandidateList() {
  const host = byId("candidate-list");
  if (!host) return;
  const rows = filteredCandidates();
  host.replaceChildren(...rows.map(candidateButton));
  setText("candidate-result-count", `${rows.length} di ${state.candidates.length} schede aperte`);
  setHidden("candidate-list-empty", rows.length > 0);
}

function setLink(id, value, allowedOrigins) {
  const link = byId(id);
  if (!link) return;
  const safe = safeUrl(value, allowedOrigins);
  link.hidden = !safe;
  if (safe) link.href = safe;
  else link.removeAttribute("href");
}

function renderProvenance(candidate) {
  const list = byId("candidate-provenance");
  if (!list) return;
  list.replaceChildren();
  for (const item of candidate.provenance || []) {
    const row = document.createElement("div");
    const term = document.createElement("dt");
    const definition = document.createElement("dd");
    term.textContent = item.label;
    definition.textContent = item.value || "Non registrato";
    row.append(term, definition);
    list.append(row);
  }
}

function selectCandidate(candidate) {
  state.selected = candidate;
  setHidden("candidate-empty-state", true);
  setHidden("candidate-detail", false);
  setHidden("decision-form", false);
  setText("selected-candidate-id", candidate.candidateId);
  setText("selected-candidate-title", candidate.title);
  setText("selected-candidate-authors", candidate.authors || "Non registrati");
  setText("selected-candidate-year", candidate.year || "Non registrato");
  setText("selected-candidate-venue", candidate.venue || "Non registrata");
  setText("selected-candidate-doi", candidate.doi || "Non registrato");
  setText("selected-candidate-source", candidate.source || "Non registrata");
  setText("selected-candidate-stage", candidate.reviewStage || stageDisplay(candidate));
  setText("selected-provenance-kind", candidate.provenanceKind === "daily" ? "Intake giornaliero" : "Pilot legacy");
  setLink("selected-candidate-issue", candidate.issueUrl, ["https://github.com"]);
  setLink("selected-candidate-doi-link", candidate.doiUrl, ["https://doi.org"]);
  renderProvenance(candidate);
  resetDecisionForm();
  renderCandidateList();
  const url = new URL(window.location.href);
  url.searchParams.set("candidate", candidate.candidateId);
  history.replaceState(null, "", `${url.pathname}${url.search}`);
  byId("decision-form")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetDecisionForm() {
  const form = byId("decision-form");
  if (!form) return;
  form.reset();
  delete form.dataset.submissionId;
  setText("form-candidate-id", state.selected?.candidateId || "—");
  setHidden("decision-result", true);
  const submit = byId("submit-decision");
  if (submit) {
    submit.disabled = false;
    submit.textContent = "Invia la decisione";
  }
  updateConditionalFields();
}

function setGroup(id, enabled, required = false) {
  const group = byId(id);
  if (!group) return;
  group.hidden = !enabled;
  const control = group.querySelector("input, select, textarea");
  if (control) {
    control.disabled = !enabled;
    control.required = enabled && required;
  }
}

function setReasonAvailability(allowedCodes) {
  const select = byId("exclusion-reason");
  if (!select) return;
  for (const option of select.options) {
    if (!option.value) continue;
    const allowed = allowedCodes.has(option.value);
    option.hidden = !allowed;
    option.disabled = !allowed;
  }
}

function updateConditionalFields() {
  const decision = byId("decision")?.value || "";
  const reason = byId("exclusion-reason");
  const topic = byId("topic-code");
  const duplicate = byId("duplicate-target");
  const eligible = decision === "eligible_core" || decision === "eligible_contextual";
  const specialReasons = {
    duplicate: "DUPLICATE_RECORD",
    not_academic: "NOT_ACADEMIC_SOURCE",
    not_retrievable: "FULL_TEXT_UNAVAILABLE",
  };
  const nonEligibleCodes = new Set(
    (state.options?.exclusionReasons || [])
      .map((row) => row.code)
      .filter((code) => !Object.values(specialReasons).includes(code)),
  );
  setGroup("topic-field", eligible, eligible);
  setGroup("duplicate-field", decision === "duplicate", decision === "duplicate");
  const usesReason = decision === "not_eligible" || Object.hasOwn(specialReasons, decision);
  setGroup("exclusion-field", usesReason, usesReason);
  if (!eligible && topic) topic.value = "";
  if (decision !== "duplicate" && duplicate) duplicate.value = "";
  if (reason) {
    if (decision === "not_eligible") {
      setReasonAvailability(nonEligibleCodes);
      if (!nonEligibleCodes.has(reason.value)) reason.value = "";
      reason.disabled = false;
    } else if (Object.hasOwn(specialReasons, decision)) {
      const expected = specialReasons[decision];
      setReasonAvailability(new Set([expected]));
      reason.value = expected;
      reason.disabled = true;
      reason.required = false;
    } else {
      setReasonAvailability(new Set());
      reason.value = "";
    }
  }
}

function decisionPayload(form) {
  const submissionId = form.dataset.submissionId || crypto.randomUUID();
  form.dataset.submissionId = submissionId;
  return {
    candidateId: state.selected.candidateId,
    candidateIssueNumber: state.selected.issueNumber,
    screeningStage: byId("screening-stage").value,
    decision: byId("decision").value,
    exclusionReasonCode: byId("exclusion-reason").value,
    topicCode: byId("topic-code").value,
    duplicateTarget: byId("duplicate-target").value.trim(),
    confidence: byId("confidence").value,
    evidence: byId("evidence-basis").value.trim(),
    rationale: byId("decision-rationale").value.trim(),
    confirmed: byId("explicit-confirmation").checked,
    submissionId,
  };
}

async function submitDecision(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!state.selected || !form.reportValidity()) return;
  const payload = decisionPayload(form);
  const submit = byId("submit-decision");
  if (submit) {
    submit.disabled = true;
    submit.textContent = "Invio in corso…";
  }
  clearAppMessage();
  try {
    const result = await apiFetch("/api/decisions", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": payload.submissionId },
      body: JSON.stringify(payload),
    });
    const issueUrl = safeUrl(result.issueUrl, ["https://github.com"]);
    const resultHost = byId("decision-result");
    if (resultHost) {
      resultHost.replaceChildren();
      const title = document.createElement("strong");
      title.textContent = result.replayed ? "Decisione già registrata" : "Decisione inviata";
      const copy = document.createElement("p");
      copy.textContent = "GitHub sta validando l’istruzione e preparerà una pull request separata.";
      resultHost.append(title, copy);
      if (issueUrl) {
        const link = document.createElement("a");
        link.href = issueUrl;
        link.textContent = `Apri l’istruzione #${result.issueNumber} su GitHub →`;
        link.rel = "noopener";
        resultHost.append(link);
      }
      resultHost.hidden = false;
    }
    if (submit) submit.textContent = "Decisione registrata";
  } catch (error) {
    showAppMessage(error.message, "error");
    if (submit) {
      submit.disabled = false;
      submit.textContent = "Invia la decisione";
    }
    if (error.status === 401) {
      setAuthenticationView(false);
      setHidden("curator-login-panel", false);
    }
  }
}

async function loadCandidates() {
  setText("candidate-result-count", "Caricamento della coda…");
  const payload = await apiFetch("/api/candidates");
  state.candidates = Array.isArray(payload.candidates) ? payload.candidates : [];
  renderCandidateList();
  const requested = new URL(window.location.href).searchParams.get("candidate");
  const candidate = state.candidates.find((row) => row.candidateId === requested);
  if (candidate) selectCandidate(candidate);
}

async function restoreAuthentication() {
  if (!state.apiBaseUrl) {
    setHidden("curator-app-unavailable", false);
    setAuthenticationView(false);
    return;
  }
  setHidden("curator-app-unavailable", true);
  const login = byId("curator-login");
  if (login) login.href = loginUrl();
  if (!state.token || !state.csrf) {
    setAuthenticationView(false);
    return;
  }
  try {
    const session = await apiFetch("/api/session");
    state.user = session.user;
    setAuthenticationView(true);
    await loadCandidates();
  } catch (error) {
    clearSession();
    setAuthenticationView(false);
    setHidden("curator-login-panel", false);
    showAppMessage(error.message, "error");
  }
}

async function logout() {
  const button = byId("curator-logout");
  if (button) button.disabled = true;
  try {
    if (state.token && state.csrf) await apiFetch("/auth/logout", { method: "POST" });
  } catch {
    // The browser session is cleared even if revocation cannot reach GitHub.
  } finally {
    clearSession();
    state.candidates = [];
    state.selected = null;
    setAuthenticationView(false);
    setHidden("curator-login-panel", false);
    renderCandidateList();
    if (button) button.disabled = false;
    showAppMessage("Sessione curatoriale terminata.");
  }
}

function wireInterface() {
  byId("candidate-search")?.addEventListener("input", renderCandidateList);
  byId("candidate-lane-filter")?.addEventListener("change", renderCandidateList);
  byId("decision")?.addEventListener("change", updateConditionalFields);
  byId("decision-form")?.addEventListener("submit", submitDecision);
  byId("decision-form")?.addEventListener("input", (event) => {
    if (event.target.id !== "explicit-confirmation") delete event.currentTarget.dataset.submissionId;
  });
  byId("curator-logout")?.addEventListener("click", logout);
}

async function loadPublicData() {
  const [aggregateResult, optionsResult] = await Promise.allSettled([
    Promise.all([
      fetch("./data/curator-stats.json").then((response) => {
        if (!response.ok) throw new Error("curator statistics unavailable");
        return response.json();
      }),
      fetch("./data/research-stats.json").then((response) => {
        if (!response.ok) throw new Error("research statistics unavailable");
        return response.json();
      }),
    ]),
    fetch("./data/curator-options.json").then((response) => {
      if (!response.ok) throw new Error("curator options unavailable");
      return response.json();
    }),
  ]);
  if (aggregateResult.status === "fulfilled") {
    renderQueue(aggregateResult.value[0]);
    renderRun(aggregateResult.value[1]);
  } else {
    renderAggregateUnavailable();
  }
  if (optionsResult.status === "fulfilled") {
    state.options = optionsResult.value;
    initialiseFormOptions(state.options);
  } else {
    showAppMessage("I codici governati del modulo non sono disponibili. L’invio resta bloccato.", "error");
  }
}

async function initialise() {
  consumeAuthenticationFragment();
  consumeAuthenticationError();
  configureSecureWorkspaceLink();
  wireInterface();
  await loadPublicData();
  if (!state.options) return;
  await restoreAuthentication();
}

initialise();
