"use strict";

const GITHUB_API = "https://api.github.com";
const GITHUB_OAUTH = "https://github.com/login/oauth";
const API_VERSION = "2026-03-10";
const MAX_TEXT_LENGTH = 2000;
const SESSION_SECONDS = 8 * 60 * 60;
const STATE_SECONDS = 10 * 60;

const DECISIONS = new Set([
  "eligible_core",
  "eligible_contextual",
  "maybe_full_text_needed",
  "not_eligible",
  "duplicate",
  "not_academic",
  "not_retrievable",
]);
const STAGES = new Set(["title_abstract", "full_text", "seed_validation"]);
const CONFIDENCE = new Set(["high", "medium", "low"]);
const SPECIAL_REASONS = {
  duplicate: "DUPLICATE_RECORD",
  not_academic: "NOT_ACADEMIC_SOURCE",
  not_retrievable: "FULL_TEXT_UNAVAILABLE",
};
const NON_ELIGIBLE_REASONS = new Set([
  "TOPIC_OFF_SCOPE",
  "NO_CRIMINAL_ACTOR_OR_INTEREST",
  "NO_LEGAL_ECONOMY_LINK",
  "NO_INFILTRATION_RELATION",
  "MENTION_ONLY_NOT_ANALYTICAL",
  "ADJACENT_PHENOMENON_ONLY",
  "CRIME_DOMAIN_MISMATCH",
  "DOCUMENT_TYPE_EXCLUDED",
  "LANGUAGE_EXCLUDED",
]);
const INPUT_FIELDS = new Set([
  "candidateId",
  "candidateIssueNumber",
  "screeningStage",
  "decision",
  "exclusionReasonCode",
  "topicCode",
  "duplicateTarget",
  "confidence",
  "evidence",
  "rationale",
  "confirmed",
  "submissionId",
]);

class CuratorAppError extends Error {
  constructor(status, code, message) {
    super(message);
    this.name = "CuratorAppError";
    this.status = status;
    this.code = code;
  }
}

function requiredEnv(env, name) {
  const value = String(env[name] || "").trim();
  if (!value) {
    throw new CuratorAppError(503, "app_not_configured", "La GitHub App non è ancora configurata.");
  }
  return value;
}

function configuration(env) {
  const repository = requiredEnv(env, "GITHUB_REPOSITORY");
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository)) {
    throw new CuratorAppError(503, "invalid_configuration", "La configurazione del repository non è valida.");
  }
  const siteUrl = new URL(requiredEnv(env, "SITE_URL"));
  const callbackUrl = new URL(requiredEnv(env, "GITHUB_CALLBACK_URL"));
  if (siteUrl.protocol !== "https:" || callbackUrl.protocol !== "https:") {
    throw new CuratorAppError(503, "invalid_configuration", "Gli URL della GitHub App devono usare HTTPS.");
  }
  const repositoryId = requiredEnv(env, "GITHUB_REPOSITORY_ID");
  if (!/^\d+$/.test(repositoryId)) {
    throw new CuratorAppError(503, "invalid_configuration", "L'ID del repository non è valido.");
  }
  return {
    repository,
    repositoryId,
    siteUrl,
    siteOrigin: siteUrl.origin,
    callbackUrl,
    clientId: requiredEnv(env, "GITHUB_CLIENT_ID"),
    clientSecret: requiredEnv(env, "GITHUB_CLIENT_SECRET"),
    curatorLogin: requiredEnv(env, "CURATOR_LOGIN"),
    sessionSecret: requiredEnv(env, "SESSION_SECRET"),
  };
}

function base64Url(bytes) {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function decodeBase64(value, configurationValue = false) {
  const normalised = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalised + "=".repeat((4 - (normalised.length % 4)) % 4);
  let binary;
  try {
    binary = atob(padded);
  } catch {
    if (configurationValue) {
      throw new CuratorAppError(503, "invalid_configuration", "La chiave di sessione non è valida.");
    }
    throw new CuratorAppError(401, "invalid_session", "La sessione non è valida.");
  }
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

function randomToken(byteLength = 32) {
  const bytes = new Uint8Array(byteLength);
  crypto.getRandomValues(bytes);
  return base64Url(bytes);
}

async function encryptionKey(secret) {
  const bytes = decodeBase64(secret, true);
  if (bytes.byteLength !== 32) {
    throw new CuratorAppError(503, "invalid_configuration", "SESSION_SECRET deve contenere esattamente 32 byte.");
  }
  return crypto.subtle.importKey("raw", bytes, { name: "AES-GCM" }, false, ["encrypt", "decrypt"]);
}

async function seal(payload, secret) {
  const iv = new Uint8Array(12);
  crypto.getRandomValues(iv);
  const plaintext = new TextEncoder().encode(JSON.stringify(payload));
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    await encryptionKey(secret),
    plaintext,
  );
  return `${base64Url(iv)}.${base64Url(new Uint8Array(ciphertext))}`;
}

async function unseal(value, secret, purpose) {
  const parts = String(value || "").split(".");
  if (parts.length !== 2) {
    throw new CuratorAppError(401, "invalid_session", "La sessione non è valida.");
  }
  try {
    const plaintext = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: decodeBase64(parts[0]) },
      await encryptionKey(secret),
      decodeBase64(parts[1]),
    );
    const payload = JSON.parse(new TextDecoder().decode(plaintext));
    const now = Math.floor(Date.now() / 1000);
    if (!payload || payload.purpose !== purpose || !Number.isInteger(payload.exp) || payload.exp <= now) {
      throw new Error("expired or wrong-purpose token");
    }
    return payload;
  } catch (error) {
    if (error instanceof CuratorAppError && error.code === "invalid_configuration") throw error;
    throw new CuratorAppError(401, "invalid_session", "La sessione è scaduta o non è valida.");
  }
}

async function pkceChallenge(verifier) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return base64Url(new Uint8Array(digest));
}

function commonHeaders() {
  return {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
  };
}

function corsHeaders(request, config) {
  if (request.headers.get("Origin") !== config.siteOrigin) return {};
  return {
    "Access-Control-Allow-Origin": config.siteOrigin,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type, X-CSRF-Token, Idempotency-Key",
    "Access-Control-Max-Age": "600",
    Vary: "Origin",
  };
}

function jsonResponse(payload, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      ...commonHeaders(),
      "Content-Type": "application/json; charset=utf-8",
      ...extraHeaders,
    },
  });
}

function requireSiteOrigin(request, config) {
  if (request.headers.get("Origin") !== config.siteOrigin) {
    throw new CuratorAppError(403, "origin_not_allowed", "Origine della richiesta non autorizzata.");
  }
}

function siteRedirect(config, parameters = {}, fragment = {}) {
  const target = new URL(config.siteUrl);
  for (const [key, value] of Object.entries(parameters)) {
    if (value) target.searchParams.set(key, value);
  }
  const hash = new URLSearchParams();
  for (const [key, value] of Object.entries(fragment)) {
    if (value) hash.set(key, value);
  }
  target.hash = hash.toString();
  return new Response(null, {
    status: 302,
    headers: { ...commonHeaders(), Location: target.toString() },
  });
}

async function githubRequest(path, token, init = {}) {
  const headers = {
    Accept: "application/vnd.github+json",
    Authorization: `Bearer ${token}`,
    "X-GitHub-Api-Version": API_VERSION,
    "User-Agent": "criminal-infiltration-curator-app",
    ...(init.headers || {}),
  };
  const response = await fetch(`${GITHUB_API}${path}`, { ...init, headers });
  if (!response.ok) {
    if (response.status === 401) {
      throw new CuratorAppError(401, "github_session_expired", "La sessione GitHub è scaduta.");
    }
    if (response.status === 403) {
      throw new CuratorAppError(403, "github_permission_denied", "La GitHub App non dispone dei permessi richiesti.");
    }
    if (response.status === 404) {
      throw new CuratorAppError(404, "github_resource_not_found", "La risorsa GitHub richiesta non è accessibile.");
    }
    throw new CuratorAppError(502, "github_api_error", "GitHub non ha completato la richiesta.");
  }
  if (response.status === 204) return null;
  return response.json();
}

async function revokeToken(config, token) {
  const credentials = btoa(`${config.clientId}:${config.clientSecret}`);
  try {
    await fetch(`${GITHUB_API}/applications/${encodeURIComponent(config.clientId)}/token`, {
      method: "DELETE",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Basic ${credentials}`,
        "X-GitHub-Api-Version": API_VERSION,
        "Content-Type": "application/json",
        "User-Agent": "criminal-infiltration-curator-app",
      },
      body: JSON.stringify({ access_token: token }),
    });
  } catch {
    // Logout remains local even if GitHub is temporarily unavailable. The token
    // is short lived and is removed from the browser by the caller.
  }
}

async function startLogin(request, config) {
  const requestUrl = new URL(request.url);
  const candidate = String(requestUrl.searchParams.get("candidate") || "").trim();
  if (candidate && !validCandidateId(candidate)) {
    throw new CuratorAppError(400, "invalid_candidate", "Il candidate ID non è valido.");
  }
  const verifier = randomToken(32);
  const now = Math.floor(Date.now() / 1000);
  const state = await seal(
    {
      purpose: "oauth-state",
      exp: now + STATE_SECONDS,
      nonce: randomToken(24),
      verifier,
      candidate,
    },
    config.sessionSecret,
  );
  const target = new URL(`${GITHUB_OAUTH}/authorize`);
  target.searchParams.set("client_id", config.clientId);
  target.searchParams.set("redirect_uri", config.callbackUrl.toString());
  target.searchParams.set("state", state);
  target.searchParams.set("code_challenge", await pkceChallenge(verifier));
  target.searchParams.set("code_challenge_method", "S256");
  target.searchParams.set("login", config.curatorLogin);
  return new Response(null, {
    status: 302,
    headers: { ...commonHeaders(), Location: target.toString() },
  });
}

async function exchangeCode(config, code, verifier) {
  const body = new URLSearchParams({
    client_id: config.clientId,
    client_secret: config.clientSecret,
    code,
    redirect_uri: config.callbackUrl.toString(),
    code_verifier: verifier,
    repository_id: config.repositoryId,
  });
  const response = await fetch(`${GITHUB_OAUTH}/access_token`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/x-www-form-urlencoded",
      "User-Agent": "criminal-infiltration-curator-app",
    },
    body,
  });
  if (!response.ok) {
    throw new CuratorAppError(502, "oauth_exchange_failed", "GitHub non ha completato l'autenticazione.");
  }
  const payload = await response.json();
  if (
    payload.error ||
    typeof payload.access_token !== "string" ||
    !payload.access_token.startsWith("ghu_") ||
    !Number.isInteger(payload.expires_in) ||
    payload.expires_in <= 0
  ) {
    throw new CuratorAppError(502, "oauth_exchange_failed", "GitHub non ha restituito una sessione temporanea valida.");
  }
  return payload;
}

async function finishLogin(request, config) {
  const url = new URL(request.url);
  if (url.searchParams.get("error")) {
    return siteRedirect(config, { auth_error: "authorization_denied" });
  }
  const code = String(url.searchParams.get("code") || "");
  const stateValue = String(url.searchParams.get("state") || "");
  if (!code || !stateValue) {
    throw new CuratorAppError(400, "oauth_callback_invalid", "La risposta di autenticazione è incompleta.");
  }
  const state = await unseal(stateValue, config.sessionSecret, "oauth-state");
  const tokenData = await exchangeCode(config, code, state.verifier);
  const token = tokenData.access_token;
  const user = await githubRequest("/user", token);
  const login = String(user?.login || "");
  if (login.toLowerCase() !== config.curatorLogin.toLowerCase()) {
    await revokeToken(config, token);
    throw new CuratorAppError(403, "curator_not_authorized", "Questo account non è autorizzato alla curatela.");
  }
  const repository = await githubRequest(`/repos/${config.repository}`, token);
  if (
    String(repository?.full_name || "").toLowerCase() !== config.repository.toLowerCase() ||
    String(repository?.id || "") !== config.repositoryId
  ) {
    await revokeToken(config, token);
    throw new CuratorAppError(403, "app_not_installed", "La GitHub App non è installata sul repository previsto.");
  }
  const now = Math.floor(Date.now() / 1000);
  const expiresIn = Math.min(Number(tokenData.expires_in), SESSION_SECONDS);
  const csrf = randomToken(24);
  const session = await seal(
    {
      purpose: "curator-session",
      exp: now + expiresIn,
      token,
      login,
      userId: Number(user.id),
      csrf,
    },
    config.sessionSecret,
  );
  return siteRedirect(
    config,
    { candidate: state.candidate || "" },
    { curator_session: session, curator_csrf: csrf },
  );
}

function bearerToken(request) {
  const header = String(request.headers.get("Authorization") || "");
  const match = header.match(/^Bearer\s+(.+)$/i);
  if (!match) {
    throw new CuratorAppError(401, "authentication_required", "Accedi con GitHub per continuare.");
  }
  return match[1];
}

async function authenticatedSession(request, config, requireCsrf = false) {
  const sealed = bearerToken(request);
  const session = await unseal(sealed, config.sessionSecret, "curator-session");
  if (String(session.login).toLowerCase() !== config.curatorLogin.toLowerCase()) {
    throw new CuratorAppError(403, "curator_not_authorized", "Questo account non è autorizzato alla curatela.");
  }
  if (requireCsrf && request.headers.get("X-CSRF-Token") !== session.csrf) {
    throw new CuratorAppError(403, "csrf_check_failed", "La conferma di sicurezza non è valida.");
  }
  return { ...session, sealed };
}

function validCandidateId(value) {
  return /^[A-Z0-9][A-Z0-9-]{2,59}$/.test(String(value || ""));
}

function stripMarkdown(value) {
  return String(value || "")
    .replace(/\\\|/g, "|")
    .replace(/\[([^\]]+)\]\((https?:\/\/.*)\)/g, "$1")
    .replace(/^<([^>]+)>$/, "$1")
    .replace(/\*\*/g, "")
    .replace(/^`|`$/g, "")
    .trim();
}

function parseCandidateIssue(issue) {
  const body = String(issue?.body || "");
  const marker = body.match(/<!--\s*curator-candidate:([A-Z0-9-]+)\s*-->/);
  if (!marker || !validCandidateId(marker[1])) return null;
  const fields = {};
  for (const line of body.split("\n")) {
    const row = line.match(/^\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|$/);
    if (!row || row[1].trim() === "---") continue;
    fields[row[1].trim()] = stripMarkdown(row[2]);
  }
  if (fields["Candidate ID"] !== marker[1] || !fields.Title) return null;
  const doiRow = body.split("\n").find((line) => line.startsWith("| DOI |")) || "";
  const doiMatch = doiRow.match(/\]\((https:\/\/doi\.org\/.+)\)\s*\|$/);
  const provenance = [];
  let inProvenance = false;
  let provenanceKind = "unknown";
  for (const line of body.split("\n")) {
    if (line.startsWith("## Pilot provenance")) {
      inProvenance = true;
      provenanceKind = "legacy";
      continue;
    }
    if (line.startsWith("## Daily intake provenance")) {
      inProvenance = true;
      provenanceKind = "daily";
      continue;
    }
    if (inProvenance && line.startsWith("## ")) break;
    if (!inProvenance) continue;
    const bullet = line.match(/^- ([^:]+):\s*(.*)$/);
    if (bullet) provenance.push({ label: bullet[1].trim(), value: stripMarkdown(bullet[2]) });
  }
  const labels = Array.isArray(issue.labels)
    ? issue.labels.map((label) => (typeof label === "string" ? label : label?.name)).filter(Boolean)
    : [];
  return {
    candidateId: marker[1],
    issueNumber: Number(issue.number),
    issueUrl: String(issue.html_url || ""),
    title: fields.Title,
    authors: fields.Authors || "",
    year: fields.Year || "",
    venue: fields.Venue || "",
    doi: fields.DOI === "Not recorded" ? "" : fields.DOI || "",
    doiUrl: doiMatch ? doiMatch[1] : "",
    source: fields.Source || "",
    reviewStage: fields["Current review stage"] || "",
    stageLabel: labels.find((label) => label.startsWith("stage:")) || "",
    provenanceKind,
    provenance,
  };
}

async function listCandidates(config, token) {
  const candidates = [];
  for (let page = 1; page <= 10; page += 1) {
    const query = new URLSearchParams({
      state: "open",
      labels: "curation:queue",
      per_page: "100",
      page: String(page),
      sort: "created",
      direction: "asc",
    });
    const issues = await githubRequest(`/repos/${config.repository}/issues?${query}`, token);
    if (!Array.isArray(issues)) {
      throw new CuratorAppError(502, "github_api_error", "GitHub ha restituito una coda non valida.");
    }
    for (const issue of issues) {
      if (issue.pull_request) continue;
      const candidate = parseCandidateIssue(issue);
      if (candidate) candidates.push(candidate);
    }
    if (issues.length < 100) break;
  }
  candidates.sort((left, right) => left.issueNumber - right.issueNumber);
  return candidates;
}

function textField(value, label, maximum = MAX_TEXT_LENGTH) {
  const clean = String(value || "").trim();
  if (!clean) throw new CuratorAppError(422, "invalid_decision", `${label} è obbligatorio.`);
  if (clean.length > maximum) {
    throw new CuratorAppError(422, "invalid_decision", `${label} supera ${maximum} caratteri.`);
  }
  if (/(^|\n)###\s|<!--\s*curator-/i.test(clean)) {
    throw new CuratorAppError(422, "invalid_decision", `${label} contiene una sintassi riservata.`);
  }
  return clean;
}

function optionalField(value, label, maximum = 100) {
  const clean = String(value || "").trim();
  if (clean.length > maximum || /[\r\n]/.test(clean)) {
    throw new CuratorAppError(422, "invalid_decision", `${label} non è valido.`);
  }
  return clean;
}

function validateDecision(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    throw new CuratorAppError(400, "invalid_json", "La decisione non è un oggetto JSON valido.");
  }
  const unknown = Object.keys(input).filter((key) => !INPUT_FIELDS.has(key));
  if (unknown.length) {
    throw new CuratorAppError(400, "unknown_fields", "La richiesta contiene campi non previsti.");
  }
  const candidateId = optionalField(input.candidateId, "Candidate ID", 60);
  if (!validCandidateId(candidateId)) {
    throw new CuratorAppError(422, "invalid_decision", "Il candidate ID non è valido.");
  }
  const issueNumber = Number(input.candidateIssueNumber);
  if (!Number.isInteger(issueNumber) || issueNumber <= 0) {
    throw new CuratorAppError(422, "invalid_decision", "La scheda GitHub del candidato non è valida.");
  }
  const screeningStage = optionalField(input.screeningStage, "Stage", 40);
  const decision = optionalField(input.decision, "Decisione", 50);
  const confidence = optionalField(input.confidence, "Confidenza", 20);
  if (!STAGES.has(screeningStage) || !DECISIONS.has(decision) || !CONFIDENCE.has(confidence)) {
    throw new CuratorAppError(422, "invalid_decision", "Stage, decisione o confidenza non sono validi.");
  }
  let exclusionReasonCode = optionalField(input.exclusionReasonCode, "Motivo di esclusione", 80);
  const topicCode = optionalField(input.topicCode, "Tema", 80);
  const duplicateTarget = optionalField(input.duplicateTarget, "Duplicato prevalente", 60);
  if (input.confirmed !== true) {
    throw new CuratorAppError(422, "confirmation_required", "La conferma esplicita è obbligatoria.");
  }
  const submissionId = optionalField(input.submissionId, "Submission ID", 40);
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(submissionId)) {
    throw new CuratorAppError(422, "invalid_decision", "Il submission ID non è valido.");
  }
  if (decision === "eligible_core" || decision === "eligible_contextual") {
    if (!/^[a-z][a-z0-9_]{1,79}$/.test(topicCode) || exclusionReasonCode || duplicateTarget) {
      throw new CuratorAppError(422, "invalid_decision", "Una decisione eleggibile richiede un solo tema governato.");
    }
  } else if (decision === "maybe_full_text_needed") {
    if (topicCode || exclusionReasonCode || duplicateTarget) {
      throw new CuratorAppError(422, "invalid_decision", "Il rinvio al full text non ammette tema, esclusione o duplicato.");
    }
  } else if (decision === "duplicate") {
    if (!validCandidateId(duplicateTarget) && !/^P\d{6}$/.test(duplicateTarget)) {
      throw new CuratorAppError(422, "invalid_decision", "Indica il candidato o paper che sopravvive.");
    }
    if (duplicateTarget === candidateId) {
      throw new CuratorAppError(422, "invalid_decision", "Un candidato non può essere duplicato di se stesso.");
    }
    if (topicCode || (exclusionReasonCode && exclusionReasonCode !== SPECIAL_REASONS.duplicate)) {
      throw new CuratorAppError(422, "invalid_decision", "La decisione di duplicato contiene campi incompatibili.");
    }
    exclusionReasonCode = SPECIAL_REASONS.duplicate;
  } else {
    const expected = SPECIAL_REASONS[decision];
    if (expected && exclusionReasonCode !== expected) {
      throw new CuratorAppError(422, "invalid_decision", `${decision} richiede ${expected}.`);
    }
    if (decision === "not_eligible" && !NON_ELIGIBLE_REASONS.has(exclusionReasonCode)) {
      throw new CuratorAppError(422, "invalid_decision", "Scegli un motivo governato coerente con not_eligible.");
    }
    if (topicCode || duplicateTarget) {
      throw new CuratorAppError(422, "invalid_decision", "Una decisione di esclusione non può assegnare tema o duplicato.");
    }
  }
  return {
    candidateId,
    candidateIssueNumber: issueNumber,
    screeningStage,
    decision,
    exclusionReasonCode,
    topicCode,
    duplicateTarget,
    confidence,
    evidence: textField(input.evidence, "La base di evidenza"),
    rationale: textField(input.rationale, "La motivazione"),
    submissionId,
  };
}

function decisionIssueBody(values) {
  const sections = [
    ["Candidate ID", values.candidateId],
    ["Screening stage", values.screeningStage],
    ["Decision", values.decision],
    ["Exclusion reason", values.exclusionReasonCode || "NOT_APPLICABLE"],
    ["Topic code", values.topicCode || "_No response_"],
    ["Duplicate target", values.duplicateTarget || "_No response_"],
    ["Confidence", values.confidence],
    ["Evidence basis and locator", values.evidence],
    ["Record-specific rationale", values.rationale],
    ["Confirmation", "APPLY"],
  ];
  return [
    `<!-- curator-submission:${values.submissionId} -->`,
    `<!-- curator-source-issue:${values.candidateIssueNumber} -->`,
    ...sections.map(([label, value]) => `### ${label}\n\n${value}`),
  ].join("\n\n");
}

async function verifyCandidate(config, token, values) {
  const issue = await githubRequest(
    `/repos/${config.repository}/issues/${values.candidateIssueNumber}`,
    token,
  );
  const labels = Array.isArray(issue?.labels)
    ? issue.labels.map((label) => (typeof label === "string" ? label : label?.name))
    : [];
  const marker = `<!-- curator-candidate:${values.candidateId} -->`;
  if (
    issue?.pull_request ||
    issue?.state !== "open" ||
    !labels.includes("curation:queue") ||
    !String(issue?.body || "").includes(marker)
  ) {
    throw new CuratorAppError(409, "candidate_stale", "La scheda non è più aperta o non corrisponde al candidato selezionato.");
  }
}

async function findSubmission(config, token, login, submissionId) {
  const query = new URLSearchParams({
    state: "all",
    labels: "curation:decision",
    creator: login,
    per_page: "100",
    sort: "created",
    direction: "desc",
  });
  const issues = await githubRequest(`/repos/${config.repository}/issues?${query}`, token);
  const marker = `<!-- curator-submission:${submissionId} -->`;
  return Array.isArray(issues)
    ? issues.find((issue) => !issue.pull_request && String(issue.body || "").includes(marker)) || null
    : null;
}

async function createDecision(config, session, input) {
  const values = validateDecision(input);
  const existing = await findSubmission(config, session.token, session.login, values.submissionId);
  if (existing) {
    return { issueNumber: Number(existing.number), issueUrl: String(existing.html_url), replayed: true };
  }
  await verifyCandidate(config, session.token, values);
  const issue = await githubRequest(`/repos/${config.repository}/issues`, session.token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: `[CURATOR] ${values.candidateId}`,
      body: decisionIssueBody(values),
      labels: ["curation:decision"],
    }),
  });
  return { issueNumber: Number(issue.number), issueUrl: String(issue.html_url), replayed: false };
}

async function readJson(request) {
  const type = String(request.headers.get("Content-Type") || "").split(";", 1)[0].trim();
  if (type !== "application/json") {
    throw new CuratorAppError(415, "json_required", "La richiesta deve usare application/json.");
  }
  const length = Number(request.headers.get("Content-Length") || 0);
  if (length > 25000) {
    throw new CuratorAppError(413, "request_too_large", "La richiesta è troppo grande.");
  }
  try {
    return await request.json();
  } catch {
    throw new CuratorAppError(400, "invalid_json", "Il contenuto JSON non è valido.");
  }
}

async function handleApi(request, config, path) {
  requireSiteOrigin(request, config);
  const cors = corsHeaders(request, config);
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: { ...commonHeaders(), ...cors } });
  if (path === "/api/session" && request.method === "GET") {
    const session = await authenticatedSession(request, config);
    const user = await githubRequest("/user", session.token);
    if (String(user?.login || "").toLowerCase() !== config.curatorLogin.toLowerCase()) {
      throw new CuratorAppError(403, "curator_not_authorized", "Questo account non è autorizzato alla curatela.");
    }
    return jsonResponse(
      { user: { login: session.login, id: session.userId }, expiresAt: session.exp },
      200,
      cors,
    );
  }
  if (path === "/api/candidates" && request.method === "GET") {
    const session = await authenticatedSession(request, config);
    return jsonResponse({ candidates: await listCandidates(config, session.token) }, 200, cors);
  }
  if (path === "/api/decisions" && request.method === "POST") {
    const session = await authenticatedSession(request, config, true);
    const values = await readJson(request);
    const headerKey = String(request.headers.get("Idempotency-Key") || "");
    if (headerKey !== values.submissionId) {
      throw new CuratorAppError(400, "idempotency_mismatch", "La chiave di invio non corrisponde alla decisione.");
    }
    const result = await createDecision(config, session, values);
    return jsonResponse(result, result.replayed ? 200 : 201, cors);
  }
  if (path === "/auth/logout" && request.method === "POST") {
    const session = await authenticatedSession(request, config, true);
    await revokeToken(config, session.token);
    return jsonResponse({ loggedOut: true }, 200, cors);
  }
  throw new CuratorAppError(404, "route_not_found", "Endpoint non disponibile.");
}

async function route(request, env) {
  const url = new URL(request.url);
  if (url.pathname === "/health" && request.method === "GET") {
    let configured = true;
    try {
      configuration(env);
    } catch {
      configured = false;
    }
    return jsonResponse({ status: configured ? "ok" : "configuration_required" }, configured ? 200 : 503);
  }
  const config = configuration(env);
  if (url.pathname === "/auth/login" && request.method === "GET") return startLogin(request, config);
  if (url.pathname === "/auth/callback" && request.method === "GET") return finishLogin(request, config);
  if (url.pathname.startsWith("/api/") || url.pathname === "/auth/logout") {
    return handleApi(request, config, url.pathname);
  }
  throw new CuratorAppError(404, "route_not_found", "Endpoint non disponibile.");
}

export {
  CuratorAppError,
  decisionIssueBody,
  parseCandidateIssue,
  route,
  seal,
  unseal,
  validateDecision,
};

export default {
  async fetch(request, env) {
    let config;
    try {
      config = configuration(env);
    } catch {
      config = null;
    }
    try {
      return await route(request, env);
    } catch (error) {
      const known = error instanceof CuratorAppError;
      const status = known ? error.status : 500;
      const code = known ? error.code : "internal_error";
      const message = known ? error.message : "La GitHub App ha interrotto la richiesta in sicurezza.";
      const url = new URL(request.url);
      if (config && url.pathname === "/auth/callback") {
        return siteRedirect(config, { auth_error: code });
      }
      const cors = config ? corsHeaders(request, config) : {};
      return jsonResponse({ error: { code, message } }, status, cors);
    }
  },
};
