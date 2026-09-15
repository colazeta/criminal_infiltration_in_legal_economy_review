#!/usr/bin/env python3
"""Resume exact full-text chunk inference from authenticated private checkpoints.

This wrapper does not change the scientific request, extractor fingerprint, model,
seed, decoder, evidence policy or proposal validation. It only reuses a raw chunk
output when the candidate id, extractor fingerprint and complete request hash are
identical. Checkpoints remain in the existing authenticated private store and no
source/model output is printed or written to GitHub artifacts by this wrapper.
"""
import json
import os
import re
import sys

from scripts.calibration import full_text_development as development
from scripts.calibration import full_text_development_run as runtime
from scripts.enrichment.service_client import call as service_call

PROTOCOL = 'CILE-FULLTEXT-DEV-CHUNK-1'
_ORIGINAL_RUNTIME_POST = runtime.runtime_post


def candidate_id_from_argv(argv=None):
    values = list(sys.argv if argv is None else argv)
    try:
        value = values[values.index('--candidate-id') + 1]
    except (ValueError, IndexError):
        raise RuntimeError('fulltext_checkpoint_candidate_unavailable') from None
    if not re.fullmatch(r'CAND-[A-Z0-9][A-Z0-9._-]{1,199}', value):
        raise RuntimeError('fulltext_checkpoint_candidate_unavailable')
    return value


def exact_commit():
    value = os.environ.get('GITHUB_SHA', '')
    if not re.fullmatch(r'[0-9a-f]{40}', value):
        raise RuntimeError('fulltext_checkpoint_commit_unavailable')
    return value


def chunk_request(payload):
    if not isinstance(payload, dict):
        return None
    try:
        user = json.loads(payload['messages'][1]['content'])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None
    if not isinstance(user, dict) or set(user) != {'chunk_id', 'text'}:
        return None
    if not re.fullmatch(r'chunk-[1-9][0-9]{0,3}', str(user.get('chunk_id'))):
        return None
    if not isinstance(user.get('text'), str):
        return None
    return user


def chunk_identity(payload, candidate_id):
    user = chunk_request(payload)
    if user is None:
        return None
    return {
        'protocol': PROTOCOL,
        'candidate_id': candidate_id,
        'extractor_fingerprint': runtime.runtime_extractor_fingerprint(),
        'request_sha256': development.sha(development.canonical(payload)),
        'chunk_id': user['chunk_id'],
    }


def resumable_post(original, payload, timeout=300, *, service=service_call, candidate_id=None):
    """Return a matching private checkpoint or persist one newly generated chunk."""
    if not os.environ.get('CURATOR_SESSION_SECRET'):
        return _ORIGINAL_RUNTIME_POST(original, payload, timeout)
    if chunk_request(payload) is None:
        return _ORIGINAL_RUNTIME_POST(original, payload, timeout)
    candidate_id = candidate_id or candidate_id_from_argv()
    identity = chunk_identity(payload, candidate_id)
    commit = exact_commit()
    try:
        result = service('development-checkpoint-get', expected_commit=commit, checkpoint=identity)
    except RuntimeError as error:
        raise RuntimeError('fulltext_checkpoint_service_unavailable') from error
    if result.get('status') == 'found':
        checkpoint = result.get('checkpoint')
        if not isinstance(checkpoint, dict) or any(checkpoint.get(key) != value for key, value in identity.items()):
            raise RuntimeError('fulltext_checkpoint_identity_mismatch')
        output = checkpoint.get('output')
        runtime._validate_original_atom_contracts([{'id': identity['chunk_id']}], [output])
        print(json.dumps({
            'event': 'private_chunk_checkpoint', 'candidate_id': candidate_id,
            'chunk_id': identity['chunk_id'], 'status': 'reused',
            'request_sha256': identity['request_sha256'],
        }, separators=(',', ':')))
        return output
    if result.get('status') != 'missing':
        raise RuntimeError('fulltext_checkpoint_service_invalid_response')

    output = _ORIGINAL_RUNTIME_POST(original, payload, timeout)
    runtime._validate_original_atom_contracts([{'id': identity['chunk_id']}], [output])
    try:
        receipt = service('development-checkpoint-put', expected_commit=commit, checkpoint={**identity, 'output': output})
    except RuntimeError as error:
        if 'development_checkpoint_conflict' in str(error):
            raise RuntimeError('fulltext_checkpoint_conflict') from error
        raise RuntimeError('fulltext_checkpoint_service_unavailable') from error
    if receipt.get('status') != 'stored' or receipt.get('request_sha256') != identity['request_sha256']:
        raise RuntimeError('fulltext_checkpoint_service_invalid_response')
    print(json.dumps({
        'event': 'private_chunk_checkpoint', 'candidate_id': candidate_id,
        'chunk_id': identity['chunk_id'], 'status': 'stored',
        'request_sha256': identity['request_sha256'],
        'output_sha256': receipt.get('output_sha256'),
    }, separators=(',', ':')))
    return output


def main():
    original = runtime.runtime_post
    runtime.runtime_post = resumable_post
    try:
        runtime.main()
    finally:
        runtime.runtime_post = original


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error)
        if code.startswith('fulltext_') or code.startswith('OA '):
            raise SystemExit(code) from None
        raise SystemExit('fulltext_calibration_development_failed') from None
