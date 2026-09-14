#!/usr/bin/env python3
"""Import one reviewed actual-paper bibliography into the existing private store.

The manifest contains public bibliographic metadata only. Current target/input/source
identifiers are resolved privately at execution time and are never printed or
committed. This script makes no external bibliographic-provider call and creates no
CandidateRecord, citation nomination, scientific classification or completion receipt.
"""
import argparse
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

from scripts.calibration.full_text_source_case import candidate
from scripts.enrichment.service_client import ORIGIN, call

ROOT = Path(__file__).resolve().parents[2]
TOP_FIELDS = {
    'protocol', 'candidate_id', 'source_url', 'source_text_sha256', 'version_label',
    'coverage', 'declared_count', 'entries'
}
ENTRY_FIELDS = {
    'position', 'title', 'authors', 'year', 'venue', 'doi', 'url',
    'source_locator', 'unresolved_identity'
}


def validate_manifest(data):
    if not isinstance(data, dict) or set(data) != TOP_FIELDS:
        raise RuntimeError('invalid_bibliography_manifest')
    if data['protocol'] != 'CILE-VERIFIED-BIBLIOGRAPHY-1':
        raise RuntimeError('invalid_bibliography_manifest')
    if not re.fullmatch(r'[a-f0-9]{64}', str(data['source_text_sha256'])):
        raise RuntimeError('invalid_bibliography_manifest')
    if data['coverage'] != 'source_complete':
        raise RuntimeError('bibliography_seed_must_be_source_complete')
    if not isinstance(data['declared_count'], int) or data['declared_count'] < 1:
        raise RuntimeError('invalid_bibliography_manifest')
    if not isinstance(data['entries'], list) or len(data['entries']) != data['declared_count']:
        raise RuntimeError('bibliography_count_conflict')
    if [entry.get('position') for entry in data['entries']] != list(range(1, data['declared_count'] + 1)):
        raise RuntimeError('bibliography_positions_not_contiguous')
    for entry in data['entries']:
        if not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS:
            raise RuntimeError('invalid_bibliography_manifest')
        if not isinstance(entry['authors'], list) or any(not isinstance(author, str) or not author.strip() for author in entry['authors']):
            raise RuntimeError('invalid_bibliography_manifest')
        if entry['title'] is not None and (not isinstance(entry['title'], str) or not entry['title'].strip()):
            raise RuntimeError('invalid_bibliography_manifest')
        if entry['year'] is not None and (not isinstance(entry['year'], int) or not 1000 <= entry['year'] <= 2100):
            raise RuntimeError('invalid_bibliography_manifest')
        if not isinstance(entry['source_locator'], str) or not entry['source_locator'].startswith('IZA DP 13028, References, p. '):
            raise RuntimeError('invalid_bibliography_manifest')
        if type(entry['unresolved_identity']) is not bool:
            raise RuntimeError('invalid_bibliography_manifest')
    record = candidate(data['candidate_id'], data['source_url'])
    if record['id'] != data['candidate_id']:
        raise RuntimeError('bibliography_candidate_identity')
    return data


def _public_readback(candidate_id):
    url = ORIGIN + '/api/public-paper-assets?' + urllib.parse.urlencode({'id': candidate_id})
    request = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'cile-bibliography-readback/1.0'})
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError('bibliography_public_readback_failed')
        payload = json.load(response)
    return payload


def import_verified(manifest, expected_commit, service=call, public_readback=_public_readback):
    data = validate_manifest(manifest)
    record = candidate(data['candidate_id'], data['source_url'])
    cycle = json.loads((ROOT / 'config/archive-cycle.json').read_text())['review_id']
    target_id = hashlib.sha256((cycle + ':candidate:' + record['id']).encode()).hexdigest()
    packet = service('packet', expected_commit=expected_commit, target_id=target_id)
    target = packet.get('target')
    if not target or target.get('record_id') != record['id']:
        raise RuntimeError('bibliography_target_unavailable')
    sources = packet.get('sources') or []
    source = next((item for item in sources
                   if item.get('evidence_kind') == 'full_text'
                   and item.get('source_url') == data['source_url']
                   and item.get('content_sha256') == data['source_text_sha256']), None)
    if source is None:
        raise RuntimeError('bibliography_retained_source_unavailable')
    if source.get('version_label') != data['version_label']:
        raise RuntimeError('bibliography_source_version_mismatch')

    payload = {
        'input_sha256': target['input_sha256'],
        'source_id': source['source_id'],
        'scope': 'paper_bibliography',
        'coverage': data['coverage'],
        'declared_count': data['declared_count'],
        'entries': data['entries'],
    }
    result = service('bibliography', expected_commit=expected_commit, target_id=target_id, bibliography=payload)
    if not isinstance(result, dict) or 'replayed' not in result:
        raise RuntimeError('bibliography_private_readback_failed')

    public = public_readback(record['id'])
    bibliography = public.get('bibliography') if isinstance(public, dict) else None
    if (public.get('availability') != 'registered' or not isinstance(bibliography, dict)
            or bibliography.get('scope') != 'paper_bibliography'
            or bibliography.get('coverage') != 'source_complete'
            or bibliography.get('declared_count') != data['declared_count']
            or bibliography.get('entries_count') != data['declared_count']
            or len(bibliography.get('entries') or []) != data['declared_count']
            or bibliography.get('next_offset') is not None
            or not re.fullmatch(r'[a-f0-9]{64}', str(bibliography.get('revision') or ''))):
        raise RuntimeError('bibliography_public_readback_failed')
    public_positions = [entry.get('position') for entry in bibliography['entries']]
    if public_positions != list(range(1, data['declared_count'] + 1)):
        raise RuntimeError('bibliography_public_readback_failed')
    return {
        'candidate_id': record['id'],
        'status': 'actual_bibliography_readback_verified',
        'replayed': bool(result['replayed']),
        'coverage': bibliography['coverage'],
        'declared_count': bibliography['declared_count'],
        'entries_count': bibliography['entries_count'],
        'public_projection_verified': True,
        'revision': bibliography['revision'],
        'scientific_validation': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'config/verified-bibliography-seed.json')
    parser.add_argument('--expected-commit', default=os.environ.get('GITHUB_SHA'))
    args = parser.parse_args()
    if not re.fullmatch(r'[a-f0-9]{40}', args.expected_commit or ''):
        parser.error('An exact reviewed/deployed commit is required.')
    result = import_verified(json.loads(args.manifest.read_text()), args.expected_commit)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error)
        if not re.fullmatch(r'(?:bibliography_[a-z_]+|invalid_bibliography_manifest|enrichment_service_[a-z0-9_:]+)', code):
            code = 'bibliography_import_failed'
        raise SystemExit(code) from None
