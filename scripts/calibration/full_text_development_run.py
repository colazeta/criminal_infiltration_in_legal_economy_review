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
# The first 6k/1,000-token execution returned an explicit incomplete model output
# rather than timing out. Eight governed atoms can legitimately require more than
# 1,000 output tokens, so raise only the response budget while retaining the same
# source-window size, atom cap, evidence contract and finite runtime.
SCIENTIFIC_CONFIG = {
    'chunk_chars': 6000,
    'chunk_overlap': 400,
    'max_atoms_per_chunk': 8,
    'chunk_max_tokens': 1600,
    'synthesis_max_tokens': 3500,
}

# Run 34864185215 reached literal-evidence validation but failed because at least
# one model-returned exact quote occurred more than once inside its source window.
# Do not guess which occurrence was intended and do not weaken the validator.
# Instead require the model to extend a repeated quote with literal surrounding
# text until the evidence locator is unique, or to omit that atom. The downstream
# source-first comparison will measure any resulting omission.
EVIDENCE_UNIQUENESS_SUFFIX = """Evidence location is part of the evidence contract. Before emitting an atom,
ensure the exact evidence substring occurs exactly once in this source window. If the shortest adequate
quote repeats, extend it with exact contiguous surrounding source words until it is unique while remaining
within the evidence length limit. If no exact unique substring supports the complete value, omit the atom.
Never invent an occurrence index, silently choose between repeated matches, or paraphrase the evidence."""

# Run 34876598941 showed that prompt-only recovery is not sufficient: a model can
# still emit an atom whose evidence is absent or repeated. The base validator must
# remain fail-closed. The runtime therefore rejects only those individual atoms
# before the base validator sees them, records only aggregate rejection diagnostics
# in the encrypted checkpoint, and lets synthesis treat the resulting omission as
# missing/not_verifiable. Malformed atoms and every other contract error still go
# unchanged to the base validator and fail the whole development case.
EVIDENCE_REJECTION_POLICY = 'omit_nonliteral_or_nonunique_atom_before_base_validation'
RUNTIME_DIAGNOSTICS = {
    'nonliteral_atoms_omitted': 0,
    'ambiguous_atoms_omitted': 0,
    'omission_digest': development.sha(development.canonical([])),
}

_ORIGINAL_CHUNK_REQUEST = development.chunk_request
_ORIGINAL_EXTRACTOR_FINGERPRINT = development.extractor_fingerprint
_ORIGINAL_RESOLVE_ATOMS = development.resolve_atoms
_ORIGINAL_CHECKPOINT = development.checkpoint


def runtime_chunk_system():
    return development.CHUNK_SYSTEM + '\n' + EVIDENCE_UNIQUENESS_SUFFIX


def runtime_extractor_fingerprint():
    stable = {
        'protocol': development.PROTOCOL,
        'model': development.MODEL,
        **SCIENTIFIC_CONFIG,
        'chunk_system': runtime_chunk_system(),
        'synthesis_system': development.SYNTHESIS_SYSTEM,
        'field_by_entity': {key: sorted(value) for key, value in development.FIELD_BY_ENTITY.items()},
        'paper_enrichment_schema_sha256': development.schema_digest(),
        'decoder_contract': 'llama.cpp-json-schema;temperature=0;seed=0',
        'evidence_rejection_policy': EVIDENCE_REJECTION_POLICY,
    }
    return development.sha(development.canonical(stable))


def bounded_chunk_request(chunk):
    request = _ORIGINAL_CHUNK_REQUEST(chunk)
    request['max_tokens'] = SCIENTIFIC_CONFIG['chunk_max_tokens']
    system = request['messages'][0]['content']
    if not system.startswith(development.CHUNK_SYSTEM):
        raise RuntimeError('fulltext_chunk_prompt_contract_changed')
    request['messages'][0]['content'] = runtime_chunk_system() + system[len(development.CHUNK_SYSTEM):]
    return request


def _evidence_occurrences(source, evidence):
    starts = []
    at = 0
    while True:
        found = source.find(evidence, at)
        if found < 0:
            break
        starts.append(found)
        if len(starts) > 1:
            break
        at = found + 1
    return len(starts)


def runtime_resolve_atoms(chunks, outputs):
    """Omit only unlocatable/non-unique atoms; keep the base validator unchanged.

    The omission is scientific missingness, not successful evidence. No source text,
    evidence quote or model value is placed in the diagnostics: only counts and a
    stable digest of non-sensitive structural descriptors enter the encrypted
    development checkpoint.
    """
    if len(chunks) != len(outputs):
        return _ORIGINAL_RESOLVE_ATOMS(chunks, outputs)
    sanitised = []
    omitted = []
    for chunk, output in zip(chunks, outputs):
        if not isinstance(output, dict) or set(output) != {'atoms'} or not isinstance(output['atoms'], list):
            sanitised.append(output)
            continue
        atoms = []
        for index, raw in enumerate(output['atoms']):
            # Do not mask malformed atoms or invalid field/entity contracts. Those
            # remain the responsibility of the base validator and must still fail.
            if (not isinstance(raw, dict) or
                    set(raw) != {'entity_type', 'entity_key', 'field', 'value', 'evidence'} or
                    not isinstance(raw.get('evidence'), str) or
                    not raw['evidence'].strip() or len(raw['evidence']) > 500):
                atoms.append(raw)
                continue
            occurrences = _evidence_occurrences(chunk['text'], raw['evidence'])
            if occurrences == 1:
                atoms.append(raw)
                continue
            reason = 'nonliteral' if occurrences == 0 else 'ambiguous'
            omitted.append({
                'chunk_id': chunk.get('id'), 'atom_index': index,
                'entity_type': raw.get('entity_type'), 'field': raw.get('field'),
                'reason': reason,
            })
        sanitised.append({'atoms': atoms})
    RUNTIME_DIAGNOSTICS['nonliteral_atoms_omitted'] = sum(item['reason'] == 'nonliteral' for item in omitted)
    RUNTIME_DIAGNOSTICS['ambiguous_atoms_omitted'] = sum(item['reason'] == 'ambiguous' for item in omitted)
    RUNTIME_DIAGNOSTICS['omission_digest'] = development.sha(development.canonical(omitted))
    return _ORIGINAL_RESOLVE_ATOMS(chunks, sanitised)


def runtime_checkpoint_payload(payload):
    return {
        **payload,
        'runtime_evidence_rejections': {
            'policy': EVIDENCE_REJECTION_POLICY,
            **RUNTIME_DIAGNOSTICS,
        },
    }


def runtime_checkpoint(output, payload):
    return _ORIGINAL_CHECKPOINT(output, runtime_checkpoint_payload(payload))


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
    original_resolve_atoms = development.resolve_atoms
    original_checkpoint = development.checkpoint

    RUNTIME_DIAGNOSTICS.update({
        'nonliteral_atoms_omitted': 0,
        'ambiguous_atoms_omitted': 0,
        'omission_digest': development.sha(development.canonical([])),
    })
    development.CHUNK_CHARS = SCIENTIFIC_CONFIG['chunk_chars']
    development.CHUNK_OVERLAP = SCIENTIFIC_CONFIG['chunk_overlap']
    development.MAX_ATOMS_PER_CHUNK = SCIENTIFIC_CONFIG['max_atoms_per_chunk']
    development.chunk_request = bounded_chunk_request
    development.extractor_fingerprint = runtime_extractor_fingerprint
    development.resolve_atoms = runtime_resolve_atoms
    development.checkpoint = runtime_checkpoint
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
        development.resolve_atoms = original_resolve_atoms
        development.checkpoint = original_checkpoint


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error)
        if code.startswith('fulltext_') or code.startswith('OA '):
            raise SystemExit(code) from None
        raise SystemExit('fulltext_calibration_development_failed') from None
