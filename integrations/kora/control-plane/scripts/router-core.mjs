const PRIORITY = {
  SCOUT: 1,
  PERSIST: 1,
  COMPLETE: 2,
  CALIBRATION_CASE: 3,
  RESOLVE: 4,
  ENGINEER: 5,
  BLOCKED: 6,
  NOOP: 7,
};

function decision(route, reason) {
  return {
    route,
    reason,
    priority: PRIORITY[route],
    side_effect_authorized: false,
    pilot_mode: "observe_only",
  };
}

export function routeActivation(input) {
  const blocker = !input.frontier_consistent
    ? input.inconsistency_code || "frontier_inconsistent"
    : input.active_wip_count > 6 ? "ordinary_wip_limit_exceeded" : null;
  // The caller must positively attest independence for the selected activity.
  // Missing attestations fail closed; neither exception authorizes side effects.
  if (input.scouting_due) {
    if (blocker && input.scout_independent_of_frontier_and_wip !== true) {
      return decision("BLOCKED", blocker);
    }
    return decision("SCOUT", "owned_scouting_window_due");
  }
  if (input.unfinished_safe_write) {
    if (blocker && input.persist_independent_of_frontier_and_wip !== true) {
      return decision("BLOCKED", blocker);
    }
    return decision("PERSIST", "unfinished_safe_write_requires_readback");
  }
  if (blocker) return decision("BLOCKED", blocker);

  const incomplete = new Set([
    "F0_METADATA_SOURCE",
    "F1_FULLTEXT_READY",
    "F2_PROPOSAL_PERSISTED",
    "F3_INDEPENDENT_COMPARISON",
    "F4_REFERENCES_READY",
  ]);

  if (
    input.candidate_present &&
    incomplete.has(input.frontier_gate) &&
    input.writer_ready &&
    !input.repeat_without_changed_prerequisite
  ) {
    return decision("COMPLETE", "deepest_owned_paper_has_executable_f0_f5_gate");
  }

  if (input.calibration_case_ready) return decision("CALIBRATION_CASE", "validation_track_case_ready_without_displacing_completion");
  if (input.identity_debt_due) return decision("RESOLVE", "identity_debt_due_under_starvation_guard");
  if (input.lane === "B" && input.engineering_blocker) return decision("ENGINEER", "lane_b_shared_blocker_to_assessment_or_validation_track");

  if (input.candidate_present && incomplete.has(input.frontier_gate) && !input.writer_ready) {
    return decision("NOOP", "paper_parked_writer_or_claim_unavailable");
  }
  if (input.candidate_present && input.repeat_without_changed_prerequisite) {
    return decision("NOOP", "anti_repeat_guard_waiting_for_prerequisite_change");
  }
  if (input.lane === "A" && input.engineering_blocker) {
    return decision("NOOP", "lane_a_cannot_open_shared_engineering");
  }
  return decision("NOOP", "no_safe_executable_work");
}
