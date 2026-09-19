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
  if (input.scouting_due) return decision("SCOUT", "owned_scouting_window_due");
  if (input.unfinished_safe_write) return decision("PERSIST", "unfinished_safe_write_requires_readback");
  if (!input.frontier_consistent) return decision("BLOCKED", input.inconsistency_code || "frontier_inconsistent");
  if (input.active_wip_count > 6) return decision("BLOCKED", "ordinary_wip_limit_exceeded");

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
