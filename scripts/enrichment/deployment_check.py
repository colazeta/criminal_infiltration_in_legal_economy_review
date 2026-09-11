#!/usr/bin/env python3
"""Check private deployment readiness, independently of individual paper outcomes."""
import argparse
import json
import os
import re
import time
from scripts.enrichment.service_client import call

STALE = 'enrichment_service_http_409:stale_deployment'


def check(expected_commit, *, activate=False, attempts=19, delay=10):
    """Only verify is retried; the requested deployment never changes on a retry."""
    if not re.fullmatch(r'[a-f0-9]{40}', expected_commit or ''):
        raise RuntimeError('invalid_expected_deployment')
    if not 1 <= attempts <= 19 or not 0 <= delay <= 10:
        raise RuntimeError('invalid_readiness_retry_budget')
    for attempt in range(attempts):
        try:
            verified = call('verify', expected_commit=expected_commit)
            break
        except RuntimeError as error:
            if str(error) != STALE or attempt + 1 == attempts:
                raise
            time.sleep(delay)
    if verified.get('verified') is not True or verified.get('commit') != expected_commit:
        raise RuntimeError('private_deployment_not_verified')
    state = call('activate' if activate else 'status', expected_commit=expected_commit)
    schedule = state.get('scheduling', {})
    plan = schedule.get('schedule')
    if state.get('commit') != expected_commit:
        raise RuntimeError('private_deployment_changed')
    if activate and (state.get('enabled') is not True or not isinstance(plan, dict)):
        raise RuntimeError('private_schedule_not_activated')
    if schedule.get('protocol') != 'CILE-HOUR40-1' or schedule.get('cron') != '40 * * * *':
        raise RuntimeError('private_schedule_contract_mismatch')
    if isinstance(plan, dict):
        for field in ['first_slot', 'next_slot']:
            value = plan.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value % 3600000 != 2400000:
                raise RuntimeError('private_schedule_slot_invalid')
    # No source bodies, proposals, credentials or candidate records are requested.
    return {'deployment_ready': True, 'commit': expected_commit,
            'enabled': state.get('enabled'), 'storage_backend': state.get('storage_backend'),
            'scientific_extraction': state.get('scientific_extraction'),
            'counts': state.get('counts'), 'jobs': state.get('jobs'), 'scheduling': schedule,
            'paper_work_executed_by_check': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-commit', default=os.environ.get('GITHUB_SHA'))
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    print(json.dumps(check(args.expected_commit, activate=args.activate), indent=2))


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as error:
        raise SystemExit(str(error)) from None
