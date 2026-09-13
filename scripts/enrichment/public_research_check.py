#!/usr/bin/env python3
"""Read-only source-to-public research check; never request or log raw proposals."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request
from scripts.enrichment.service_client import call, current_commit, _PRIVATE_HTTP, ORIGIN


def public_get(url):
    # Fixed official origins only; do not follow redirects to another service.
    if not url.startswith((ORIGIN + '/api/public-paper-research?',
                           'https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/data/paper-register.json')):
        raise RuntimeError('unexpected_public_origin')
    with _PRIVATE_HTTP.open(Request(url, headers={'Accept': 'application/json', 'Cache-Control': 'no-cache'}), timeout=25) as response:
        raw = response.read(4_000_001)
    if len(raw) > 4_000_000:
        raise RuntimeError('public_response_limit')
    return json.loads(raw)


def digest(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def normal_doi(value):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(value or '').strip(), flags=re.I).lower()


def check(expected_commit, *, caller=call, fetcher=public_get):
    audit = caller('public-research-audit', expected_commit=expected_commit)
    if audit.get('projection_version') != 'CILE-PUBLIC-RESEARCH-1':
        raise RuntimeError('projection_version_mismatch')
    rows = audit.get('records')
    if not isinstance(rows, list) or len(rows) > 10000 or len({r['id'] for r in rows}) != len(rows):
        raise RuntimeError('invalid_audit_inventory')
    register = fetcher('https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/data/paper-register.json')
    registered = {r['id']: r for r in register['records']}
    # Verify every populated context and every blocked/stale record; sample at most
    # five unpopulated entries. The receipt states this denominator explicitly.
    selected = [r for r in rows if r['availability'] in {'available', 'withheld', 'stale'}]
    selected += [r for r in rows if r['availability'] == 'not_assessed'][:5]
    if len(selected) > 1000:
        raise RuntimeError('explicit_paged_audit_required')
    mismatches, unregistered, checked = [], [], []
    for row in selected:
        data = fetcher(ORIGIN + '/api/public-paper-research?' + urlencode({'id': row['id']}))
        unsigned = {k: v for k, v in data.items() if k != 'revision'}
        if data.get('revision') != row['revision'] or digest(unsigned) != row['revision'] or data.get('availability') != row['availability']:
            mismatches.append(row['id'])
            continue
        candidate = data.get('candidate')
        current = registered.get(row['id'])
        if not current:
            unregistered.append(row['id'])
        elif (not candidate or candidate['id'] != current['id'] or candidate['title'] != current['title']
              or normal_doi(candidate.get('doi')) != normal_doi(current.get('doi'))
              or sorted(candidate.get('sourceLinks', [])) != sorted(current.get('sourceLinks', []))):
            mismatches.append(row['id'])
        else:
            checked.append({'id': row['id'], 'availability': data['availability'], 'revision': data['revision'],
                            'primary': data['research']['framework']['primary'] if data.get('research') else None})
    return {'verified': not mismatches and not unregistered,
            'checked_at': datetime.now(timezone.utc).isoformat(), 'commit': expected_commit,
            'projection_version': 'CILE-PUBLIC-RESEARCH-1', 'source_counts': audit['counts'],
            'public_register_count': len(registered), 'verified_http_records': len(checked),
            'unpopulated_sample_limit': 5, 'all_populated_records_checked': True,
            'mismatched_records': mismatches, 'unregistered_records': unregistered,
            'verified_records': checked,
            'scientific_approval_performed': False, 'private_content_exported': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-commit', default=os.environ.get('GITHUB_SHA'))
    args = parser.parse_args()
    result = check(args.expected_commit or current_commit())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result['verified']:
        raise SystemExit('public_research_verification_failed')


if __name__ == '__main__':
    main()
