#!/usr/bin/env python3
"""Retain a bounded B-shard frontier of already-governed public full-text PDFs.

This runner performs no discovery and no rights inference. It consumes only current
CandidateRecords whose access coverage already records a successful governed PDF
fetch, acquires a real candidate-bound F1 lease, stores source text and original
bytes privately, verifies the authenticated reader route, and releases the lease.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path

from scripts.calibration.full_text_source_case import extract_text
from scripts.enrichment.service_client import call
from scripts.oa_acquisition import acquire_pdf

ROOT = Path(__file__).resolve().parents[2]
ACCESS = ROOT / 'data/curation/access_coverage.csv'
REGISTER = ROOT / 'site/data/paper-register.json'
CYCLE = json.loads((ROOT / 'config/archive-cycle.json').read_text(encoding='utf-8'))['review_id']
RETENTION_BASIS = 'Owner-authorised private research; no redistribution'
VERSION_LABEL = 'governed public-full-text manifestation; version not independently labelled'


def target_id(candidate_id: str) -> str:
    return hashlib.sha256(f'{CYCLE}:candidate:{candidate_id}'.encode()).hexdigest()


def owns_b(candidate_id: str) -> bool:
    return hashlib.sha256(candidate_id.encode()).digest()[0] % 2 == 1


def identity_text(value: str) -> str:
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()
    return ' '.join(re.findall(r'[a-z0-9]+', value))


def title_matches(title: str, text: str) -> bool:
    wanted = identity_text(title)
    head = identity_text(text[:30000])
    if wanted and wanted in head:
        return True
    words = wanted.split()
    significant = [word for word in words if len(word) >= 4]
    prefix = ' '.join(words[: min(8, len(words))])
    overlap = sum(word in head.split() for word in set(significant))
    required = max(1, int(len(set(significant)) * 0.8 + 0.999))
    return len(words) >= 4 and prefix in head and overlap >= required


def frontier(limit: int) -> list[tuple[dict, dict]]:
    records = json.loads(REGISTER.read_text(encoding='utf-8'))['records']
    by_id = {record['id']: record for record in records}
    if len(by_id) != len(records):
        raise RuntimeError('frontier_duplicate_candidate_id')
    selected = []
    with ACCESS.open(encoding='utf-8', newline='') as handle:
        for row in csv.DictReader(handle):
            candidate_id = row['candidate_id']
            record = by_id.get(candidate_id)
            if not record or not owns_b(candidate_id):
                continue
            if record.get('metadataStatus') != 'metadata_verified':
                continue
            if row.get('access_status') != 'open' or row.get('access_kind') != 'public_full_text':
                continue
            if row.get('evidence_source') != 'Governed PDF fetch' or not row.get('access_url', '').startswith('https://'):
                continue
            if identity_text(row.get('title', '')) != identity_text(record.get('title', '')):
                continue
            selected.append((record, row))
    selected.sort(key=lambda item: (item[0].get('registeredAt') or '9999', item[0]['id']))
    return selected[:limit]


def retain_one(record: dict, row: dict, expected_commit: str, service=call, acquire=acquire_pdf, extract=extract_text) -> dict:
    candidate_id = record['id']
    tid = target_id(candidate_id)
    existing = service('documents', expected_commit=expected_commit, target_id=tid).get('documents', [])
    if existing:
        return {'candidate_id': candidate_id, 'status': 'already_retained_current_input'}
    claim = service('document-retention-claim', expected_commit=expected_commit, target_id=tid)
    if claim.get('status') == 'leased':
        return {'candidate_id': candidate_id, 'status': 'leased_elsewhere'}
    if claim.get('status') != 'claimed' or claim.get('input_sha256') is None or claim.get('lease_token') is None:
        raise RuntimeError('frontier_claim_failed')
    checkpoint = {'lease_token': claim['lease_token']}
    stage = 'acquire'
    try:
        pdf, observation = acquire(row['access_url'])
        pdf_hash = hashlib.sha256(pdf).hexdigest()
        if observation.get('full_text_sha256') != pdf_hash or len(pdf) > 4194304:
            raise RuntimeError('frontier_pdf_integrity_failed')
        stage = 'extract'
        text = extract(pdf)
        if not title_matches(record['title'], text):
            raise RuntimeError('frontier_title_identity_failed')
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        stage = 'source_write'
        source = service('source-claimed', expected_commit=expected_commit, target_id=tid, checkpoint=checkpoint, source={
            'input_sha256': claim['input_sha256'],
            'source_url': observation['full_text_url'],
            'evidence_kind': 'full_text',
            'text': text,
            'version_label': VERSION_LABEL,
            'language': None,
            'retention_basis': RETENTION_BASIS,
            'licence_status': 'not_verified',
        })
        source_id = source.get('source_id')
        if not isinstance(source_id, str) or not re.fullmatch(r'[a-f0-9]{64}', source_id):
            raise RuntimeError('frontier_source_write_failed')
        stage = 'document_write'
        document = service('document-claimed', expected_commit=expected_commit, target_id=tid, checkpoint=checkpoint, document={
            'input_sha256': claim['input_sha256'],
            'source_id': source_id,
            'pdf_sha256': pdf_hash,
            'source_text_sha256': text_hash,
            'bytes_base64': base64.b64encode(pdf).decode(),
            'retention_basis': RETENTION_BASIS,
            'licence_status': 'not_verified',
            'licence_url': None,
            'attribution': record.get('authors') or record.get('title'),
            'visibility': 'private',
            'rights_verified': False,
        })
        document_id = document.get('document_id')
        if not isinstance(document_id, str):
            raise RuntimeError('frontier_document_write_failed')
        stage = 'document_readback'
        checked = service('document-check', expected_commit=expected_commit, target_id=tid, document_id=document_id)
        if checked.get('readable') is not True or checked.get('byte_length') != len(pdf) or checked.get('content_type') != 'application/pdf':
            raise RuntimeError('frontier_document_readback_failed')
        stage = 'release'
        released = service('document-retention-release', expected_commit=expected_commit, target_id=tid, checkpoint=checkpoint)
        if released.get('status') != 'released':
            raise RuntimeError('frontier_claim_release_failed')
        return {
            'candidate_id': candidate_id,
            'status': 'retained_readback_verified',
            'pdf_sha256': pdf_hash,
            'text_sha256': text_hash,
            'byte_length': len(pdf),
            'visibility': 'private',
            'scientific_validation': False,
        }
    except Exception as error:
        try:
            service('document-retention-abort', expected_commit=expected_commit, target_id=tid, checkpoint=checkpoint)
        except Exception:
            pass
        code = str(error)
        if not re.fullmatch(r'(?:frontier_[a-z_]+|OA [A-Z0-9_ -]+|document_[a-z_]+|enrichment_service_[a-z0-9_:]+)', code):
            code = 'frontier_retention_failed'
        raise RuntimeError(f'{stage}:{code}') from None


def run_frontier(expected_commit: str, limit: int = 3) -> list[dict]:
    results = []
    for record, row in frontier(limit):
        try:
            results.append(retain_one(record, row, expected_commit))
        except RuntimeError as error:
            results.append({'candidate_id': record['id'], 'status': 'failed', 'error_code': str(error)})
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-commit', default=os.environ.get('GITHUB_SHA'))
    parser.add_argument('--limit', type=int, default=3)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-f0-9]{40}', args.expected_commit or ''):
        parser.error('An exact reviewed/deployed commit is required.')
    if args.limit < 1 or args.limit > 6:
        parser.error('--limit must be between 1 and 6')
    results = run_frontier(args.expected_commit, args.limit)
    print(json.dumps({'status': 'frontier_retention_finished', 'results': results}, indent=2))
    if not any(item['status'] in {'retained_readback_verified', 'already_retained_current_input'} for item in results):
        raise SystemExit('frontier_retention_no_success')


if __name__ == '__main__':
    main()
