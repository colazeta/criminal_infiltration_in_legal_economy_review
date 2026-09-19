"""Mechanical, idempotent backfill; logs only a validated aggregate receipt."""
import json
import os
from scripts.enrichment.service_client import call


def migrate():
    expected = os.environ['GITHUB_SHA']
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


if __name__ == '__main__':
    try:
        print(json.dumps(migrate(), indent=2))
    except Exception:
        raise SystemExit('normalization_gate_failed') from None
