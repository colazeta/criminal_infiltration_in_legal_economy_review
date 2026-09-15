#!/usr/bin/env python3
"""Persist one structurally valid full-text calibration proposal through the private store.

The bridge is deliberately narrow. It reuses exact private chunk checkpoints, reads an
already-retained candidate-bound full-text source and original PDF through the existing
authenticated service, reruns only bounded synthesis/linking, remaps calibration-local
source/target identifiers to the current production-private target, and delegates the
actual atomic proposal write plus readback to ``storeExtraction`` via the existing
``proposal`` service operation.

This does not create or import a calibration receipt, adjudication receipt, completion
receipt, canonical identity decision, classification acceptance or public full text.
Missing checkpoints, stale identity, ambiguous retained sources or reader failures are
fail-closed and never trigger new chunk inference.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from scripts.calibration import full_text_development as development
from scripts.calibration import full_text_development_run as runtime
from scripts.calibration import full_text_development_resume_v2 as v2
from scripts.calibration import full_text_development_resume_v5 as v5
from scripts.enrichment.service_client import call as service_call

ROOT = Path(__file__).resolve().parents[2]
HEX64 = re.compile(r'^[0-9a-f]{64}$')
SHA40 = re.compile(r'^[0-9a-f]{40}$')
CANDIDATE = re.compile(r'^CAND-[A-Za-z0-9][A-Za-z0-9._-]{1,199}$')


def _sha(value):
    if isinstance(value, str):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def production_target_id(candidate_id):
    if not CANDIDATE.fullmatch(candidate_id or ''):
        raise RuntimeError('fulltext_production_candidate_invalid')
    cycle = json.loads((ROOT / 'config/archive-cycle.json').read_text())['review_id']
    return _sha(cycle + ':candidate:' + candidate_id)


def retained_binding(candidate_id, source_url, pdf_sha256, text_sha256, expected_visibility,
                     expected_commit, service=service_call):
    if not SHA40.fullmatch(expected_commit or ''):
        raise RuntimeError('fulltext_production_commit_invalid')
    if not HEX64.fullmatch(pdf_sha256 or '') or not HEX64.fullmatch(text_sha256 or ''):
        raise RuntimeError('fulltext_production_hash_invalid')
    if expected_visibility not in {'private', 'public'}:
        raise RuntimeError('fulltext_production_visibility_invalid')

    target_id = production_target_id(candidate_id)
    packet = service('packet', expected_commit=expected_commit, target_id=target_id)
    target = packet.get('target') if isinstance(packet, dict) else None
    sources = packet.get('sources') if isinstance(packet, dict) else None
    if not isinstance(target, dict) or target.get('record_id') != candidate_id \
            or target.get('target_id') != target_id:
        raise RuntimeError('fulltext_production_target_unavailable')
    if not HEX64.fullmatch(str(target.get('input_sha256', ''))):
        raise RuntimeError('fulltext_production_target_invalid')
    if not isinstance(sources, list):
        raise RuntimeError('fulltext_production_source_unavailable')

    matches = [source for source in sources if (
        isinstance(source, dict)
        and source.get('evidence_kind') == 'full_text'
        and source.get('source_url') == source_url
        and source.get('content_sha256') == text_sha256
        and isinstance(source.get('source_id'), str)
        and isinstance(source.get('text'), str)
        and _sha(source['text']) == text_sha256
    )]
    if len(matches) != 1:
        raise RuntimeError('fulltext_production_source_ambiguous')
    source = matches[0]

    document_rows = service('documents', expected_commit=expected_commit, target_id=target_id)
    documents = document_rows.get('documents') if isinstance(document_rows, dict) else None
    if not isinstance(documents, list):
        raise RuntimeError('fulltext_production_document_unavailable')
    docs = [doc for doc in documents if (
        isinstance(doc, dict)
        and doc.get('source_url') == source_url
        and doc.get('pdf_sha256') == pdf_sha256
        and doc.get('visibility') == expected_visibility
        and isinstance(doc.get('document_id'), str)
        and isinstance(doc.get('byte_length'), int)
        and doc['byte_length'] > 0
    )]
    if len(docs) != 1:
        raise RuntimeError('fulltext_production_document_ambiguous')
    document = docs[0]
    checked = service(
        'document-check', expected_commit=expected_commit, target_id=target_id,
        document_id=document['document_id'],
    )
    if not isinstance(checked, dict) or checked.get('readable') is not True:
        raise RuntimeError('fulltext_production_document_reader_failed')
    if checked.get('content_type') != 'application/pdf' or checked.get('byte_length') != document['byte_length']:
        raise RuntimeError('fulltext_production_document_reader_failed')
    if checked.get('etag') != '"' + pdf_sha256 + '"':
        raise RuntimeError('fulltext_production_document_hash_mismatch')

    return {
        'target': target,
        'source': source,
        'document': document,
        'text': source['text'],
        'source_url': source_url,
        'pdf_sha256': pdf_sha256,
        'text_sha256': text_sha256,
        'expected_visibility': expected_visibility,
    }


def remap_proposal(payload, binding):
    if not isinstance(payload, dict) or payload.get('status') != 'structurally_valid_unreviewed':
        raise RuntimeError('fulltext_production_proposal_not_structurally_valid')
    if payload.get('scientific_validation') is not False or payload.get('production_writes') != 0:
        raise RuntimeError('fulltext_production_development_scope_invalid')
    if payload.get('source_url') != binding['source_url'] or payload.get('pdf_sha256') != binding['pdf_sha256'] \
            or payload.get('text_sha256') != binding['text_sha256']:
        raise RuntimeError('fulltext_production_source_binding_mismatch')

    proposal = payload.get('proposal')
    if not isinstance(proposal, dict):
        raise RuntimeError('fulltext_production_proposal_missing')
    target = binding['target']
    if proposal.get('input_sha256') != target.get('input_sha256'):
        raise RuntimeError('fulltext_production_input_stale')
    source_ids = proposal.get('source_ids')
    if not isinstance(source_ids, list) or len(source_ids) != 1 or not isinstance(source_ids[0], str):
        raise RuntimeError('fulltext_production_calibration_source_invalid')
    calibration_source_id = source_ids[0]
    spans = proposal.get('spans')
    if not isinstance(spans, list) or any(
        not isinstance(span, dict) or span.get('source_id') != calibration_source_id for span in spans
    ):
        raise RuntimeError('fulltext_production_calibration_source_invalid')

    remapped = copy.deepcopy(proposal)
    remapped['target_id'] = target['target_id']
    remapped['source_ids'] = [binding['source']['source_id']]
    for span in remapped['spans']:
        span['source_id'] = binding['source']['source_id']
    return remapped


def persist_proposal(payload, binding, expected_commit, service=service_call):
    proposal = remap_proposal(payload, binding)
    result = service(
        'proposal', expected_commit=expected_commit,
        target_id=binding['target']['target_id'], proposal=proposal,
    )
    if not isinstance(result, dict) or result.get('scientific_status') != 'proposed' \
            or not isinstance(result.get('proposal_id'), str) or type(result.get('replayed')) is not bool:
        raise RuntimeError('fulltext_production_proposal_readback_failed')
    return {
        'candidate_id': binding['target']['record_id'],
        'status': 'proposal_persisted_readback_verified',
        'replayed': result['replayed'],
        'scientific_status': 'proposed',
        'scientific_validation': False,
        'accepted': False,
        'completed': False,
    }


def run(args, service=service_call):
    commit = os.environ.get('CALIBRATION_CHECKPOINT_SERVICE_COMMIT', '')
    binding = retained_binding(
        args.candidate_id, args.url, args.expected_pdf_sha256, args.expected_text_sha256,
        args.expected_visibility, commit, service,
    )

    original_acquire = development.acquire_pdf
    original_extract = development.extract_text
    original_runtime_checkpoint = runtime.runtime_checkpoint
    original_resolution_checkpoint = runtime._persist_resolution_checkpoint
    original_pass_limit = v2.pass_limit
    original_requires_complete = v2.pass_requires_complete
    original_argv = sys.argv
    receipt = {'value': None}
    output = Path(os.environ.get('RUNNER_TEMP', '/tmp')) / 'fulltext-production-proposal.noartifact'
    output.unlink(missing_ok=True)

    def retained_acquire(url):
        if url != binding['source_url']:
            raise RuntimeError('fulltext_production_source_binding_mismatch')
        return b'private-retained-pdf-verified-by-authenticated-reader', {
            'full_text_sha256': binding['pdf_sha256'],
            'full_text_url': binding['source_url'],
        }

    def retained_extract(_pdf):
        return binding['text']

    def private_checkpoint(_output, payload):
        enriched = runtime.runtime_checkpoint_payload(payload)
        runtime.RUNTIME_CHECKPOINT['output'] = None
        runtime.RUNTIME_CHECKPOINT['payload'] = copy.deepcopy(payload)
        if enriched.get('status') == 'structurally_valid_unreviewed':
            if receipt['value'] is not None:
                raise RuntimeError('fulltext_production_duplicate_persistence')
            receipt['value'] = persist_proposal(enriched, binding, commit, service)

    def private_resolution_checkpoint():
        prior = runtime.RUNTIME_CHECKPOINT.get('payload')
        if not isinstance(prior, dict):
            raise RuntimeError('fulltext_resolution_checkpoint_unavailable')
        runtime.RUNTIME_CHECKPOINT['payload'] = {
            **copy.deepcopy(prior), 'status': 'evidence_resolution_complete_model_pending',
        }

    development.acquire_pdf = retained_acquire
    development.extract_text = retained_extract
    runtime.runtime_checkpoint = private_checkpoint
    runtime._persist_resolution_checkpoint = private_resolution_checkpoint
    v2.pass_limit = lambda: 0
    v2.pass_requires_complete = lambda: True
    sys.argv = [
        original_argv[0],
        '--candidate-id', args.candidate_id,
        '--url', args.url,
        '--expected-pdf-sha256', args.expected_pdf_sha256,
        '--expected-text-sha256', args.expected_text_sha256,
        '--output', str(output),
    ]
    try:
        v5.main()
        if output.exists():
            raise RuntimeError('fulltext_production_artifact_forbidden')
    finally:
        sys.argv = original_argv
        development.acquire_pdf = original_acquire
        development.extract_text = original_extract
        runtime.runtime_checkpoint = original_runtime_checkpoint
        runtime._persist_resolution_checkpoint = original_resolution_checkpoint
        v2.pass_limit = original_pass_limit
        v2.pass_requires_complete = original_requires_complete
        output.unlink(missing_ok=True)

    if receipt['value'] is None:
        raise RuntimeError('fulltext_production_proposal_not_persisted')
    return receipt['value']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-id', required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--expected-pdf-sha256', required=True)
    parser.add_argument('--expected-text-sha256', required=True)
    parser.add_argument('--expected-visibility', choices=['private', 'public'], required=True)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error)
        if code.startswith('fulltext_') or code.startswith('OA '):
            raise SystemExit(code) from None
        raise SystemExit('fulltext_production_proposal_persistence_failed') from None
