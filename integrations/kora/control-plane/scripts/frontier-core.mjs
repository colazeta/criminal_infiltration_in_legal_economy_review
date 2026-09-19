const GATES = [
  "F0_METADATA_SOURCE",
  "F1_FULLTEXT_READY",
  "F2_PROPOSAL_PERSISTED",
  "F3_INDEPENDENT_COMPARISON",
  "F4_REFERENCES_READY",
  "F5_ASSESSMENT_COMPLETE",
  "F6_VALIDATION_READY",
  "F7_VALIDATED",
];

export function evaluateFrontier(input) {
  const candidateFlags = [
    "metadata_source_ready",
    "fulltext_ready",
    "proposal_persisted",
    "mandatory_fields_accounted",
    "framework_assessed",
    "independent_comparison_ready",
    "references_ready",
    "limitations_caveats_ready",
    "version_guards_match",
    "validation_ready",
    "validated",
  ];

  if (!input.candidate_present) {
    const dirty = candidateFlags.some((key) => input[key] === true);
    return dirty
      ? {
          frontier_gate: "NONE",
          next_gate: "F0_METADATA_SOURCE",
          frontier_consistent: false,
          assessment_completed: false,
          validation_accepted: false,
          inconsistency_code: "candidate_absent_with_frontier_state",
        }
      : {
          frontier_gate: "NONE",
          next_gate: "F0_METADATA_SOURCE",
          frontier_consistent: true,
          assessment_completed: false,
          validation_accepted: false,
        };
  }

  const consistencyChecks = [
    [input.fulltext_ready && !input.metadata_source_ready, "fulltext_without_metadata_source"],
    [input.proposal_persisted && !input.fulltext_ready, "proposal_without_fulltext"],
    [input.independent_comparison_ready && !input.proposal_persisted, "comparison_without_proposal"],
    [input.references_ready && !input.independent_comparison_ready, "references_without_comparison"],
  ];

  const assessmentCompleted = Boolean(
    input.fulltext_ready &&
      input.proposal_persisted &&
      input.mandatory_fields_accounted &&
      input.framework_assessed &&
      input.independent_comparison_ready &&
      input.references_ready &&
      input.limitations_caveats_ready &&
      input.version_guards_match
  );

  consistencyChecks.push(
    [input.validation_ready && !assessmentCompleted, "validation_ready_before_assessment_complete"],
    [input.validated && !input.validation_ready, "validated_without_validation_ready"]
  );

  const inconsistency = consistencyChecks.find(([failed]) => failed)?.[1];

  let frontierGate;
  let nextGate;
  let distance;
  if (!input.fulltext_ready) {
    frontierGate = "F0_METADATA_SOURCE";
    nextGate = "F1_FULLTEXT_READY";
    distance = 5;
  } else if (!input.proposal_persisted) {
    frontierGate = "F1_FULLTEXT_READY";
    nextGate = "F2_PROPOSAL_PERSISTED";
    distance = 4;
  } else if (!input.independent_comparison_ready) {
    frontierGate = "F2_PROPOSAL_PERSISTED";
    nextGate = "F3_INDEPENDENT_COMPARISON";
    distance = 3;
  } else if (!input.references_ready) {
    frontierGate = "F3_INDEPENDENT_COMPARISON";
    nextGate = "F4_REFERENCES_READY";
    distance = 2;
  } else if (!assessmentCompleted) {
    frontierGate = "F4_REFERENCES_READY";
    nextGate = "F5_ASSESSMENT_COMPLETE";
    distance = 1;
  } else if (!input.validation_ready) {
    frontierGate = "F5_ASSESSMENT_COMPLETE";
    nextGate = "F6_VALIDATION_READY";
    distance = 0;
  } else if (!input.validated) {
    frontierGate = "F6_VALIDATION_READY";
    nextGate = "F7_VALIDATED";
    distance = 0;
  } else {
    frontierGate = "F7_VALIDATED";
    nextGate = "NONE";
    distance = 0;
  }

  const out = {
    frontier_gate: frontierGate,
    next_gate: nextGate,
    frontier_consistent: !inconsistency,
    assessment_completed: assessmentCompleted,
    validation_accepted: Boolean(input.validated),
    assessment_distance_to_f5: distance,
  };
  if (inconsistency) out.inconsistency_code = inconsistency;
  return out;
}

export { GATES };
