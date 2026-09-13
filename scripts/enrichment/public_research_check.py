#!/usr/bin/env python3
"""Read-only source-to-public research check; never request or log raw proposals."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit, parse_qs
from urllib.request import Request
from urllib.error import HTTPError, URLError
from scripts.enrichment.service_client import call, current_commit, _PRIVATE_HTTP, ORIGIN


PUBLIC_ORIGIN = 'https://colazeta.github.io'
REGISTER_URL = PUBLIC_ORIGIN + '/criminal_infiltration_in_legal_economy_review/data/paper-register.json'


class PublicFetchError(RuntimeError):
    """Bounded transport metadata only, never response bodies or credentials."""
    def __init__(self, code, *, status=None, content_type=None):
        self.details = {'code': code}
        if status is not None:
            self.details['http_status'] = status
        if content_type is not None:
            self.details['content_type'] = content_type if content_type in {'application/json', 'text/html', 'text/plain'} else 'other'
        super().__init__(code)


def public_get(url):
    # Explicit public identity, no cookie/signature/session, no redirects. Check
    # the actual cross-origin browser contract rather than a privileged route.
    parsed = urlsplit(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    research = (parsed.scheme == 'https' and parsed.netloc == urlsplit(ORIGIN).netloc
                and parsed.path == '/api/public-paper-research' and not parsed.fragment
                and set(query) == {'id'} and len(query['id']) == 1
                and re.fullmatch(r'CAND-[A-Za-z0-9-]{1,100}', query['id'][0]))
    if not research and url != REGISTER_URL:
        raise RuntimeError('unexpected_public_origin')
    headers = {'Accept': 'application/json', 'Cache-Control': 'no-cache',
               'User-Agent': 'cile-public-research-check/1.0'}
    if research:
        headers['Origin'] = PUBLIC_ORIGIN
    try:
        with _PRIVATE_HTTP.open(Request(url, headers=headers), timeout=25) as response:
            if research and response.headers.get('Access-Control-Allow-Origin') != PUBLIC_ORIGIN:
                raise PublicFetchError('public_cors_mismatch')
            raw = response.read(4_000_001)
    except HTTPError as error:
        content_type = error.headers.get('Content-Type', '').split(';')[0].strip().lower()
        raise PublicFetchError('public_http_error', status=error.code, content_type=content_type) from None
    except (URLError, TimeoutError):
        raise PublicFetchError('public_transport_failure') from None
    if len(raw) > 4_000_000:
        raise PublicFetchError('public_response_limit')
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise PublicFetchError('public_decode_failure') from None


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
    register = fetcher(REGISTER_URL)
    registered = {r['id']: r for r in register['records']}
    # Verify every populated context and every blocked/stale record; sample at most
    # five unpopulated entries. The receipt states this denominator explicitly.
    selected = [r for r in rows if r['availability'] in {'available', 'withheld', 'stale'}]
    selected += [r for r in rows if r['availability'] == 'not_assessed'][:5]
    if len(selected) > 1000:
        raise RuntimeError('explicit_paged_audit_required')
    mismatches, unregistered, checked, transport_errors = [], [], [], []
    for row in selected:
        try:
            data = fetcher(ORIGIN + '/api/public-paper-research?' + urlencode({'id': row['id']}))
        except PublicFetchError as error:
            transport_errors.append({'id': row['id'], **error.details})
            continue
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
            checked.append({'id': row['id'], 'title': current['title'], 'availability': data['availability'], 'revision': data['revision'],
                            'primary': data['research']['framework']['primary'] if data.get('research') else None})
    return {'verified': not mismatches and not unregistered and not transport_errors,
            'checked_at': datetime.now(timezone.utc).isoformat(), 'commit': expected_commit,
            'projection_version': 'CILE-PUBLIC-RESEARCH-1', 'source_counts': audit['counts'],
            'public_register_count': len(registered), 'verified_http_records': len(checked),
            'unpopulated_sample_limit': 5, 'all_populated_records_checked': not transport_errors,
            'transport_errors': transport_errors,
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
