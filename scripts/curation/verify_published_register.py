#!/usr/bin/env python3
"""Verify served candidate bibliography after deployment without a token.

Saved intake, merge and deployment acceptance are not served-publication evidence.
A later release may add records but must not omit or alter expected records.
This verifier makes no scientific or access decision.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.curation.build_paper_register import FIELDS
MAX_BYTES = 16 * 1024 * 1024

def record_index(payload: dict) -> dict[str, dict]:
    if not isinstance(payload, dict) or payload.get('schemaVersion') != 1:
        raise ValueError('Unsupported public-register envelope')
    records = payload.get('records')
    if not isinstance(records, list):
        raise ValueError('Public records must be a list')
    result = {}
    for row in records:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError('Public-register field allowlist mismatch')
        candidate_id = row.get('id')
        if not isinstance(candidate_id, str) or not candidate_id.strip() or candidate_id in result:
            raise ValueError('Public candidate IDs must be nonblank and unique')
        result[candidate_id] = row
    return result

def compare_registers(expected: dict, actual: dict) -> dict:
    required, served = record_index(expected), record_index(actual)
    missing = sorted(required.keys() - served.keys())
    changed = sorted(cid for cid in required.keys() & served.keys() if required[cid] != served[cid])
    if missing or changed:
        raise ValueError(f'Public register mismatch: missing={missing[:10]}, changed={changed[:10]}')
    canonical = json.dumps(expected, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    return {'expected_records': len(required), 'served_records': len(served),
            'missing_records': 0, 'changed_records': 0,
            'expected_payload_sha256': hashlib.sha256(canonical).hexdigest()}

def public_bytes(url: str) -> bytes:
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != 'colazeta.github.io' or parsed.username or parsed.password:
        raise ValueError('Only the authorised credential-free public Pages origin is allowed')
    request = Request(url, headers={'Cache-Control': 'no-cache', 'Accept': 'application/json',
                                  'User-Agent': 'CILE-publication-verification/1'})
    with urlopen(request, timeout=25) as response:
        if response.status != 200 or urlsplit(response.url).hostname != parsed.hostname:
            raise ValueError('Unexpected public response or redirect')
        body = response.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError('Public register exceeds the bounded read size')
    return body

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--expected', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--attempts', type=int, default=9)
    parser.add_argument('--retry-seconds', type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.attempts <= 12 or not 0 <= args.retry_seconds <= 30:
        parser.error('Retry settings exceed the bounded publication check')
    expected = json.loads(args.expected.read_text())
    record_index(expected)
    error = ''
    for attempt in range(1, args.attempts + 1):
        try:
            body = public_bytes(args.url)
            receipt = compare_registers(expected, json.loads(body))
            receipt.update(url=args.url, verified_at=datetime.now(timezone.utc).isoformat(),
                           served_bytes_sha256=hashlib.sha256(body).hexdigest(), attempt=attempt,
                           workflow_run_id=os.environ.get('GITHUB_RUN_ID'),
                           scope='provisional_bibliography_only')
            args.receipt.write_text(json.dumps(receipt, indent=2) + '\n')
            print(json.dumps(receipt, sort_keys=True))
            return
        except (OSError, ValueError) as exc:
            error = str(exc)
            print(f'Publication read-back attempt {attempt}/{args.attempts}: {error}', file=sys.stderr)
            if attempt < args.attempts:
                time.sleep(args.retry_seconds)
    raise SystemExit('Served candidate publication was not verified: ' + error)

if __name__ == '__main__':
    main()
