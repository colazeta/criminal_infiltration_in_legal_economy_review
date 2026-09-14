#!/usr/bin/env python3
"""Runtime policy for the bounded full-text calibration development harness.

Operational model timeouts remain outside the scientific extractor fingerprint.
This wrapper also selects the reviewed bounded calibration configuration used by
this execution. Scientific settings are incorporated into an explicit stable
source-independent fingerprint before the base harness is called.
"""
from scripts.calibration import full_text_development as development

CHUNK_TIMEOUT_SECONDS = 600
SYNTHESIS_TIMEOUT_SECONDS = 720

# The 18k-character configuration timed out twice before completing its first
# chunk on the current four-CPU runner. Smaller windows preserve complete source
# coverage through overlap while increasing total atom capacity (about 14 chunks
# × 8 atoms rather than 5 × 18) and bounding each individual model request.
SCIENTIFIC_CONFIG = {
    'chunk_chars': 6000,
    'chunk_overlap': 400,
    'max_atoms_per_chunk': 8,
    'chunk_max_tokens': 1000,
    'synthesis_max_tokens': 3500,
}

_ORIGINAL_CHUNK_REQUEST = development.chunk_request
_ORIGINAL_EXTRACTOR_FINGERPRINT = development.extractor_fingerprint


def runtime_extractor_fingerprint():
    stable = {
        'protocol': development.PROTOCOL,
        'model': development.MODEL,
        **SCIENTIFIC_CONFIG,
        'chunk_system': development.CHUNK_SYSTEM,
        'synthesis_system': development.SYNTHESIS_SYSTEM,
        'field_by_entity': {key: sorted(value) for key, value in development.FIELD_BY_ENTITY.items()},
        'paper_enrichment_schema_sha256': development.schema_digest(),
        'decoder_contract': 'llama.cpp-json-schema;temperature=0;seed=0',
    }
    return development.sha(development.canonical(stable))


def bounded_chunk_request(chunk):
    request = _ORIGINAL_CHUNK_REQUEST(chunk)
    request['max_tokens'] = SCIENTIFIC_CONFIG['chunk_max_tokens']
    return request


def runtime_timeout(requested):
    if not isinstance(requested, (int, float)) or requested <= 0:
        raise ValueError('fulltext_runtime_timeout_invalid')
    if requested <= 300:
        return max(requested, CHUNK_TIMEOUT_SECONDS)
    return max(requested, SYNTHESIS_TIMEOUT_SECONDS)


def runtime_post(original, payload, timeout=300):
    try:
        return original(payload, timeout=runtime_timeout(timeout))
    except TimeoutError:
        raise RuntimeError('fulltext_model_timeout') from None


def main():
    original_post = development.post_model
    original_chunk_chars = development.CHUNK_CHARS
    original_chunk_overlap = development.CHUNK_OVERLAP
    original_max_atoms = development.MAX_ATOMS_PER_CHUNK
    original_chunk_request = development.chunk_request
    original_fingerprint = development.extractor_fingerprint

    development.CHUNK_CHARS = SCIENTIFIC_CONFIG['chunk_chars']
    development.CHUNK_OVERLAP = SCIENTIFIC_CONFIG['chunk_overlap']
    development.MAX_ATOMS_PER_CHUNK = SCIENTIFIC_CONFIG['max_atoms_per_chunk']
    development.chunk_request = bounded_chunk_request
    development.extractor_fingerprint = runtime_extractor_fingerprint
    development.post_model = lambda payload, timeout=300: runtime_post(original_post, payload, timeout)
    try:
        development.main()
    finally:
        development.post_model = original_post
        development.CHUNK_CHARS = original_chunk_chars
        development.CHUNK_OVERLAP = original_chunk_overlap
        development.MAX_ATOMS_PER_CHUNK = original_max_atoms
        development.chunk_request = original_chunk_request
        development.extractor_fingerprint = original_fingerprint


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error)
        if code.startswith('fulltext_') or code.startswith('OA '):
            raise SystemExit(code) from None
        raise SystemExit('fulltext_calibration_development_failed') from None
