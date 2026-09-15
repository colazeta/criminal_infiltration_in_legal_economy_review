#!/usr/bin/env python3
"""Relation-safe v3 wrapper for the reviewed resumable full-text harness.

The reviewed v2 implementation is preserved byte-for-byte in
``full_text_development_resume_v2.py``. This wrapper changes only the synthesis
contract observed after run 34948604180 failed closed with
``fulltext_variable_relation`` after all source chunks had been durably
checkpointed.

V3 keeps the base validator unchanged. It makes relation arrays unique at decode
time, gives the synthesis model explicit fail-closed referential-integrity rules,
and binds that prompt/schema contract into the extractor fingerprint. Because
those are synthesis-only changes, exact v2 chunk checkpoints may be reused only
when candidate, complete chunk request hash and the known v2 extractor fingerprint
all match; a validated hit is promoted into the current private namespace before
use. No source text or model output is written to public repository state.
"""
from scripts.calibration import full_text_development as development
from scripts.calibration import full_text_development_run as runtime
from scripts.calibration import full_text_development_resume_v2 as v2

LEGACY_SYNTHESIS_ATOM_SCOPED_SCHEMA = v2.SYNTHESIS_ATOM_SCOPED_SCHEMA
SYNTHESIS_ATOM_SCOPED_SCHEMA = 'destination-field-atom-and-relation-scoped-assignments-v3'
RELATION_CONSISTENCY_SUFFIX = """Relational integrity is fail-closed. Every relationship id MUST reference a record you emit in this same JSON object. Dataset study_id must reference an emitted study. Analysis study_id must reference an emitted study and every analysis dataset_id must reference an emitted dataset belonging to that same study. Variable-use analysis_id must reference an emitted analysis and every variable-use dataset_id must be unique and drawn only from that analysis's dataset_ids. Finding analysis_id must reference an emitted analysis and every finding variable_use_id must be unique, reference an emitted variable use, and belong to the same analysis. Relationship arrays must not contain duplicate ids. If the supplied atoms do not support a relationship conservatively, omit the dependent record rather than inventing or guessing an id."""

_V2_ATOM_SCOPED_RECORD_SCHEMA = v2._atom_scoped_record_schema
_V2_ATOM_SCOPED_SYNTHESIS_SCHEMA = v2.atom_scoped_synthesis_schema
_V2_BOUNDED_SYNTHESIS_REQUEST = v2.atom_scoped_bounded_synthesis_request
_V2_INSTALL_ASSIGNMENT_SCOPE = v2.install_assignment_scope
_V2_RESTORE_ASSIGNMENT_SCOPE = v2.restore_assignment_scope
_V2_RESUMABLE_POST = v2.resumable_post
_ORIGINAL_RUNTIME_FINGERPRINT = runtime.runtime_extractor_fingerprint


def _atom_scoped_record_schema(kind, atoms):
    """Retain v2 atom scoping and make relation arrays decoder-unique."""
    schema = _V2_ATOM_SCOPED_RECORD_SCHEMA(kind, atoms)
    props = schema['properties']
    if kind == 'analysis':
        props['dataset_ids']['uniqueItems'] = True
    elif kind == 'variable_use':
        props['dataset_ids']['uniqueItems'] = True
    elif kind == 'finding':
        props['variable_use_ids']['uniqueItems'] = True
    return schema


def atom_scoped_synthesis_schema(atoms):
    """Use the v2 evidence scope plus relation-array uniqueness constraints."""
    return _V2_ATOM_SCOPED_SYNTHESIS_SCHEMA(atoms)


def atom_scoped_bounded_synthesis_request(atoms):
    """Build the v3 request without changing source atoms or base validation."""
    request = _V2_BOUNDED_SYNTHESIS_REQUEST(atoms)
    system = request['messages'][0]['content']
    if RELATION_CONSISTENCY_SUFFIX not in system:
        request['messages'][0]['content'] = system + '\n' + RELATION_CONSISTENCY_SUFFIX
    return request


def relation_scoped_extractor_fingerprint():
    """Bind the exact v3 synthesis prompt as well as the decoder contract."""
    base = _ORIGINAL_RUNTIME_FINGERPRINT()
    return development.sha(development.canonical({
        'base_runtime_fingerprint': base,
        'relation_consistency_prompt': RELATION_CONSISTENCY_SUFFIX,
        'relation_schema_contract': SYNTHESIS_ATOM_SCOPED_SCHEMA,
    }))


def legacy_v2_extractor_fingerprint():
    """Reconstruct the exact #711 v2 fingerprint for chunk-only migration."""
    current_contract = runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA
    try:
        runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA = LEGACY_SYNTHESIS_ATOM_SCOPED_SCHEMA
        return _ORIGINAL_RUNTIME_FINGERPRINT()
    finally:
        runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA = current_contract


def install_assignment_scope():
    """Install v3 synthesis constraints while preserving a restorable runtime."""
    prior_scope = _V2_INSTALL_ASSIGNMENT_SCOPE()
    prior_fingerprint = runtime.runtime_extractor_fingerprint
    runtime.runtime_extractor_fingerprint = relation_scoped_extractor_fingerprint
    return prior_scope, prior_fingerprint


def restore_assignment_scope(prior):
    prior_scope, prior_fingerprint = prior
    runtime.runtime_extractor_fingerprint = prior_fingerprint
    _V2_RESTORE_ASSIGNMENT_SCOPE(prior_scope)


def _legacy_migration_enabled():
    return (
        runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA == SYNTHESIS_ATOM_SCOPED_SCHEMA
        and runtime.runtime_extractor_fingerprint is relation_scoped_extractor_fingerprint
    )


def _migration_service(service):
    """Read exact v2 chunk checkpoints once and promote them into v3 privately."""
    def call(operation, **kwargs):
        if operation != 'development-checkpoint-get' or not _legacy_migration_enabled():
            return service(operation, **kwargs)

        current_identity = kwargs.get('checkpoint')
        current = service(operation, **kwargs)
        if current.get('status') != 'missing' or not isinstance(current_identity, dict):
            return current

        legacy_identity = {
            **current_identity,
            'extractor_fingerprint': legacy_v2_extractor_fingerprint(),
        }
        if legacy_identity['extractor_fingerprint'] == current_identity.get('extractor_fingerprint'):
            return current
        legacy = service(
            'development-checkpoint-get',
            expected_commit=kwargs['expected_commit'],
            checkpoint=legacy_identity,
        )
        if legacy.get('status') == 'missing':
            return current
        if legacy.get('status') != 'found':
            raise RuntimeError('fulltext_checkpoint_service_invalid_response')
        checkpoint = legacy.get('checkpoint')
        if not isinstance(checkpoint, dict) or any(
            checkpoint.get(key) != value for key, value in legacy_identity.items()
        ):
            raise RuntimeError('fulltext_checkpoint_identity_mismatch')
        output = checkpoint.get('output')
        runtime._validate_original_atom_contracts(
            [{'id': current_identity['chunk_id']}], [output]
        )
        try:
            receipt = service(
                'development-checkpoint-put',
                expected_commit=kwargs['expected_commit'],
                checkpoint={**current_identity, 'output': output},
            )
        except RuntimeError as error:
            if 'development_checkpoint_conflict' not in str(error):
                raise RuntimeError('fulltext_checkpoint_service_unavailable') from error
            reread = service(
                'development-checkpoint-get',
                expected_commit=kwargs['expected_commit'],
                checkpoint=current_identity,
            )
            if reread.get('status') != 'found':
                raise RuntimeError('fulltext_checkpoint_conflict') from error
            promoted = reread.get('checkpoint')
            if not isinstance(promoted, dict) or any(
                promoted.get(key) != value for key, value in current_identity.items()
            ):
                raise RuntimeError('fulltext_checkpoint_identity_mismatch') from error
            return reread
        if (
            receipt.get('status') != 'stored'
            or receipt.get('request_sha256') != current_identity.get('request_sha256')
        ):
            raise RuntimeError('fulltext_checkpoint_service_invalid_response')
        return {'status': 'found', 'checkpoint': {**current_identity, 'output': output}}

    return call


def resumable_post(original, payload, timeout=300, *, service=v2.service_call, candidate_id=None):
    """Reuse current checkpoints, with exact v2 chunk migration before inference."""
    return _V2_RESUMABLE_POST(
        original,
        payload,
        timeout,
        service=_migration_service(service),
        candidate_id=candidate_id,
    )


# Patch only the preserved implementation's runtime-resolved extension points.
v2.SYNTHESIS_ATOM_SCOPED_SCHEMA = SYNTHESIS_ATOM_SCOPED_SCHEMA
v2._atom_scoped_record_schema = _atom_scoped_record_schema
v2.atom_scoped_synthesis_schema = atom_scoped_synthesis_schema
v2.atom_scoped_bounded_synthesis_request = atom_scoped_bounded_synthesis_request
v2.install_assignment_scope = install_assignment_scope
v2.restore_assignment_scope = restore_assignment_scope
v2.resumable_post = resumable_post

# Preserve the existing module API for workflows and regression tests.
for _name in dir(v2):
    if not _name.startswith('__') and _name not in globals():
        globals()[_name] = getattr(v2, _name)


def main():
    return v2.main()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error)
        if code.startswith('fulltext_') or code.startswith('OA '):
            raise SystemExit(code) from None
        raise SystemExit('fulltext_calibration_development_failed') from None
