#!/usr/bin/env python3
"""Resume exact full-text chunk inference from authenticated private checkpoints.

This wrapper reuses a raw chunk output only when the candidate id, extractor
fingerprint and complete request hash are identical. Checkpoints remain in the
existing authenticated private store and no source/model output is printed or
written to GitHub artifacts by this wrapper.

An optional operational pass budget can bound how many previously-missing chunks
one process computes. Exhausting that budget after durable private checkpointing
is a successful partial pass unless the caller explicitly requires completion.
This is scheduling only: cache hits, requests, model settings and the eventual
scientific proposal remain governed by the existing contracts.

The production resume path also tightens the synthesis decoder so each assignment
may cite only resolved atom ids with the same destination entity type and field.
The base proposal validator remains unchanged and fail-closed. Because this is a
model-output constraint, its version is included in the existing stable extractor
fingerprint during the run.
"""
import json
import os
from pathlib import Path
import re
import sys

from scripts.calibration import full_text_development as development
from scripts.calibration import full_text_development_run as runtime
from scripts.enrichment.service_client import call as service_call

PROTOCOL = 'CILE-FULLTEXT-DEV-CHUNK-1'
SYNTHESIS_ATOM_SCOPED_SCHEMA = 'destination-field-and-atom-scoped-assignments-v2'
_ORIGINAL_RUNTIME_POST = runtime.runtime_post
PASS_STATE = {'limit': None, 'new_chunks': 0, 'reused_chunks': 0}


def _compatible_assignment_branches(fields, atoms, entity_type=None):
    """Return one decoder branch per field with only compatible resolved atom ids."""
    branches = []
    for field in sorted(fields):
        atom_ids = sorted({
            atom['id'] for atom in atoms
            if atom.get('field') == field and (
                entity_type is None or atom.get('entity_type') == entity_type
            )
        })
        if not atom_ids:
            continue
        branch = runtime.field_scoped_assignment_schema({field})
        branch['properties']['field'] = {'const': field}
        branch['properties']['atom_ids']['items'] = {'enum': atom_ids}
        branch['properties']['atom_ids']['maxItems'] = min(12, len(atom_ids))
        branches.append(branch)
    return branches


def _assignment_array_schema(fields, atoms, entity_type=None):
    branches = _compatible_assignment_branches(fields, atoms, entity_type)
    if not branches:
        return {
            'type': 'array', 'maxItems': 0,
            'items': runtime.field_scoped_assignment_schema(fields),
        }
    return {
        'type': 'array', 'maxItems': len(branches),
        'items': {'oneOf': branches},
    }


def _atom_scoped_record_schema(kind, atoms):
    schema = runtime.field_scoped_record_schema(kind)
    schema['properties']['fields'] = _assignment_array_schema(
        development.FIELD_BY_ENTITY[kind], atoms, kind,
    )
    return schema


def atom_scoped_synthesis_schema(atoms):
    """Constrain synthesis citations to the destination entity/field atom scope.

    Framework rationale is intentionally cross-entity, as in the reviewed base
    policy, but it may still cite only atoms whose field equals the rationale
    assignment field. If no resolved atom can support a destination, that
    assignment array is decoder-constrained to remain empty rather than inviting a
    reference that the unchanged base validator would have to reject later.
    """
    framework_branches = _compatible_assignment_branches(
        development.ALL_FIELDS, atoms, entity_type=None,
    )
    if framework_branches:
        framework_assignment = {'oneOf': framework_branches}
        framework_rationale = {'anyOf': [framework_assignment, {'type': 'null'}]}
        framework_secondary = {
            'type': 'array', 'maxItems': 5,
            'items': {
                'type': 'object', 'additionalProperties': False,
                'properties': {
                    'category': {'enum': development.CATEGORIES},
                    'rationale': framework_assignment,
                },
                'required': ['category', 'rationale'],
            },
        }
    else:
        framework_rationale = {'type': 'null'}
        framework_secondary = {
            'type': 'array', 'maxItems': 0,
            'items': {'type': 'object'},
        }
    framework = {
        'type': 'object', 'additionalProperties': False,
        'properties': {
            'status': {'enum': ['proposed', 'insufficient_evidence', 'outside_framework']},
            'primary': {'enum': development.CATEGORIES + [None]},
            'rationale': framework_rationale,
            'secondary': framework_secondary,
            'alternative': {'enum': development.CATEGORIES + [None]},
        },
        'required': ['status', 'primary', 'rationale', 'secondary', 'alternative'],
    }
    return {
        'type': 'object', 'additionalProperties': False,
        'properties': {
            'global_fields': _assignment_array_schema(
                development.GLOBAL_FIELDS, atoms, 'global',
            ),
            'studies': {
                'type': 'array', 'maxItems': 50,
                'items': _atom_scoped_record_schema('study', atoms),
            },
            'datasets': {
                'type': 'array', 'maxItems': 100,
                'items': _atom_scoped_record_schema('dataset', atoms),
            },
            'analyses': {
                'type': 'array', 'maxItems': 200,
                'items': _atom_scoped_record_schema('analysis', atoms),
            },
            'variable_uses': {
                'type': 'array', 'maxItems': 500,
                'items': _atom_scoped_record_schema('variable_use', atoms),
            },
            'findings': {
                'type': 'array', 'maxItems': 300,
                'items': _atom_scoped_record_schema('finding', atoms),
            },
            'framework': framework,
        },
        'required': [
            'global_fields', 'studies', 'datasets', 'analyses',
            'variable_uses', 'findings', 'framework',
        ],
    }


def atom_scoped_bounded_synthesis_request(atoms):
    """Build the existing synthesis request with atom-compatible decoder choices."""
    original_synthesis_schema = development.synthesis_schema
    development.synthesis_schema = lambda: atom_scoped_synthesis_schema(atoms)
    try:
        request = runtime._ORIGINAL_SYNTHESIS_REQUEST(atoms)
    finally:
        development.synthesis_schema = original_synthesis_schema
    request['max_tokens'] = runtime.SCIENTIFIC_CONFIG['synthesis_max_tokens']
    return request


def install_assignment_scope():
    """Install the v2 synthesis decoder for one resume-run process and return prior state."""
    prior = (
        runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA,
        runtime.bounded_synthesis_request,
    )
    runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA = SYNTHESIS_ATOM_SCOPED_SCHEMA
    runtime.bounded_synthesis_request = atom_scoped_bounded_synthesis_request
    return prior


def restore_assignment_scope(prior):
    runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA, runtime.bounded_synthesis_request = prior


def candidate_id_from_argv(argv=None):
    values = list(sys.argv if argv is None else argv)
    try:
        value = values[values.index('--candidate-id') + 1]
    except (ValueError, IndexError):
        raise RuntimeError('fulltext_checkpoint_candidate_unavailable') from None
    if not re.fullmatch(r'CAND-[A-Za-z0-9][A-Za-z0-9._-]{1,199}', value):
        raise RuntimeError('fulltext_checkpoint_candidate_unavailable')
    return value


def checkpoint_service_commit():
    value = os.environ.get('CALIBRATION_CHECKPOINT_SERVICE_COMMIT', '')
    if not re.fullmatch(r'[0-9a-f]{40}', value):
        raise RuntimeError('fulltext_checkpoint_service_commit_unavailable')
    return value


def pass_limit():
    value = os.environ.get('FULLTEXT_MAX_NEW_CHUNKS', '').strip()
    if not value:
        return None
    if not re.fullmatch(r'[1-9][0-9]{0,2}', value) or int(value) > 50:
        raise RuntimeError('fulltext_checkpoint_pass_limit_invalid')
    return int(value)


def pass_requires_complete():
    value = os.environ.get('FULLTEXT_REQUIRE_COMPLETE', '0').strip()
    if value not in {'0', '1'}:
        raise RuntimeError('fulltext_checkpoint_pass_completion_invalid')
    return value == '1'


def reset_pass_state(limit=None):
    PASS_STATE.update({'limit': limit, 'new_chunks': 0, 'reused_chunks': 0})


def write_pass_status(status):
    if status not in {'partial', 'complete', 'incomplete'}:
        raise RuntimeError('fulltext_checkpoint_pass_status_invalid')
    value = os.environ.get('FULLTEXT_PASS_STATUS_FILE', '').strip()
    if not value:
        return
    path = Path(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(status + '\n', encoding='utf-8')


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
    commit = checkpoint_service_commit()
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
        PASS_STATE['reused_chunks'] += 1
        print(json.dumps({
            'event': 'private_chunk_checkpoint', 'candidate_id': candidate_id,
            'chunk_id': identity['chunk_id'], 'status': 'reused',
            'request_sha256': identity['request_sha256'],
        }, separators=(',', ':')), flush=True)
        return output
    if result.get('status') != 'missing':
        raise RuntimeError('fulltext_checkpoint_service_invalid_response')

    limit = PASS_STATE.get('limit')
    if limit is not None and PASS_STATE['new_chunks'] >= limit:
        raise RuntimeError('fulltext_checkpoint_pass_budget_exhausted')

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
    PASS_STATE['new_chunks'] += 1
    print(json.dumps({
        'event': 'private_chunk_checkpoint', 'candidate_id': candidate_id,
        'chunk_id': identity['chunk_id'], 'status': 'stored',
        'request_sha256': identity['request_sha256'],
        'output_sha256': receipt.get('output_sha256'),
    }, separators=(',', ':')), flush=True)
    return output


def pass_event(status):
    return json.dumps({
        'event': 'private_chunk_pass',
        'status': status,
        'new_chunks': PASS_STATE['new_chunks'],
        'reused_chunks': PASS_STATE['reused_chunks'],
    }, separators=(',', ':'))


def main():
    original = runtime.runtime_post
    assignment_scope = install_assignment_scope()
    limit = pass_limit()
    require_complete = pass_requires_complete()
    reset_pass_state(limit)
    runtime.runtime_post = resumable_post
    try:
        try:
            runtime.main()
        except RuntimeError as error:
            if str(error) != 'fulltext_checkpoint_pass_budget_exhausted':
                raise
            status = 'incomplete' if require_complete else 'partial'
            write_pass_status(status)
            print(pass_event(status), flush=True)
            if require_complete:
                raise
            return
        write_pass_status('complete')
        print(pass_event('complete'), flush=True)
    finally:
        runtime.runtime_post = original
        restore_assignment_scope(assignment_scope)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error)
        if code.startswith('fulltext_') or code.startswith('OA '):
            raise SystemExit(code) from None
        raise SystemExit('fulltext_calibration_development_failed') from None
