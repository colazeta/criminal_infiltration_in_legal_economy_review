"""Verify every current candidate's archived annotations against public delivery."""
import argparse
import json
import os
from urllib.parse import urlencode
from urllib.request import Request
from scripts.enrichment.service_client import call, current_commit, ORIGIN, _PRIVATE_HTTP
from scripts.enrichment.public_research_check import digest, PUBLIC_ORIGIN


def fetch(parameters):
    url = ORIGIN + '/api/public-paper-research?' + urlencode(parameters)
    try:
        with _PRIVATE_HTTP.open(Request(url, headers={'Accept': 'application/json',
                'Origin': PUBLIC_ORIGIN, 'Cache-Control': 'no-cache'}), timeout=30) as response:
            if response.headers.get('Access-Control-Allow-Origin') != PUBLIC_ORIGIN:
                raise RuntimeError('annotation_cors_invalid')
            raw = response.read(4000001)
        if len(raw) > 4000000:
            raise RuntimeError('annotation_response_limit')
        return json.loads(raw)
    except Exception:
        raise RuntimeError('annotation_public_transport_failed') from None


def check(commit, caller=call, reader=fetch):
    audit = caller('annotation-projection-audit', expected_commit=commit)
    if (audit.get('contract') != 'CILE-ANNOTATION-PROJECTION-AUDIT-1'
            or audit.get('commit') != commit or audit.get('private_content_exported') is not False):
        raise RuntimeError('annotation_audit_contract_invalid')
    records = audit['records']
    expected = {r['candidate_id']: r for r in records}
    if len(expected) != len(records) or len(records) > 10000:
        raise RuntimeError('annotation_population_invalid')
    indexed, cursor = {}, 0
    while cursor is not None:
        page = reader({'view': 'index', 'cursor': cursor, 'revision': audit['index_revision']})
        if (page.get('projection_version') != 'CILE-PUBLIC-INDEX-2' or page.get('index_revision') != audit['index_revision']
                or page.get('total') != len(records) or not isinstance(page.get('records'), list) or len(page['records']) > 50):
            raise RuntimeError('annotation_index_invalid')
        for row in page['records']:
            identifier = row['candidate']['id']
            if identifier not in expected or identifier in indexed:
                raise RuntimeError('annotation_index_identity_invalid')
            source = expected[identifier]
            if (row['annotation_summary'] != {'count': source['annotations'], 'conflicts': source['conflicts'], 'revision': source['revision']}
                    or row['classification'] != source['classification']):
                raise RuntimeError('annotation_index_content_mismatch')
            indexed[identifier] = row
        next_cursor = page.get('next_cursor')
        if next_cursor is not None and (type(next_cursor) is not int or next_cursor != cursor + len(page['records']) or next_cursor <= cursor):
            raise RuntimeError('annotation_index_cursor_invalid')
        cursor = next_cursor
    if set(indexed) != set(expected):
        raise RuntimeError('annotation_population_incomplete')
    for identifier, row in expected.items():
        data = reader({'view': 'annotations', 'id': identifier})
        unsigned = {k: v for k, v in data.items() if k != 'revision'}
        if (data.get('projection_version') != 'CILE-PUBLIC-ANNOTATIONS-1' or data.get('candidate_id') != identifier
                or data.get('revision') != row['revision'] or digest(unsigned) != row['revision']
                or len(data.get('annotations', [])) != row['annotations'] or data.get('conflicts') != row['conflicts']):
            raise RuntimeError('annotation_sheet_mismatch')
    # An observation that changes during delivery is never certified as one release.
    final = caller('annotation-projection-audit', expected_commit=commit)
    if final != audit:
        raise RuntimeError('annotation_projection_changed')
    return {'contract': 'CILE-ANNOTATION-PUBLIC-VERIFICATION-1', 'commit': commit,
            'index_revision': audit['index_revision'], 'candidates_checked': len(expected),
            'annotations_checked': sum(r['annotations'] for r in records),
            'all_current_candidates_verified': True, 'scientific_approval_performed': False,
            'private_content_exported': False}


def compatibility(reader=fetch):
    """Release precondition only; the protected deployment verifies all records."""
    page = reader({'view': 'index', 'cursor': 0})
    if page.get('projection_version') != 'CILE-PUBLIC-INDEX-2' or not isinstance(page.get('records'), list):
        raise RuntimeError('annotation_contract_not_deployed')
    if page['records']:
        row = page['records'][0]
        data = reader({'view': 'annotations', 'id': row['candidate']['id']})
        if data.get('projection_version') != 'CILE-PUBLIC-ANNOTATIONS-1' or data.get('revision') != row['annotation_summary']['revision']:
            raise RuntimeError('annotation_contract_incompatible')
    return {'compatible': True, 'projection_version': page['projection_version'], 'full_population_verification': False}


if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--compatibility-only', action='store_true')
        args = parser.parse_args()
        result = compatibility() if args.compatibility_only else check(os.environ.get('GITHUB_SHA') or current_commit())
        print(json.dumps(result, indent=2))
    except Exception:
        raise SystemExit('annotation_projection_verification_failed') from None
