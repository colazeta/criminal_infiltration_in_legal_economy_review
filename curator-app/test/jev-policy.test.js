"use strict";

import assert from "node:assert/strict";
import test from "node:test";

import { buildJevShadowState } from "../src/jev-policy.js";
import { getJevQuestionSet, JEV_QUESTION_SETS } from "../src/jev-question-sets.js";

test("candidate screening admits only bounded metadata and derived support", () => {
  const state = buildJevShadowState("candidate_screening", {
    candidate: { candidate_id: "CAND-1", title: "A paper", authors: "A. Author", year: 2026, doi: "10.1/example" },
    evidence: {
      source_basis: "verified publisher metadata and analyst-derived synopsis",
      evidence_scope: "abstract_only",
      research_synopsis: "The study investigates sustained criminal influence over legitimate firms.",
      method_synopsis: "Panel analysis.",
      legal_economy_synopsis: "Legitimate firms are the unit of analysis.",
      relationship_synopsis: "Sustained ownership and control are analysed.",
      source_urls: ["https://example.org/paper"],
    },
  });
  assert.equal(state.candidate.candidate_id, "CAND-1");
  assert.equal(state.evidence.evidence_scope, "abstract_only");
});

test("forbidden raw/private content is rejected before state construction", () => {
  assert.throws(() => buildJevShadowState("candidate_screening", {
    candidate: { candidate_id: "CAND-1", title: "A paper" },
    evidence: { source_basis: "publisher", full_text: "raw copyrighted body" },
  }), /jev_forbidden_input_key/);
  assert.throws(() => buildJevShadowState("enrichment_qa", {
    candidate: { candidate_id: "CAND-1", title: "A paper" },
    proposal: {},
    evidence: { private_note: "internal" },
  }), /jev_forbidden_input_key/);
});

test("unknown fields fail instead of being silently ignored", () => {
  assert.throws(() => buildJevShadowState("candidate_screening", {
    candidate: { candidate_id: "CAND-1", title: "A paper", invented_field: "x" },
    evidence: {},
  }), /jev_state_key_not_allowed/);
});

test("metadata assertions preserve conflicting observations without choosing a last string", () => {
  const state = buildJevShadowState("metadata_assertion", {
    candidate_id: "CAND-1",
    assertion: { field: "publication_year", value: 2022 },
    evidence: [
      { source: "publisher", observed_value: 2022, source_url: "https://example.org/a" },
      { source: "repository", observed_value: 2023, source_url: "https://example.org/b", evidence_note: "online-first versus issue-year distinction" },
    ],
  });
  assert.equal(state.evidence.length, 2);
  assert.equal(state.evidence[1].observed_value, 2023);
});

test("identity relation keeps manifestations explicit", () => {
  const state = buildJevShadowState("identity_relation", {
    left: { candidate_id: "CAND-A", title: "Working paper", year: 2019 },
    right: { candidate_id: "CAND-B", title: "Journal article", year: 2020 },
    evidence: { version_notes: "Publisher states the article developed from the working paper." },
  });
  assert.equal(state.left.year, 2019);
  assert.equal(state.right.year, 2020);
});

test("question sets are closed, versioned, and cloned before use", () => {
  assert.deepEqual(Object.keys(JEV_QUESTION_SETS).sort(), ["candidate_screening_v1", "enrichment_qa_v1", "identity_relation_v1", "metadata_assertion_v1"]);
  const set = getJevQuestionSet("candidate_screening_v1");
  assert.equal(set.version, "CILE-JEV-CANDIDATE-SCREENING-1");
  assert.equal(set.stateKind, "candidate_screening");
  for (const required of ["criminal_actor_supported", "legal_economy_object_supported", "sustained_relation_supported", "substantive_analysis_supported"]) {
    assert.equal(set.questions[required].type, "noul");
  }
  set.questions.criminal_actor_supported.instructions = "mutated";
  assert.notEqual(getJevQuestionSet("candidate_screening_v1").questions.criminal_actor_supported.instructions, "mutated");
});
