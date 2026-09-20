"use strict";

const FORBIDDEN_KEY = /(full[_-]?text|abstract[_-]?text|source[_-]?body|raw[_-]?text|pdf[_-]?(bytes|body)|credential|secret|token|api[_-]?key|reviewer|private[_-]?note)/i;

function fail(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function plainObject(value) {
  return value && typeof value === "object" && !Array.isArray(value);
}

function assertNoForbiddenKeys(value, path = "state") {
  if (Array.isArray(value)) {
    value.forEach((item, index) => assertNoForbiddenKeys(item, `${path}[${index}]`));
    return;
  }
  if (!plainObject(value)) return;
  for (const [key, child] of Object.entries(value)) {
    if (FORBIDDEN_KEY.test(key)) fail(`jev_forbidden_input_key:${path}.${key}`);
    assertNoForbiddenKeys(child, `${path}.${key}`);
  }
}

function assertKeys(value, allowed, path) {
  if (!plainObject(value)) fail(`jev_state_invalid:${path}`);
  for (const key of Object.keys(value)) {
    if (!allowed.includes(key)) fail(`jev_state_key_not_allowed:${path}.${key}`);
  }
}

function text(value, path, max = 6000, { required = false } = {}) {
  if (value == null || value === "") {
    if (required) fail(`jev_state_missing:${path}`);
    return null;
  }
  if (typeof value !== "string") fail(`jev_state_invalid:${path}`);
  const result = value.trim();
  if (required && !result) fail(`jev_state_missing:${path}`);
  if (result.length > max) fail(`jev_state_too_large:${path}`);
  return result || null;
}

function scalar(value, path) {
  if (value == null) return null;
  if (["string", "number", "boolean"].includes(typeof value)) {
    if (typeof value === "string" && value.length > 2000) fail(`jev_state_too_large:${path}`);
    return value;
  }
  fail(`jev_state_invalid:${path}`);
}

function textArray(value, path, { maxItems = 20, maxLength = 1200 } = {}) {
  if (value == null) return [];
  if (!Array.isArray(value) || value.length > maxItems) fail(`jev_state_invalid:${path}`);
  return value.map((item, index) => text(item, `${path}[${index}]`, maxLength, { required: true }));
}

function httpsUrl(value, path) {
  const result = text(value, path, 2048);
  if (result == null) return null;
  let parsed;
  try { parsed = new URL(result); } catch { fail(`jev_state_invalid_url:${path}`); }
  if (parsed.protocol !== "https:") fail(`jev_state_invalid_url:${path}`);
  return parsed.toString();
}

function urlArray(value, path) {
  if (value == null) return [];
  if (!Array.isArray(value) || value.length > 20) fail(`jev_state_invalid:${path}`);
  return value.map((item, index) => httpsUrl(item, `${path}[${index}]`));
}

function candidateBrief(value, path = "candidate") {
  const allowed = ["candidate_id", "title", "authors", "year", "venue", "doi", "work_type", "language", "review_stage"];
  assertKeys(value, allowed, path);
  const out = {
    candidate_id: text(value.candidate_id, `${path}.candidate_id`, 300, { required: true }),
    title: text(value.title, `${path}.title`, 1500, { required: true }),
  };
  for (const key of ["authors", "venue", "doi", "work_type", "language", "review_stage"]) {
    const v = text(value[key], `${path}.${key}`, 1500);
    if (v != null) out[key] = v;
  }
  if (value.year != null) {
    if (!Number.isInteger(value.year) || value.year < 1000 || value.year > 3000) fail(`jev_state_invalid:${path}.year`);
    out.year = value.year;
  }
  return out;
}

function evidenceSummary(value, path = "evidence") {
  const allowed = ["source_basis", "evidence_scope", "research_synopsis", "method_synopsis", "legal_economy_synopsis", "relationship_synopsis", "source_summary", "access_status", "source_labels", "source_urls", "metadata_notes"];
  assertKeys(value, allowed, path);
  const out = {};
  for (const key of ["source_basis", "evidence_scope", "research_synopsis", "method_synopsis", "legal_economy_synopsis", "relationship_synopsis", "source_summary", "access_status", "metadata_notes"]) {
    const v = text(value[key], `${path}.${key}`, key.includes("synopsis") || key === "source_summary" ? 6000 : 1500);
    if (v != null) out[key] = v;
  }
  const labels = textArray(value.source_labels, `${path}.source_labels`);
  const urls = urlArray(value.source_urls, `${path}.source_urls`);
  if (labels.length) out.source_labels = labels;
  if (urls.length) out.source_urls = urls;
  return out;
}

function buildCandidateScreening(input) {
  assertKeys(input, ["candidate", "evidence"], "input");
  return { candidate: candidateBrief(input.candidate), evidence: evidenceSummary(input.evidence) };
}

function buildMetadataAssertion(input) {
  assertKeys(input, ["candidate_id", "assertion", "evidence"], "input");
  const candidateId = text(input.candidate_id, "input.candidate_id", 300, { required: true });
  assertKeys(input.assertion, ["field", "value"], "input.assertion");
  const assertion = {
    field: text(input.assertion.field, "input.assertion.field", 200, { required: true }),
    value: scalar(input.assertion.value, "input.assertion.value"),
  };
  if (!Array.isArray(input.evidence) || !input.evidence.length || input.evidence.length > 20) fail("jev_state_invalid:input.evidence");
  const evidence = input.evidence.map((row, index) => {
    const path = `input.evidence[${index}]`;
    assertKeys(row, ["source", "observed_value", "source_url", "evidence_note"], path);
    const out = {
      source: text(row.source, `${path}.source`, 500, { required: true }),
      observed_value: scalar(row.observed_value, `${path}.observed_value`),
    };
    const url = httpsUrl(row.source_url, `${path}.source_url`);
    const note = text(row.evidence_note, `${path}.evidence_note`, 1500);
    if (url) out.source_url = url;
    if (note) out.evidence_note = note;
    return out;
  });
  return { candidate_id: candidateId, assertion, evidence };
}

function buildIdentityRelation(input) {
  assertKeys(input, ["left", "right", "evidence"], "input");
  const allowedEvidence = ["stable_identifier_agreement", "title_relation", "author_relation", "date_relation", "version_notes", "relation_evidence", "source_urls"];
  assertKeys(input.evidence, allowedEvidence, "input.evidence");
  const evidence = {};
  for (const key of ["stable_identifier_agreement", "title_relation", "author_relation", "date_relation", "version_notes"]) {
    const v = text(input.evidence[key], `input.evidence.${key}`, 2000);
    if (v) evidence[key] = v;
  }
  const relationEvidence = textArray(input.evidence.relation_evidence, "input.evidence.relation_evidence", { maxItems: 20, maxLength: 2000 });
  const urls = urlArray(input.evidence.source_urls, "input.evidence.source_urls");
  if (relationEvidence.length) evidence.relation_evidence = relationEvidence;
  if (urls.length) evidence.source_urls = urls;
  return { left: candidateBrief(input.left, "input.left"), right: candidateBrief(input.right, "input.right"), evidence };
}

function buildEnrichmentQa(input) {
  assertKeys(input, ["candidate", "proposal", "evidence"], "input");
  const proposalKeys = ["research_question", "contribution", "infiltration_definition", "study_summary", "data_summary", "methods_summary", "variables_summary", "findings_summary", "limitations_summary", "framework_proposal"];
  assertKeys(input.proposal, proposalKeys, "input.proposal");
  const proposal = {};
  for (const key of proposalKeys) {
    const v = text(input.proposal[key], `input.proposal.${key}`, 6000);
    if (v != null) proposal[key] = v;
  }
  return { candidate: candidateBrief(input.candidate), proposal, evidence: evidenceSummary(input.evidence) };
}

const BUILDERS = {
  candidate_screening: buildCandidateScreening,
  metadata_assertion: buildMetadataAssertion,
  identity_relation: buildIdentityRelation,
  enrichment_qa: buildEnrichmentQa,
};

function buildJevShadowState(kind, input) {
  if (!BUILDERS[kind]) fail(`jev_state_kind_unknown:${kind}`);
  assertNoForbiddenKeys(input);
  const state = BUILDERS[kind](input);
  assertNoForbiddenKeys(state);
  return state;
}

export { buildJevShadowState };
