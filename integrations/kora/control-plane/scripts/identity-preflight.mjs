// Pure preflight over supplied observations. No network access or review writes.
// evidence_ref identifies the caller's evidence; the pilot does not retrieve it.
export function evaluateIdentityStarvation(input) {
  const result = (status, reason) => ({
    identity_starvation_status: status,
    identity_starvation_reason: reason,
  });
  const e = input.identity_preflight_evidence;
  const unknown = reason => result('undetermined', reason);
  if (!e || typeof e !== 'object' || Array.isArray(e)) return unknown('missing_preflight_evidence');
  if (typeof e.evidence_ref !== 'string' || !e.evidence_ref.trim()) return unknown('missing_evidence_reference');
  if (!['new_research', 'in_progress', 'non_research'].includes(e.activity_kind)) {
    return unknown('activity_nature_not_established');
  }
  // In-progress and non-research activity do not open new research. No inference
  // from frontier_gate/next_gate (including F3) is permitted here.
  if (e.activity_kind !== 'new_research') return result('not_required', 'activity_does_not_open_new_research');
  const count = e.pending_observation_count;
  const age = e.oldest_pending_age_seconds;
  const hasCount = Number.isInteger(count) && count >= 0;
  const hasAge = typeof age === 'number' && Number.isFinite(age) && age >= 0;
  if ((count != null && !hasCount) || (age != null && !hasAge)) return unknown('invalid_queue_evidence');
  if (count === 0 && hasAge) return unknown('empty_queue_with_pending_observation_age');
  if (count === 0) return result('not_required', 'observed_empty_pending_queue');
  if (hasAge && age >= 86400) return result('required', 'oldest_pending_at_least_24_hours');
  if (hasCount && count >= 20) return result('required', 'pending_queue_at_least_20');
  if (!hasAge || !hasCount) return unknown('insufficient_evidence_to_exclude_both_thresholds');
  return result('not_required', 'both_thresholds_observed_below_limit');
}
