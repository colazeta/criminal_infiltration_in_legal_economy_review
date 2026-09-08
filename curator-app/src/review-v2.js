import { fetchWithTimeout } from "./network.js";
import { queryManifestProblem } from "./daily-source-policy.js";

export const CRITERIA = Object.freeze(["criminal_actor", "legal_economy", "sustained_relation", "substantive_analysis"]);
export const V2_PROTOCOL = "CILE-4PT-OA-v3";
export const V2_ONTOLOGY = "0.3.0";
const DECISIONS = new Set(["eligible_core", "eligible_contextual", "needs_full_text", "not_eligible", "duplicate", "not_academic", "not_retrievable"]);
const SCIENTIFIC_KINDS = new Set(["abstract", "full_text", "full_text_excerpt", "publisher_summary"]);
const EXCLUSION_REASONS = new Set(["TOPIC_OFF_SCOPE", "NO_CRIMINAL_ACTOR_OR_INTEREST", "NO_LEGAL_ECONOMY_LINK", "NO_INFILTRATION_RELATION", "MENTION_ONLY_NOT_ANALYTICAL", "ADJACENT_PHENOMENON_ONLY", "CRIME_DOMAIN_MISMATCH", "DOCUMENT_TYPE_EXCLUDED", "LANGUAGE_EXCLUDED", "DUPLICATE_RECORD", "NOT_ACADEMIC_SOURCE", "FULL_TEXT_UNAVAILABLE"]);

export class V2Error extends Error {
  constructor(code, status = 422) { super(code); this.code = code; this.status = status; }
}
export function canonicalJson(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
}
export async function sha256(value) {
  const bytes = typeof value === "string" ? new TextEncoder().encode(value) : value;
  return [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map((b) => b.toString(16).padStart(2, "0")).join("");
}
function text(value, label, limit = 6000) {
  if (typeof value !== "string" || !value.trim() || value.length > limit) throw new V2Error(`invalid_${label}`);
  return value.trim();
}
function exact(value, keys, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)
    || Object.keys(value).some((key) => !keys.includes(key)) || keys.some((key) => !(key in value))) throw new V2Error(`invalid_${label}_fields`);
}
function https(value) {
  const url = new URL(text(value, "source_url", 2000));
  if (url.protocol !== "https:" || url.username || url.password) throw new V2Error("invalid_source_url");
  return url.href;
}
export function validateProposal(input, { candidate, review, spans, actor, access }) {
  exact(input, ["proposal_id", "review_id", "candidate_id", "expected_version", "protocol_version", "decision", "stage", "confidence", "rationale", "exclusion_reason", "duplicate_target", "criteria", "supersedes_id", "access_assessment_id"], "proposal");
  if (!/^[a-zA-Z0-9-]{8,80}$/.test(input.proposal_id)) throw new V2Error("invalid_proposal_id");
  if (input.review_id !== review.review_id || input.candidate_id !== candidate.candidate_id || candidate.review_id !== review.review_id) throw new V2Error("review_mismatch");
  if (review.phase !== "active") throw new V2Error("review_not_active", 409);
  if (input.protocol_version !== review.protocol_version || input.protocol_version !== V2_PROTOCOL) throw new V2Error("protocol_mismatch", 409);
  if (input.expected_version !== candidate.record_version) throw new V2Error("stale_candidate", 409);
  if (!DECISIONS.has(input.decision) || !["title_abstract", "full_text", "seed_validation"].includes(input.stage)
    || !["low", "medium", "high"].includes(input.confidence)) throw new V2Error("invalid_decision");
  text(actor, "human_actor", 100); text(input.rationale, "rationale");
  if (!Array.isArray(input.criteria) || input.criteria.length !== 4 || new Set(input.criteria.map((c) => c.criterion_id)).size !== 4) throw new V2Error("four_criteria_required");
  for (const criterion of input.criteria) {
    exact(criterion, ["criterion_id", "outcome", "rationale", "evidence_span_ids"], "criterion");
    if (!CRITERIA.includes(criterion.criterion_id) || !["YES", "NO", "UNCERTAIN"].includes(criterion.outcome)) throw new V2Error("invalid_criterion");
    text(criterion.rationale, "criterion_rationale");
    if (!Array.isArray(criterion.evidence_span_ids) || criterion.evidence_span_ids.length > 12
      || new Set(criterion.evidence_span_ids).size !== criterion.evidence_span_ids.length) throw new V2Error("invalid_span_ids");
    if (criterion.outcome !== "UNCERTAIN" && !criterion.evidence_span_ids.length) throw new V2Error("evidence_required");
    for (const id of criterion.evidence_span_ids) {
      const span = spans.find((row) => row.span_id === id);
      if (!span || span.review_id !== input.review_id || span.candidate_id !== input.candidate_id
        || span.identity_state !== "verified" || !SCIENTIFIC_KINDS.has(span.evidence_kind)) throw new V2Error("unverified_or_non_source_evidence");
    }
  }
  if (["eligible_core", "eligible_contextual"].includes(input.decision) && (candidate.identity_state !== "verified" || !candidate.work_id)) throw new V2Error("identity_unresolved");
  if (["eligible_core", "eligible_contextual"].includes(input.decision) && (!access || access.access_status !== "verified_open" || access.review_id !== review.review_id || access.candidate_id !== candidate.candidate_id || input.access_assessment_id !== access.assessment_id)) throw new V2Error("current_open_access_assessment_required");
  if (input.access_assessment_id !== null) text(input.access_assessment_id, "access_assessment_id", 100);
  if (input.decision === "eligible_core" && input.criteria.some((c) => c.outcome !== "YES")) throw new V2Error("core_requires_four_yes");
  if (input.decision === "eligible_contextual" && !input.criteria.some((c) => c.evidence_span_ids.length)) throw new V2Error("contextual_evidence_required");
  if (input.decision === "not_eligible" && !input.criteria.some((c) => c.outcome === "NO")) throw new V2Error("exclusion_requires_supported_no");
  if (["not_eligible", "not_academic", "not_retrievable", "duplicate"].includes(input.decision)) {
    if (!EXCLUSION_REASONS.has(input.exclusion_reason)) throw new V2Error("controlled_exclusion_reason_required");
    const required = { duplicate: "DUPLICATE_RECORD", not_academic: "NOT_ACADEMIC_SOURCE", not_retrievable: "FULL_TEXT_UNAVAILABLE" }[input.decision];
    if (required && input.exclusion_reason !== required) throw new V2Error("inconsistent_exclusion_reason");
    if (input.decision === "not_eligible" && ["DUPLICATE_RECORD", "NOT_ACADEMIC_SOURCE", "FULL_TEXT_UNAVAILABLE"].includes(input.exclusion_reason)) throw new V2Error("inconsistent_exclusion_reason");
  }
  else if (input.exclusion_reason) throw new V2Error("unexpected_exclusion_reason");
  if (input.decision === "duplicate") {
    text(input.duplicate_target, "duplicate_target", 100);
    if (input.duplicate_target === input.candidate_id) throw new V2Error("self_duplicate");
  } else if (input.duplicate_target) throw new V2Error("unexpected_duplicate_target");
  if (input.supersedes_id !== null) text(input.supersedes_id, "supersedes_id", 100);
  return JSON.parse(canonicalJson(input));
}

function stmt(db, sql, ...values) { return db.prepare(sql).bind(...values); }
async function rows(db, sql, ...values) { return (await stmt(db, sql, ...values).all()).results; }
export async function readiness(env) {
  const blockers = [];
  if (!env.REVIEW_DB) blockers.push("private_database_not_bound");
  if (!env.REVIEW_EVIDENCE) blockers.push("private_evidence_store_not_bound");
  if (!env.REVIEW_JOBS) blockers.push("durable_queue_not_bound");
  // CILE-DAILY-v3 uses Exa. Access, budget and approved-query gates still apply.
  let manifestReady = false;
  try { manifestReady = !queryManifestProblem(JSON.parse(env.REVIEW_DAILY_QUERY_MANIFEST || "null")); } catch { /* Invalid manifests never establish readiness. */ }
  if (!manifestReady) blockers.push("approved_daily_query_manifest_required");
  if (!env.EXA_API_KEY || env.EXA_FREE_ONLY !== "true" || env.EXA_DEDICATED_STARTER_ACCOUNT !== "true") blockers.push("exa_budget_readiness_required");
  let review = null;
  if (env.REVIEW_DB) {
    try {
      review = await env.REVIEW_DB.prepare("SELECT review_id,phase,start_date,protocol_version,ontology_version FROM reviews WHERE phase = 'active'").first();
      const accessSchema = await env.REVIEW_DB.prepare("SELECT name FROM sqlite_master WHERE type='view' AND name='v2_open_access_candidates'").first();
      if (!accessSchema) blockers.push("open_access_schema_not_applied");
      if (review && (review.protocol_version !== V2_PROTOCOL || review.ontology_version !== V2_ONTOLOGY)) blockers.push("review_protocol_mismatch");
    }
    catch { blockers.push("schema_not_applied"); }
  }
  if (!review) blockers.push("review_not_activated");
  return { schema_version: 2, ontology_version: V2_ONTOLOGY, protocol_version: V2_PROTOCOL, review, blockers, ready: blockers.length === 0,
    access_policy: "open_access_only", access_policy_version: "OA-1",
    assistant_mode: "observation_disabled_pending_calibration", seed_status: "proposed_unapproved" };
}
async function activeReview(env) {
  if (!env.REVIEW_DB) throw new V2Error("private_database_not_bound", 503);
  const review = await env.REVIEW_DB.prepare("SELECT * FROM reviews WHERE phase = 'active'").first();
  if (!review) throw new V2Error("review_not_activated", 409);
  if (review.protocol_version !== V2_PROTOCOL || review.ontology_version !== V2_ONTOLOGY) throw new V2Error("review_protocol_mismatch", 409);
  return review;
}
async function candidateContext(db, review, candidateId) {
  const candidate = await stmt(db, "SELECT * FROM review_candidates WHERE review_id=? AND candidate_id=?", review.review_id, candidateId).first();
  if (!candidate) throw new V2Error("candidate_not_found", 404);
  const spans = await rows(db, `SELECT s.*,e.candidate_id,e.identity_state,e.evidence_kind,e.content_sha256,e.source_url
    FROM evidence_spans s JOIN evidence_sources e USING(review_id,evidence_id)
    WHERE s.review_id=? AND e.candidate_id=?`, review.review_id, candidateId);
  const access = await stmt(db, "SELECT * FROM v2_open_access_candidates WHERE review_id=? AND candidate_id=?", review.review_id, candidateId).first();
  return { review, candidate, spans, access };
}
async function github(path, token, method = "GET", body = undefined) {
  const response = await fetchWithTimeout(`https://api.github.com${path}`, { method, body: body === undefined ? undefined : JSON.stringify(body), headers: { Authorization: `Bearer ${token}`, Accept: "application/vnd.github+json", "Content-Type": "application/json", "User-Agent": "cile-v2-approval", "X-GitHub-Api-Version": "2022-11-28" } });
  if (!response.ok) throw new V2Error("github_approval_verification_failed", 503);
  return response.json();
}
export async function verifyHumanApproval({ repository, prNumber, proposal, token, humanLogin }, get = github) {
  if (!Number.isSafeInteger(prNumber) || prNumber < 1) throw new V2Error("invalid_pr_number");
  const root = `/repos/${repository}`;
  const pr = await get(`${root}/pulls/${prNumber}`, token);
  if (!pr.merged || pr.base?.ref !== "main" || pr.base?.repo?.full_name !== repository || pr.head?.repo?.full_name !== repository) throw new V2Error("scientific_pr_not_merged", 409);
  const reviews = [];
  for (let page = 1; page <= 20; page++) {
    const part = await get(`${root}/pulls/${prNumber}/reviews?per_page=100&page=${page}`, token);
    reviews.push(...part); if (part.length < 100) break;
    if (page === 20) throw new V2Error("review_pagination_incomplete", 409);
  }
  const authoritative = reviews.filter((r) => r.user?.login === humanLogin && r.user?.type === "User" && ["APPROVED", "CHANGES_REQUESTED", "DISMISSED"].includes(r.state));
  const review = authoritative.at(-1);
  if (!review || review.state !== "APPROVED" || review.commit_id !== pr.head.sha) throw new V2Error("exact_head_human_approval_required", 409);
  // Only the hash is written to the public repository; private scientific evidence remains in D1/R2.
  const path = `scientific-approvals/${proposal.proposal_id}.json`;
  const file = await get(`${root}/contents/${path}?ref=${pr.head.sha}`, token);
  if (file.encoding !== "base64" || file.size > 4096) throw new V2Error("approval_manifest_invalid");
  const manifest = JSON.parse(atob(file.content.replace(/\s/g, "")));
  exact(manifest, ["proposal_id", "payload_sha256", "protocol_version", "action"], "approval_manifest");
  if (manifest.action !== "approve_screening" || manifest.proposal_id !== proposal.proposal_id || manifest.payload_sha256 !== proposal.payload_sha256 || manifest.protocol_version !== proposal.protocol_version) throw new V2Error("approval_hash_mismatch", 409);
  return { human_login: humanLogin, human_review_id: String(review.id), reviewed_commit: pr.head.sha, approved_at: review.submitted_at };
}
async function validateDuplicateTarget(db, review, payload) {
  if (payload.decision !== "duplicate") return;
  const target = await stmt(db, "SELECT candidate_id,identity_state FROM review_candidates WHERE review_id=? AND candidate_id=?", review.review_id, payload.duplicate_target).first();
  if (!target || target.identity_state !== "verified") throw new V2Error("verified_duplicate_target_required", 409);
}
async function importApproval(env, session, review, input) {
  exact(input, ["proposal_id", "pr_number"], "approval_import");
  const db = env.REVIEW_DB;
  const proposal = await stmt(db, "SELECT * FROM decision_proposals WHERE proposal_id=? AND review_id=?", input.proposal_id, review.review_id).first();
  if (!proposal) throw new V2Error("proposal_not_found", 404);
  const existing = await stmt(db, "SELECT receipt_id FROM approval_receipts WHERE proposal_id=?", input.proposal_id).first();
  if (existing) return { ...existing, replayed: true };
  const context = await candidateContext(db, review, proposal.candidate_id);
  const payload = validateProposal(JSON.parse(proposal.payload_json), { ...context, actor: session.login });
  await validateDuplicateTarget(db, review, payload);
  if (await sha256(canonicalJson(payload)) !== proposal.payload_sha256) throw new V2Error("proposal_integrity_failure", 409);
  const current = await stmt(db, `SELECT decision_id FROM screening_decisions_v2 d WHERE review_id=? AND candidate_id=?
    AND NOT EXISTS (SELECT 1 FROM screening_decisions_v2 newer WHERE newer.supersedes_id=d.decision_id)`, review.review_id, proposal.candidate_id).first();
  if ((current?.decision_id || null) !== payload.supersedes_id) throw new V2Error("stale_decision", 409);
  const approval = await verifyHumanApproval({ repository: env.GITHUB_REPOSITORY, prNumber: input.pr_number, proposal, token: session.token, humanLogin: env.CURATOR_LOGIN });
  const receiptId = crypto.randomUUID(), decisionId = crypto.randomUUID(), now = new Date().toISOString();
  // The NOT NULL scalar subquery is the transaction's optimistic concurrency gate.
  // A stale row aborts the whole D1 batch before any decision can be inserted.
  const statements = [stmt(db, `INSERT INTO approval_receipts VALUES (?,?,?,
    (SELECT candidate_id FROM review_candidates WHERE review_id=? AND candidate_id=? AND record_version=?),?,?,?,?,?,?,?,?,?)`,
    receiptId, proposal.proposal_id, review.review_id, review.review_id, proposal.candidate_id, payload.expected_version,
    payload.expected_version, proposal.payload_sha256, env.GITHUB_REPOSITORY, input.pr_number, approval.reviewed_commit,
    approval.human_login, approval.human_review_id, approval.approved_at, now),
  stmt(db, "INSERT INTO screening_decisions_v2 VALUES (?,?,?,?,?,?,?,?,?)", decisionId, receiptId, review.review_id, payload.candidate_id, payload.decision, payload.rationale, payload.protocol_version, payload.supersedes_id, now),
  ...payload.criteria.map((c) => stmt(db, "INSERT INTO criterion_assessments VALUES (?,?,?,?,?)", decisionId, c.criterion_id, c.outcome, c.rationale, canonicalJson(c.evidence_span_ids))),
  stmt(db, "UPDATE review_candidates SET record_version=record_version+1 WHERE review_id=? AND candidate_id=?", review.review_id, payload.candidate_id)];
  await db.batch(statements);
  return { decision_id: decisionId, receipt_id: receiptId, replayed: false, publication: "not_approved" };
}
function response(value, status = 200) { return Response.json(value, { status, headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer" } }); }
async function body(request) {
  if (!request.headers.get("Content-Type")?.startsWith("application/json")) throw new V2Error("json_required", 400);
  const raw = await request.text(); if (raw.length > 250000) throw new V2Error("payload_too_large", 413);
  try { return JSON.parse(raw); } catch { throw new V2Error("invalid_json", 400); }
}

export async function handleV2(request, env, session) {
  try {
    const url = new URL(request.url), path = url.pathname, db = env.REVIEW_DB;
    if (path === "/api/v2/status" && request.method === "GET") return response(await readiness(env));
    const review = await activeReview(env);
    if (path === "/api/v2/proposal" && request.method === "GET") {
      const proposal = await stmt(db, "SELECT * FROM decision_proposals WHERE proposal_id=? AND review_id=?", url.searchParams.get("id"), review.review_id).first();
      if (!proposal) throw new V2Error("proposal_not_found", 404);
      return response({ proposal_id: proposal.proposal_id, payload_sha256: proposal.payload_sha256, proposed_by: proposal.proposed_by, created_at: proposal.created_at, payload: JSON.parse(proposal.payload_json) });
    }
    if (path === "/api/v2/candidates" && request.method === "GET") return response({ review_id: review.review_id, candidates: await rows(db, "SELECT candidate_id,title,work_id,identity_state,stage,record_version FROM review_candidates WHERE review_id=? ORDER BY created_at,candidate_id LIMIT 200", review.review_id) });
    if (path === "/api/v2/candidate" && request.method === "GET") {
      const context = await candidateContext(db, review, url.searchParams.get("id"));
      const work = context.candidate.work_id ? await stmt(db, "SELECT * FROM scholarly_works WHERE work_id=?", context.candidate.work_id).first() : null;
      const expressions = work ? await rows(db, "SELECT * FROM expressions WHERE work_id=?", work.work_id) : [];
      const contributions = work ? await rows(db, "SELECT c.*,a.display_name FROM contributions c JOIN agents a USING(agent_id) JOIN expressions e USING(expression_id) WHERE e.work_id=? ORDER BY c.position", work.work_id) : [];
      const evidence = await rows(db, "SELECT evidence_id,evidence_kind,identity_state,source_url,content_sha256,observed_at FROM evidence_sources WHERE review_id=? AND candidate_id=?", review.review_id, context.candidate.candidate_id);
      const decisions = await rows(db, "SELECT d.*,r.human_login,r.pr_number FROM screening_decisions_v2 d JOIN approval_receipts r USING(receipt_id) WHERE d.review_id=? AND d.candidate_id=? ORDER BY d.created_at", review.review_id, context.candidate.candidate_id);
      const access_history = await rows(db, "SELECT * FROM access_assessments_v2 WHERE review_id=? AND candidate_id=? ORDER BY rowid", review.review_id, context.candidate.candidate_id);
      return response({ ...context, work, expressions, contributions, evidence, decisions, access_history });
    }
    if (path === "/api/v2/access-assessments" && request.method === "POST") {
      const input = await body(request);
      const fields = ["assessment_id", "candidate_id", "evidence_id", "full_text_url", "version_type", "host_type", "license_uri", "rights_basis", "rights_evidence_url", "access_status", "verification_method", "supersedes_id"];
      exact(input, [...fields, "expected_version"], "access_assessment");
      text(input.assessment_id, "assessment_id", 100); text(input.rights_basis, "rights_basis");
      if (!["verified_open", "restricted", "unknown", "revoked"].includes(input.access_status)) throw new V2Error("invalid_access_status");
      const previous = await stmt(db, "SELECT * FROM access_assessments_v2 WHERE assessment_id=?", input.assessment_id).first();
      if (previous) {
        if (previous.review_id !== review.review_id || fields.some((key) => input[key] !== previous[key])) throw new V2Error("access_assessment_conflict", 409);
        return response({ assessment_id: previous.assessment_id, replayed: true });
      }
      const context = await candidateContext(db, review, input.candidate_id);
      if (input.expected_version !== context.candidate.record_version) throw new V2Error("stale_candidate", 409);
      const latest = await stmt(db, `SELECT assessment_id FROM access_assessments_v2 a WHERE review_id=? AND candidate_id=?
        AND NOT EXISTS (SELECT 1 FROM access_assessments_v2 n WHERE n.supersedes_id=a.assessment_id)`, review.review_id, input.candidate_id).first();
      if ((latest?.assessment_id || null) !== input.supersedes_id) throw new V2Error("stale_access_assessment", 409);
      if (input.access_status === "verified_open") {
        if (!["accepted", "version_of_record"].includes(input.version_type) || !["publisher", "repository"].includes(input.host_type)
          || input.verification_method !== "anonymous_full_text_verified") throw new V2Error("lawful_full_text_verification_required");
        https(input.full_text_url); https(input.rights_evidence_url); if (input.license_uri) https(input.license_uri);
        const source = await stmt(db, "SELECT * FROM evidence_sources WHERE review_id=? AND candidate_id=? AND evidence_id=?", review.review_id, input.candidate_id, input.evidence_id).first();
        if (!source || source.evidence_kind !== "full_text" || source.identity_state !== "verified" || source.source_url !== input.full_text_url) throw new V2Error("verified_full_text_source_required");
        const object = await env.REVIEW_EVIDENCE?.get(source.storage_key);
        if (!object || await sha256(await object.text()) !== source.content_sha256) throw new V2Error("full_text_integrity_failure", 409);
      } else if (input.verification_method !== "access_observation") throw new V2Error("invalid_access_observation");
      await db.batch([
        stmt(db, `INSERT INTO access_assessments_v2 VALUES (?,?,
          (SELECT candidate_id FROM review_candidates WHERE review_id=? AND candidate_id=? AND record_version=?),?,?,?,?,?,?,?,?,?,?,?,?)`,
          input.assessment_id, review.review_id, review.review_id, input.candidate_id, input.expected_version,
          input.evidence_id, input.full_text_url, input.version_type, input.host_type, input.license_uri, input.rights_basis,
          input.rights_evidence_url, input.access_status, input.verification_method, new Date().toISOString(), session.login, input.supersedes_id),
        stmt(db, "UPDATE review_candidates SET record_version=record_version+1 WHERE review_id=? AND candidate_id=?", review.review_id, input.candidate_id),
      ]);
      return response({ assessment_id: input.assessment_id, replayed: false, scientific_decision: "not_created" }, 201);
    }
    if (path === "/api/v2/evidence" && request.method === "GET") {
      const source = await stmt(db, "SELECT * FROM evidence_sources WHERE review_id=? AND evidence_id=?", review.review_id, url.searchParams.get("id")).first();
      if (!source || !env.REVIEW_EVIDENCE) throw new V2Error("evidence_not_found", 404);
      const object = await env.REVIEW_EVIDENCE.get(source.storage_key); if (!object) throw new V2Error("evidence_unavailable", 503);
      const sourceText = await object.text();
      if (await sha256(sourceText) !== source.content_sha256) throw new V2Error("evidence_integrity_failure", 409);
      return response({ evidence_id: source.evidence_id, evidence_kind: source.evidence_kind, text: sourceText, content_sha256: source.content_sha256 });
    }
    if (path === "/api/v2/evidence" && request.method === "POST") {
      const input = await body(request);
      exact(input, ["candidate_id", "expected_version", "source_url", "evidence_kind", "identity_state", "rights_basis", "text", "spans"], "evidence");
      const context = await candidateContext(db, review, input.candidate_id);
      if (input.expected_version !== context.candidate.record_version) throw new V2Error("stale_candidate", 409);
      if (!env.REVIEW_EVIDENCE) throw new V2Error("private_evidence_store_not_bound", 503);
      if (![...SCIENTIFIC_KINDS, "metadata", "triage_note", "model_summary"].includes(input.evidence_kind)
        || !["unresolved", "verified", "conflict"].includes(input.identity_state)) throw new V2Error("invalid_evidence_kind");
      if (input.identity_state === "verified" && context.candidate.identity_state !== "verified") throw new V2Error("candidate_identity_unverified");
      const sourceUrl = https(input.source_url);
      text(input.text, "source_text", 200000);
      const sourceText = input.text;
      const rights = text(input.rights_basis, "rights_basis", 1500);
      if (!Array.isArray(input.spans) || input.spans.length > 40) throw new V2Error("invalid_spans");
      const evidenceId = crypto.randomUUID(), hash = await sha256(sourceText), now = new Date().toISOString();
      const key = `${review.review_id}/evidence/${hash}.txt`;
      const spans = [];
      for (const span of input.spans) {
        exact(span, ["locator", "start_offset", "end_offset"], "span");
        text(span.locator, "locator", 1000);
        if (!Number.isSafeInteger(span.start_offset) || !Number.isSafeInteger(span.end_offset)
          || span.start_offset < 0 || span.end_offset <= span.start_offset || span.end_offset > sourceText.length) throw new V2Error("invalid_span_offsets");
        spans.push({ ...span, span_id: crypto.randomUUID(), text_sha256: await sha256(sourceText.slice(span.start_offset, span.end_offset)) });
      }
      // Content addressed R2 writes are replay-safe; a failed D1 transaction leaves only an unreferenced object.
      await env.REVIEW_EVIDENCE.put(key, sourceText, { httpMetadata: { contentType: "text/plain; charset=utf-8" } });
      await db.batch([
        stmt(db, `INSERT INTO evidence_sources VALUES (?,?,
          (SELECT candidate_id FROM review_candidates WHERE review_id=? AND candidate_id=? AND record_version=?),
          NULL,NULL,?,?,?,?,?,?,?)`, review.review_id, evidenceId, review.review_id, input.candidate_id, input.expected_version,
          sourceUrl, input.evidence_kind, input.identity_state, hash, key, rights, now),
        ...spans.map((s) => stmt(db, "INSERT INTO evidence_spans VALUES (?,?,?,?,?,?,?)", review.review_id, s.span_id, evidenceId, s.locator, s.start_offset, s.end_offset, s.text_sha256)),
        stmt(db, "UPDATE review_candidates SET record_version=record_version+1 WHERE review_id=? AND candidate_id=?", review.review_id, input.candidate_id),
        stmt(db, "INSERT INTO operational_events VALUES (?,?,?,?,?,?)", crypto.randomUUID(), review.review_id, "curator_evidence_acquired", canonicalJson({ evidence_id: evidenceId, candidate_id: input.candidate_id, content_sha256: hash }), session.login, now),
      ]);
      return response({ evidence_id: evidenceId, content_sha256: hash, spans, record_version: input.expected_version + 1 }, 201);
    }
    if (path === "/api/v2/daily" && request.method === "GET") {
      const days = await rows(db, "SELECT scheduled_date,status,timezone,deadline_at FROM search_days WHERE review_id=? ORDER BY scheduled_date", review.review_id);
      const daily = [];
      for (const day of days) {
        const attempts = await rows(db, "SELECT attempt_number,started_at,finished_at,status,error_code,retry_after FROM run_attempts WHERE review_id=? AND scheduled_date=? ORDER BY attempt_number", review.review_id, day.scheduled_date);
        const checkpoints = await rows(db, "SELECT provider,query_id,status,occurrences_returned FROM query_executions WHERE review_id=? AND scheduled_date=? AND status='completed'", review.review_id, day.scheduled_date);
        daily.push({ ...day, attempt_count: attempts.length, started_at: attempts[0]?.started_at || null, finished_at: attempts.at(-1)?.finished_at || null,
          queries_completed: checkpoints.length, occurrences_returned: day.status === "completed" ? checkpoints.reduce((n, q) => n + q.occurrences_returned, 0) : null,
          new_candidates: null, screening_decisions: null, error_codes: [...new Set(attempts.map((a) => a.error_code).filter(Boolean))],
          recovered_late: attempts.some((a) => new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Rome" }).format(new Date(a.started_at)) > day.scheduled_date),
          attempts });
      }
      return response({ schema_version: 2, review_id: review.review_id, timezone: "Europe/Rome", daily });
    }
    if (path === "/api/v2/proposals" && request.method === "POST") {
      const input = await body(request), context = await candidateContext(db, review, input.candidate_id);
      const payload = validateProposal(input, { ...context, actor: session.login });
      await validateDuplicateTarget(db, review, payload);
      const json = canonicalJson(payload), hash = await sha256(json), now = new Date().toISOString();
      const existing = await stmt(db, "SELECT payload_sha256 FROM decision_proposals WHERE proposal_id=?", payload.proposal_id).first();
      if (existing) {
        if (existing.payload_sha256 !== hash) throw new V2Error("idempotency_conflict", 409);
        return response({ proposal_id: payload.proposal_id, payload_sha256: hash, state: "awaiting_human_pr_review", replayed: true });
      }
      const manifest = { action: "approve_screening", proposal_id: payload.proposal_id, payload_sha256: hash, protocol_version: payload.protocol_version };
      await db.batch([
        stmt(db, `INSERT INTO decision_proposals VALUES (?,?,(SELECT candidate_id FROM review_candidates WHERE review_id=? AND candidate_id=? AND record_version=?),?,?,?,?,?,?)`, payload.proposal_id, review.review_id, review.review_id, payload.candidate_id, payload.expected_version, payload.expected_version, payload.protocol_version, json, hash, session.login, now),
        stmt(db, "INSERT INTO outbox(outbox_id,review_id,kind,payload_json,created_at) VALUES (?,?,?,?,?)", `pr-${payload.proposal_id}`, review.review_id, "scientific_pr", canonicalJson(manifest), now),
      ]);
      return response({ ...manifest, state: "awaiting_human_pr_review", approval_file: `scientific-approvals/${payload.proposal_id}.json`, replayed: false }, 201);
    }
    if (path === "/api/v2/approval-import" && request.method === "POST") return response(await importApproval(env, session, review, await body(request)));
    if (path === "/api/v2/prepare-pr" && request.method === "POST") {
      const input = await body(request); exact(input, ["proposal_id"], "prepare_pr");
      const outbox = await stmt(db, "SELECT * FROM outbox WHERE outbox_id=? AND review_id=?", `pr-${input.proposal_id}`, review.review_id).first();
      if (!outbox) throw new V2Error("proposal_not_found", 404);
      const marker = `<!-- cile-v2-proposal:${input.proposal_id} -->`;
      const root = `/repos/${env.GITHUB_REPOSITORY}`;
      // Recover an uncertain previous issue submission without creating a duplicate.
      let existing = null;
      for (let page = 1; page <= 20; page++) {
        const issues = await github(`${root}/issues?state=all&creator=${encodeURIComponent(session.login)}&per_page=100&page=${page}`, session.token);
        existing = issues.find((issue) => !issue.pull_request && issue.user?.login === session.login && issue.body?.startsWith(marker));
        if (existing || issues.length < 100) break;
        if (page === 20) throw new V2Error("submission_inventory_incomplete", 503);
      }
      const receipt = JSON.parse(outbox.payload_json);
      if (!existing) {
        const claim = await stmt(db, "UPDATE outbox SET attempts=attempts+1 WHERE outbox_id=? AND attempts=0", outbox.outbox_id).run();
        if (!claim.meta?.changes) throw new V2Error("submission_unconfirmed_manual_reconciliation_required", 409);
      }
      const issue = existing || await github(`${root}/issues`, session.token, "POST", {
        title: `[V2 PROPOSAL] ${input.proposal_id}`, body: `${marker}\n\n\`\`\`json\n${canonicalJson(receipt)}\n\`\`\``,
      });
      await stmt(db, "UPDATE outbox SET delivered_at=? WHERE outbox_id=?", new Date().toISOString(), outbox.outbox_id).run();
      return response({ state: "awaiting_human_pr_review", issue_url: issue.html_url, replayed: Boolean(existing) });
    }
    throw new V2Error("route_not_found", 404);
  } catch (error) { return response({ error: { code: error.code || "v2_internal_error", message: error.code || "Operazione interrotta; nessuna approvazione implicita." } }, error.status || 500); }
}
