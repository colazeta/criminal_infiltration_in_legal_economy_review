"""Audit or reindex retained PDFs through the existing signed private service.

No arbitrary URL retrieval, discovery, scientific decision or public upload.
Output must be a private path outside the public repository. Resumption is by
candidate offset; indexing is idempotent and bound to unchanged source hashes.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
from scripts.enrichment.service_client import call
from scripts.enrichment.document_text import extract_document

ROOT = Path(__file__).resolve().parents[2]


def summarise(records):
    """Candidate counts, never counts of works or duplicated document versions."""
    groups = {}
    for row in records:
        groups.setdefault(row['candidate_id'], []).append(row)
    counts = dict.fromkeys(('registered', 'pdf_acquired', 'full_text_verified',
                           'text_extracted', 'analysed', 'validation_accepted',
                           'publicly_rehostable', 'private_only', 'rights_unresolved',
                           'full_text_missing'), 0)
    counts['registered'] = len(groups)
    for versions in groups.values():
        retained = any(r['acquisition_status'] == 'acquired' for r in versions)
        indexed = any(r['full_text_extraction_status'] == 'verified' for r in versions)
        counts['pdf_acquired'] += retained
        counts['full_text_missing'] += not retained
        counts['full_text_verified'] += indexed
        counts['text_extracted'] += indexed
        counts['analysed'] += any(r['analysed'] for r in versions)
        counts['validation_accepted'] += any(r['validation_accepted'] is True for r in versions)
        # Rows arrive newest first: old assertions never undo a rights withdrawal.
        latest = {}
        for row in versions:
            if row['content_sha256']:
                latest.setdefault(row['content_sha256'], row)
        public = any(r['redistribution_status'] == 'public_rehost_allowed' for r in latest.values())
        counts['publicly_rehostable'] += public
        counts['private_only'] += retained and not public
        counts['rights_unresolved'] += any(r['redistribution_status'] == 'rights_unresolved' for r in latest.values())
    return {**counts, 'canonical_works': None, 'included': None, 'assessment_completed': None,
            'basis': 'verified current candidate inventory; validation acceptance is separate from unattested assessment completion'}


def run(expected_commit, *, offset=0, pages=1, reindex=False, revision=None, service=call):
    results = []
    cycle = json.loads((ROOT / 'config/archive-cycle.json').read_text())['review_id']
    next_offset = offset
    for _ in range(pages):
        page = service('document-coverage', expected_commit=expected_commit,
                       checkpoint={'offset': next_offset, 'limit': 25, 'revision': revision})
        if page.get('protocol') != 'CILE-DOCUMENT-COVERAGE-1' or page.get('archive_commit') != expected_commit:
            raise RuntimeError('document_coverage_revision_mismatch')
        if revision is not None and page['identity_revision'] != revision:
            raise RuntimeError('document_inventory_changed')
        revision = page['identity_revision']
        for row in page['records']:
            if reindex and row['document_id'] and row['full_text_extraction_status'] != 'verified':
                target = hashlib.sha256(f"{cycle}:candidate:{row['candidate_id']}".encode()).hexdigest()
                try:
                    packet = service('document-packet', expected_commit=expected_commit,
                                     target_id=target, document_id=row['document_id'])
                    text, attestation = extract_document(base64.b64decode(packet['bytes_base64'], validate=True))
                    if text != packet['text'] or attestation['text_sha256'] != packet['document']['source_text_sha256']:
                        # Preserve old scientific spans; do not silently attach them to new text.
                        raise RuntimeError('document_legacy_extraction_differs')
                    service('document-index', expected_commit=expected_commit, target_id=target,
                            document_id=row['document_id'], document=attestation)
                    row = {**row, 'backfill_status': 'indexed_and_verified'}
                except Exception as error:
                    code = str(error)
                    allowed = {'document_legacy_extraction_differs', 'document_ocr_required',
                               'document_parser_failed', 'document_extraction_quality_failed'}
                    row = {**row, 'backfill_status': 'blocked',
                           'backfill_blocker': code if code in allowed else 'document_backfill_failed'}
            results.append(row)
        next_offset = page['next_offset']
        if next_offset is None:
            break
    complete = offset == 0 and next_offset is None
    return {'protocol': 'CILE-DOCUMENT-COVERAGE-1', 'archive_commit': expected_commit,
            'private_inventory_observed': True, 'counts': summarise(results) if complete else None,
            'identity_revision': revision, 'observation_mode': 'per_candidate_not_atomic_snapshot',
            'records': results, 'next_offset': next_offset, 'start_offset': offset,
            'complete_inventory': complete,
            'note': 'Coverage is observed before each attempted reindex; rerun audit for final counts.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--pages', type=int, default=1)
    parser.add_argument('--reindex', action='store_true')
    parser.add_argument('--revision', help='Identity revision from a preceding page, required with nonzero offset')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.pages <= 20 or not 0 <= args.offset <= 10000:
        parser.error('Bounded pages/offset required')
    if args.output.resolve().is_relative_to(ROOT):
        parser.error('Private inventory must remain outside the public repository')
    report = run(args.expected_commit, offset=args.offset, pages=args.pages, reindex=args.reindex, revision=args.revision)
    fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump(report, out, ensure_ascii=False)
    print(json.dumps({'private_report_written': True, 'records': len(report['records']),
                      'next_offset': report['next_offset'], 'complete_inventory': report['complete_inventory']}))


if __name__ == '__main__':
    main()
