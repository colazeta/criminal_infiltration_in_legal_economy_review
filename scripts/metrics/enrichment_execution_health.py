"""Read-only diagnostics from existing hour-40 receipts, not research completion.

Deployment readiness and the scheduling watermark do not establish successful
execution. This module consumes the existing bounded status projection; it does
not write tickets, retry jobs, call providers or change scientific state.
"""
from collections import Counter

HOUR = 3_600_000
OFFSET = 2_400_000
FAILURE_THRESHOLD = 3
TERMINAL_MAX_AGE = 3 * HOUR
SCHEDULE_ID = 'cile-hour40-v1'
SAFE_ERROR_CODES = frozenset({
    'crossref_rate_limited', 'openalex_rate_limited', 'registry_rate_limited',
    'rate_limited', 'provider_record_not_found', 'provider_authentication_required',
    'identifier_resolution_required', 'identity_conflict', 'provider_unavailable',
    'provider_timeout', 'invalid_provider_json', 'operation_failed', 'lease_expired',
    'scheduler_operation_failed', 'processor_leased', 'processor_unavailable',
    'registry_unavailable', 'model_calibration_required', 'source_readback_failed',
    'source_integrity_failure',
})


def execution_health(scheduling, now):
    """Return an operational diagnostic, with unknown counts kept as None.

    Pending/running tickets do not reset the terminal failure streak. A completed
    ticket breaks it but may represent partial or empty processor work; it is
    never evidence of an assessment, accepted proposal or scientific inclusion.
    """
    result = {'status': 'unavailable', 'error_code': 'enrichment_iteration_history_unavailable',
              'observed_iterations': None, 'consecutive_failed_in_sample': None,
              'last_terminal_slot': None, 'last_terminal_status': None,
              'failure_codes_in_streak': None}
    if not isinstance(scheduling, dict) or type(now) is not int:
        return result
    schedule, iterations = scheduling.get('schedule'), scheduling.get('iterations')
    if (not isinstance(schedule, dict) or not isinstance(iterations, list)
            or len(iterations) > 48 or schedule.get('schedule_id') != SCHEDULE_ID
            or type(schedule.get('first_slot')) is not int
            or schedule['first_slot'] % HOUR != OFFSET):
        return result
    seen = set()
    for row in iterations:
        if not isinstance(row, dict):
            return result
        slot = row.get('scheduled_at')
        if (type(slot) is not int or slot % HOUR != OFFSET or slot > now
                or slot < schedule['first_slot'] or slot in seen
                or row.get('schedule_id') != SCHEDULE_ID
                or not isinstance(row.get('status'), str)
                or row.get('status') not in {'pending', 'running', 'completed', 'failed'}):
            return result
        seen.add(slot)
    result['observed_iterations'] = len(iterations)
    terminal = sorted((row for row in iterations if row['status'] in {'completed', 'failed'}),
                      key=lambda row: row['scheduled_at'], reverse=True)
    if not terminal:
        if now < schedule['first_slot'] + TERMINAL_MAX_AGE:
            result.update(status='awaiting_execution', error_code=None)
        else:
            result['error_code'] = 'enrichment_terminal_receipt_stalled'
        return result
    latest = terminal[0]
    failures = []
    for row in terminal:
        if row['status'] != 'failed':
            break
        code = row.get('error_code')
        # Emit only recognised diagnostic codes, never arbitrary retained text.
        failures.append(code if isinstance(code, str) and code in SAFE_ERROR_CODES
                        else 'unclassified_failure')
    result.update(status='no_failure_cluster', error_code=None,
                  consecutive_failed_in_sample=len(failures),
                  last_terminal_slot=latest['scheduled_at'], last_terminal_status=latest['status'],
                  failure_codes_in_streak=dict(sorted(Counter(failures).items())))
    if now - latest['scheduled_at'] > TERMINAL_MAX_AGE:
        result.update(status='stalled', error_code='enrichment_terminal_receipt_stalled')
    elif len(failures) >= FAILURE_THRESHOLD:
        result.update(status='degraded', error_code='enrichment_recent_iterations_failed')
    return result
