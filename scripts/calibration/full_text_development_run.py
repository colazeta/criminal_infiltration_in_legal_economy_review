#!/usr/bin/env python3
"""Runtime policy for the bounded full-text calibration development harness.

Operational model timeouts remain outside the scientific extractor fingerprint.
This wrapper also selects the reviewed bounded calibration configuration used by
this execution. Scientific settings are incorporated into an explicit stable
source-independent fingerprint before the base harness is called.
"""
import copy
from scripts.calibration import full_text_development as development

CHUNK_TIMEOUT_SECONDS = 600
SYNTHESIS_TIMEOUT_SECONDS = 720
SYNTHESIS_COMPLETION_TIMEOUT_SECONDS = 1800

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
    'synthesis_max_tokens': 6000,
}

# Run 34900857749 failed with `fulltext_model_output_incomplete` after #703 changed
# only the synthesis decoder schema. The chunk request, chunk decoder, source,
# model, seed and 1,600-token chunk budget were unchanged from run 34888989672,
# which completed chunk extraction and reached synthesis validation. Therefore
# recover this newly observed truncation by increasing only the bounded synthesis
# response budget. `finish_reason != stop` remains fail-closed; partial output is
# never accepted and the changed budget is bound into the extractor fingerprint.
# Run 34906117062 then preserved the same scientific request but timed out after
# the larger 4,500-token synthesis budget was introduced. #705 kept that request
# unchanged and extended only the completion allowance to 20 minutes. Successor
# run 34914763034 no longer timed out but again returned
# `fulltext_model_output_incomplete` under the 4,500-token synthesis cap after all
# chunk work had completed. Increase only that bounded response cap to 6,000 and
# its operational completion allowance to 30 minutes. Source, model, seed, chunk
# coverage, atom capacity, decoder/field rules, evidence rejection and fail-closed
# validation remain unchanged. The token-cap change is bound into the extractor
# fingerprint; the timeout remains operational and outside that fingerprint.

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
# after validating every non-evidence contract on the ORIGINAL model output. The
# omission becomes scientific missingness, never accepted evidence, and aggregate
# diagnostics are checkpointed immediately after evidence resolution.
EVIDENCE_REJECTION_POLICY = 'omit_nonliteral_or_nonunique_atom_after_structural_validation'

# Run 34883540426 reached structural validation but failed with
# `fulltext_atom_field_scope`: the generic decoder schema allowed every governed
# field for every entity and relied on the post-model validator to reject an
# invalid entity/field pairing. Keep that validator unchanged, but make the
# constrained decoder express the same closed field map up front. This is a model
# output constraint, not a recoding rule: invalid pairings remain impossible to
# accept and are never silently moved between entity types.
FIELD_SCOPED_ATOM_SCHEMA = 'entity-field-paired-oneof-v1'

# Run 34888989672 passed chunk-level entity/field validation, completed inference,
# then failed `fulltext_assignment_field` while converting the synthesis graph.
# The base synthesis JSON schema leaves assignment.field generic and relies on the
# post-model destination validator to reject an assignment placed under the wrong
# group. Preserve that validator unchanged and constrain only the decoder schema:
# global assignments can select GLOBAL_FIELDS, each record kind can select only
# its FIELD_BY_ENTITY fields, while framework rationale may cite any governed atom
# field because it is an analyst interpretation grounded across source entities.
SYNTHESIS_FIELD_SCOPED_SCHEMA = 'destination-field-scoped-assignments-v1'

RUNTIME_DIAGNOSTICS = {
    'nonliteral_atoms_omitted': 0,
    'ambiguous_atoms_omitted': 0,
    'omission_digest': development.sha(development.canonical([])),
}
RUNTIME_CHECKPOINT = {'output': None, 'payload': None}

_ORIGINAL_CHUNK_REQUEST = development.chunk_request
_ORIGINAL_SYNTHESIS_REQUEST = development.synthesis_request
_ORIGINAL_EXTRACTOR_FINGERPRINT = development.extractor_fingerprint
_ORIGINAL_RESOLVE_ATOMS = development.resolve_atoms
_ORIGINAL_CHECKPOINT = development.checkpoint
_ORIGINAL_ATOM_SCHEMA = development.atom_schema
_ORIGINAL_SYNTHESIS_SCHEMA = development.synthesis_schema


def runtime_chunk_system():
    return development.CHUNK_SYSTEM + '\n' + EVIDENCE_UNIQUENESS_SUFFIX


def field_scoped_atom_schema():
    """Constrain entity/field pairs in the JSON decoder without changing review semantics."""
    branches = []
    for entity_type, fields in development.FIELD_BY_ENTITY.items():
        branches.append({
            'type': 'object',
            'additionalProperties': False,
            'properties': {
                'entity_type': {'const': entity_type},
                'entity_key': {'type': 'string', 'minLength': 1, 'maxLength': 80},
                'field': {'enum': sorted(fields)},
                'value': {'type': 'string', 'minLength': 1, 'maxLength': 1000},
                'evidence': {'type': 'string', 'minLength': 1, 'maxLength': 500},
            },
            'required': ['entity_type', 'entity_key', 'field', 'value', 'evidence'],
        })
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'atoms': {
                'type': 'array',
                'maxItems': development.MAX_ATOMS_PER_CHUNK,
                'items': {'oneOf': branches},
            },
        },
        'required': ['atoms'],
    }


def field_scoped_assignment_schema(fields=None):
    """Return the base assignment shape with an optional closed destination field enum."""
    field = {'type': 'string', 'minLength': 1, 'maxLength': 80}
    if fields is not None:
        field = {'enum': sorted(fields)}
    return {
        'type': 'object', 'additionalProperties': False,
        'properties': {
            'field': field,
            'value': {'type': 'string', 'minLength': 1, 'maxLength': 1000},
            'atom_ids': {'type': 'array', 'minItems': 1, 'maxItems': 12,
                         'items': {'type': 'string', 'minLength': 1, 'maxLength': 80}},
        },
        'required': ['field', 'value', 'atom_ids'],
    }


def field_scoped_record_schema(kind):
    fields = development.FIELD_BY_ENTITY[kind]
    props = {
        'id': {'type': 'string', 'minLength': 1, 'maxLength': 80},
        'fields': {'type': 'array', 'maxItems': len(fields),
                   'items': field_scoped_assignment_schema(fields)},
    }
    required = ['id', 'fields']
    if kind == 'dataset':
        props['study_id'] = {'type': 'string', 'minLength': 1, 'maxLength': 80}
        required.append('study_id')
    elif kind == 'analysis':
        props['study_id'] = {'type': 'string', 'minLength': 1, 'maxLength': 80}
        props['dataset_ids'] = {'type': 'array', 'maxItems': 100,
                                'items': {'type': 'string', 'maxLength': 80}}
        required.extend(['study_id', 'dataset_ids'])
    elif kind == 'variable_use':
        props['analysis_id'] = {'type': 'string', 'minLength': 1, 'maxLength': 80}
        props['dataset_ids'] = {'type': 'array', 'maxItems': 100,
                                'items': {'type': 'string', 'maxLength': 80}}
        required.extend(['analysis_id', 'dataset_ids'])
    elif kind == 'finding':
        props['analysis_id'] = {'type': 'string', 'minLength': 1, 'maxLength': 80}
        props['variable_use_ids'] = {'type': 'array', 'maxItems': 100,
                                     'items': {'type': 'string', 'maxLength': 80}}
        required.extend(['analysis_id', 'variable_use_ids'])
    return {'type': 'object', 'additionalProperties': False, 'properties': props, 'required': required}


def field_scoped_synthesis_schema():
    """Constrain synthesis destinations while leaving framework evidence cross-entity."""
    framework_assignment = field_scoped_assignment_schema()
    framework = {
        'type': 'object', 'additionalProperties': False,
        'properties': {
            'status': {'enum': ['proposed', 'insufficient_evidence', 'outside_framework']},
            'primary': {'enum': development.CATEGORIES + [None]},
            'rationale': {'anyOf': [framework_assignment, {'type': 'null'}]},
            'secondary': {
                'type': 'array', 'maxItems': 5,
                'items': {
                    'type': 'object', 'additionalProperties': False,
                    'properties': {
                        'category': {'enum': development.CATEGORIES},
                        'rationale': field_scoped_assignment_schema(),
                    },
                    'required': ['category', 'rationale'],
                },
            },
            'alternative': {'enum': development.CATEGORIES + [None]},
        },
        'required': ['status', 'primary', 'rationale', 'secondary', 'alternative'],
    }
    return {
        'type': 'object', 'additionalProperties': False,
        'properties': {
            'global_fields': {
                'type': 'array', 'maxItems': len(development.GLOBAL_FIELDS),
                'items': field_scoped_assignment_schema(development.GLOBAL_FIELDS),
            },
            'studies': {'type': 'array', 'maxItems': 50, 'items': field_scoped_record_schema('study')},
            'datasets': {'type': 'array', 'maxItems': 100, 'items': field_scoped_record_schema('dataset')},
            'analyses': {'type': 'array', 'maxItems': 200, 'items': field_scoped_record_schema('analysis')},
            'variable_uses': {'type': 'array', 'maxItems': 500,
                              'items': field_scoped_record_schema('variable_use')},
            'findings': {'type': 'array', 'maxItems': 300, 'items': field_scoped_record_schema('finding')},
            'framework': framework,
        },
        'required': ['global_fields', 'studies', 'datasets', 'analyses', 'variable_uses', 'findings', 'framework'],
    }


def runtime_extractor_fingerprint():
    stable = {
        'protocol': development.PROTOCOL,
        'model': development.MODEL,
        **SCIENTIFIC_CONFIG,
        'chunk_system': runtime_chunk_system(),
        'synthesis_system': development.SYNTHESIS_SYSTEM,
        'field_by_entity': {key: sorted(value) for key, value in development.FIELD_BY_ENTITY.items()},
        'atom_schema_contract': FIELD_SCOPED_ATOM_SCHEMA,
        'synthesis_schema_contract': SYNTHESIS_FIELD_SCOPED_SCHEMA,
        'paper_enrichment_schema_sha256': development.schema_digest(),
        'decoder_contract': 'llama.cpp-json-schema;temperature=0;seed=0',
        'evidence_rejection_policy': EVIDENCE_REJECTION_POLICY,
    }
    return development.sha(development.canonical(stable))


def bounded_chunk_request(chunk):
    # The reviewed base request builder reads development.atom_schema dynamically.
    # Swap only for construction of this one request, then restore immediately so
    # importing this runtime policy never mutates the base scientific module.
    original_atom_schema = development.atom_schema
    development.atom_schema = field_scoped_atom_schema
    try:
        request = _ORIGINAL_CHUNK_REQUEST(chunk)
    finally:
        development.atom_schema = original_atom_schema
    request['max_tokens'] = SCIENTIFIC_CONFIG['chunk_max_tokens']
    system = request['messages'][0]['content']
    if not system.startswith(development.CHUNK_SYSTEM):
        raise RuntimeError('fulltext_chunk_prompt_contract_changed')
    request['messages'][0]['content'] = runtime_chunk_system() + system[len(development.CHUNK_SYSTEM):]
    return request


def bounded_synthesis_request(atoms):
    # As at chunk extraction, change only the decoder schema supplied to this one
    # request. The base proposal builder/post-model validators remain authoritative.
    original_synthesis_schema = development.synthesis_schema
    development.synthesis_schema = field_scoped_synthesis_schema
    try:
        request = _ORIGINAL_SYNTHESIS_REQUEST(atoms)
    finally:
        development.synthesis_schema = original_synthesis_schema
    request['max_tokens'] = SCIENTIFIC_CONFIG['synthesis_max_tokens']
    return request


def _validate_original_atom_contracts(chunks, outputs):
    """Mirror every pre-location fail-closed check before any atom can be omitted."""
    if len(chunks) != len(outputs):
        raise ValueError('fulltext_chunk_result_count')
    for output in outputs:
        if not isinstance(output, dict) or set(output) != {'atoms'} or not isinstance(output['atoms'], list):
            raise ValueError('fulltext_atom_shape')
        if len(output['atoms']) > development.MAX_ATOMS_PER_CHUNK:
            raise ValueError('fulltext_atom_limit')
        for raw in output['atoms']:
            if not isinstance(raw, dict) or set(raw) != {'entity_type', 'entity_key', 'field', 'value', 'evidence'}:
                raise ValueError('fulltext_atom_shape')
            entity = raw['entity_type']
            if entity not in development.FIELD_BY_ENTITY or raw['field'] not in development.FIELD_BY_ENTITY[entity]:
                raise ValueError('fulltext_atom_field_scope')
            evidence = raw['evidence']
            if not isinstance(evidence, str) or not evidence.strip() or len(evidence) > 500:
                raise ValueError('fulltext_atom_evidence')


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


def runtime_checkpoint_payload(payload):
    return {
        **payload,
        'runtime_evidence_rejections': {
            'policy': EVIDENCE_REJECTION_POLICY,
            **RUNTIME_DIAGNOSTICS,
        },
    }


def runtime_checkpoint(output, payload):
    RUNTIME_CHECKPOINT['output'] = output
    RUNTIME_CHECKPOINT['payload'] = copy.deepcopy(payload)
    return _ORIGINAL_CHECKPOINT(output, runtime_checkpoint_payload(payload))


def _persist_resolution_checkpoint():
    output = RUNTIME_CHECKPOINT.get('output')
    prior = RUNTIME_CHECKPOINT.get('payload')
    if output is None or not isinstance(prior, dict):
        raise RuntimeError('fulltext_resolution_checkpoint_unavailable')
    payload = {
        **prior,
        'status': 'evidence_resolution_complete_model_pending',
    }
    RUNTIME_CHECKPOINT['payload'] = copy.deepcopy(payload)
    _ORIGINAL_CHECKPOINT(output, runtime_checkpoint_payload(payload))


def runtime_resolve_atoms(chunks, outputs):
    """Omit only unlocatable/non-unique atoms after original structural checks.

    The omission is scientific missingness, not successful evidence. No source text,
    evidence quote or model value is placed in the diagnostics: only counts and a
    stable digest of non-sensitive structural descriptors enter the encrypted
    development checkpoint. Structural/field/count errors still fail the whole run.
    """
    _validate_original_atom_contracts(chunks, outputs)
    sanitised = []
    omitted = []
    for chunk, output in zip(chunks, outputs):
        atoms = []
        for index, raw in enumerate(output['atoms']):
            occurrences = _evidence_occurrences(chunk['text'], raw['evidence'])
            if occurrences == 1:
                atoms.append(raw)
                continue
            reason = 'nonliteral' if occurrences == 0 else 'ambiguous'
            omitted.append({
                'chunk_id': chunk.get('id'), 'atom_index': index,
                'entity_type': raw['entity_type'], 'field': raw['field'],
                'reason': reason,
            })
        sanitised.append({'atoms': atoms})
    RUNTIME_DIAGNOSTICS['nonliteral_atoms_omitted'] = sum(item['reason'] == 'nonliteral' for item in omitted)
    RUNTIME_DIAGNOSTICS['ambiguous_atoms_omitted'] = sum(item['reason'] == 'ambiguous' for item in omitted)
    RUNTIME_DIAGNOSTICS['omission_digest'] = development.sha(development.canonical(omitted))
    resolved = _ORIGINAL_RESOLVE_ATOMS(chunks, sanitised)
    # Persist the measured omissions before synthesis starts. A later model timeout,
    # invalid graph or native-validation failure therefore cannot erase this audit.
    _persist_resolution_checkpoint()
    return resolved


def runtime_timeout(requested):
    if not isinstance(requested, (int, float)) or requested <= 0:
        raise ValueError('fulltext_runtime_timeout_invalid')
    if requested <= 300:
        return max(requested, CHUNK_TIMEOUT_SECONDS)
    return max(requested, SYNTHESIS_TIMEOUT_SECONDS)


def runtime_post(original, payload, timeout=300):
    effective_timeout = runtime_timeout(timeout)
    if timeout > 300:
        effective_timeout = max(effective_timeout, SYNTHESIS_COMPLETION_TIMEOUT_SECONDS)
    try:
        return original(payload, timeout=effective_timeout)
    except TimeoutError:
        raise RuntimeError('fulltext_model_timeout') from None


def main():
    original_post = development.post_model
    original_chunk_chars = development.CHUNK_CHARS
    original_chunk_overlap = development.CHUNK_OVERLAP
    original_max_atoms = development.MAX_ATOMS_PER_CHUNK
    original_chunk_request = development.chunk_request
    original_synthesis_request = development.synthesis_request
    original_fingerprint = development.extractor_fingerprint
    original_resolve_atoms = development.resolve_atoms
    original_checkpoint = development.checkpoint

    RUNTIME_DIAGNOSTICS.update({
        'nonliteral_atoms_omitted': 0,
        'ambiguous_atoms_omitted': 0,
        'omission_digest': development.sha(development.canonical([])),
    })
    RUNTIME_CHECKPOINT.update({'output': None, 'payload': None})
    development.CHUNK_CHARS = SCIENTIFIC_CONFIG['chunk_chars']
    development.CHUNK_OVERLAP = SCIENTIFIC_CONFIG['chunk_overlap']
    development.MAX_ATOMS_PER_CHUNK = SCIENTIFIC_CONFIG['max_atoms_per_chunk']
    development.chunk_request = bounded_chunk_request
    development.synthesis_request = bounded_synthesis_request
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
        development.synthesis_request = original_synthesis_request
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