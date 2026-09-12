import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

import { parseCandidateIssue, validateDecision } from "../src/index.js";

const CANDIDATE_ID = "CAND-ACADEMIC-2026-09-09-EXTRA-85e203d4eb5a-002";

function lowercaseCandidateIssue() {
  return {
    number: 464,
    state: "open",
    html_url: "https://github.com/colazeta/example/issues/464",
    labels: [{ name: "curation:queue" }, { name: "stage:manual-review" }],
    body: `<!-- curator-candidate:${CANDIDATE_ID} -->

## Candidate record

| Field | Value |
|---|---|
| Candidate ID | \`${CANDIDATE_ID}\` |
| Title | Beyond Mafia: Considerations on Criminal Infiltration in the Legal Economy |
| Authors | Giovanni Nicolazzo |
| Year | 2025 |
| Venue | Bristol University Press |
| DOI | Not recorded |
| Source | candidate-bound retrieval |
| Current review stage | **Manual scope review** |

## Daily intake provenance

- Provider: Parallel Search

## Curator action

Record an evidence-backed decision.
`,
  };
}

test("curator issue parser accepts lowercase batch fragments in governed candidate IDs", () => {
  const parsed = parseCandidateIssue(lowercaseCandidateIssue());
  assert.equal(parsed?.candidateId, CANDIDATE_ID);
  assert.equal(parsed?.title, "Beyond Mafia: Considerations on Criminal Infiltration in the Legal Economy");
});

test("decision validation accepts the same lowercase candidate-ID grammar", () => {
  const validated = validateDecision({
    candidateId: CANDIDATE_ID,
    candidateIssueNumber: 464,
    screeningStage: "title_abstract",
    decision: "maybe_full_text_needed",
    exclusionReasonCode: "",
    topicCode: "",
    duplicateTarget: "",
    secondaryCollectionCode: "",
    secondaryCollectionRationale: "",
    confidence: "medium",
    evidence: "Publisher abstract inspected; full-text review remains required.",
    rationale: "The current evidence is insufficient for a governed eligibility decision.",
    confirmed: true,
    submissionId: "c65db5c0-b505-47a9-9b40-36b094a0f837",
  });
  assert.equal(validated.candidateId, CANDIDATE_ID);
});

test("retrieval Worker accepts lowercase alphanumeric candidate IDs instead of the retired uppercase-only grammar", () => {
  const source = readFileSync(new URL("../src/worker.js", import.meta.url), "utf8");
  assert.match(source, /\^\[A-Za-z0-9\]\[A-Za-z0-9-\]\{2,59\}\$/);
  assert.doesNotMatch(source, /\^\[A-Z0-9\]\[A-Z0-9-\]\{2,59\}\$/);
});
