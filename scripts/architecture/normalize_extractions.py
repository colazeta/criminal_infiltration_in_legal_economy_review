"""Mechanical, idempotent backfill; logs only a validated aggregate receipt."""
import json
import os
import re
from scripts.enrichment.service_client import call, classify_private_error
from scripts.enrichment.deployment_check import check


def migrate():
    expected = os.environ['GITHUB_SHA']
    # Public /version can precede the Durable Object deployment. Reuse the
    # bounded read-only exact-commit gate before either mechanical write/replay.
    # Only verify may retry; normalization itself never retries on failure.
    check(expected, activate=False)
    receipts = []
    for attempt in range(2):
        receipt = call('architecture-normalize', expected_commit=expected)
        keys = {'contract', 'commit', 'proposals', 'migrated', 'verified', 'complete',
                'scientific_decisions_changed', 'private_content_exported', 'cutover_ready'}
        if (set(receipt) != keys or receipt['contract'] != 'CILE-EXTRACTION-RELATIONS-1'
                or receipt['commit'] != expected or receipt['complete'] is not True
                or any(receipt[k] is not False for k in ['scientific_decisions_changed', 'private_content_exported', 'cutover_ready'])
                or any(type(receipt[k]) is not int or receipt[k] < 0 for k in ['proposals', 'migrated', 'verified'])
                or receipt['proposals'] != receipt['migrated'] + receipt['verified']
                or attempt == 1 and receipt['migrated'] != 0):
            raise RuntimeError('normalization_receipt_invalid')
        receipts.append(receipt)
    return {'migration': receipts[0], 'replay': receipts[1], 'idempotency_verified': True}


def failure_code(error):
    """Keep actionable closed diagnostics without logging an exception payload."""
    message = str(error)
    if message == 'normalization_receipt_invalid':
        return message
    match = re.fullmatch(r'enrichment_service_http_([0-9]{3})(?::([a-z0-9_]+))?', message)
    if match:
        category = classify_private_error(match[2])
        return 'enrichment_service_http_' + match[1] + (':' + category if category else '')
    return 'normalization_operation_failed'


if __name__ == '__main__':
    try:
        print(json.dumps(migrate(), indent=2))
    except Exception as error:
        raise SystemExit('normalization_gate_failed:' + failure_code(error)) from None
