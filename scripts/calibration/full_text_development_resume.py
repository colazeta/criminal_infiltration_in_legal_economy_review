#!/usr/bin/env python3
"""Relation-safe v4 wrapper for the reviewed resumable full-text harness.

The reviewed v2 implementation is preserved byte-for-byte in
``full_text_development_resume_v2.py``. V3 added relation-array uniqueness and an
explicit referential-integrity prompt after a completed source pass failed closed
with ``fulltext_variable_relation``. The first natural v3 run reused all 15 exact
private chunk checkpoints and still failed with the same validator code.

V4 therefore keeps the base validator unchanged and adds one narrow, explicit
normalisation before a second validation attempt: a variable-use ``analysis_id``
may be replaced only when its already-emitted, non-empty, unique ``dataset_ids``
are contained by exactly one already-emitted analysis. Dataset links are never
added, removed or rewritten. Zero or multiple compatible analyses remain a
fail-closed error. The policy, count and a non-sensitive structural digest are
checkpointed and the policy is bound into the extractor fingerprint.

Because this remains a synthesis-only change, exact v3 and v2 chunk checkpoints
may be reused only when candidate, complete chunk request hash and the relevant
legacy extractor fingerprint all match; validated hits are promoted into the
current private namespace before use. No source text or model output is written
to public repository state.
"""
import copy

from scripts.calibration import full_text_development as development
from scripts.calibration import full_text_development_run as runtime
from scripts.calibration import full_text_development_resume_v2 as v2

LEGACY_V2_SYNTHESIS_ATOM_SCOPED_SCHEMA = v2.SYNTHESIS_ATOM_SCOPED_SCHEMA
LEGACY_V3_SYNTHESIS_ATOM_SCOPED_SCHEMA = 'destination-field-atom-and-relation-scoped-assignments-v3'
SYNTHESIS_ATOM_SCOPED_SCHEMA = 'destination-field-atom-and-relation-scoped-assignments-v4'
RELATION_NORMALISATION_POLICY = 'variable-analysis-id-unique-dataset-containment-v1'
RELATION_CONSISTENCY_SUFFIX = """Relational integrity is fail-closed. Every relationship id MUST reference a record you emit in this same JSON object. Dataset study_id must reference an emitted study. Analysis study_id must reference an emitted study and every analysis dataset_id must reference an emitted dataset belonging to that same study. Variable-use analysis_id must reference an emitted analysis and every variable-use dataset_id must be unique and drawn only from that analysis's dataset_ids. Finding analysis_id must reference an emitted analysis and every finding variable_use_id must be unique, reference an emitted variable use, and belong to the same analysis. Relationship arrays must not contain duplicate ids. If the supplied atoms do not support a relationship conservatively, omit the dependent record rather than inventing or guessing an id."""

_V2_ATOM_SCOPED_RECORD_SCHEMA = v2._atom_scoped_record_schema
_V2_ATOM_SCOPED_SYNTHESIS_SCHEMA = v2.atom_scoped_synthesis_schema
_V2_BOUNDED_SYNTHESIS_REQUEST = v2.atom_scoped_bounded_synthesis_request
_V2_INSTALL_ASSIGNMENT_SCOPE = v2.install_assignment_scope
_V2_RESTORE_ASSIGNMENT_SCOPE = v2.restore_assignment_scope
_V2_RESUMABLE_POST = v2.resumable_post
_ORIGINAL_RUNTIME_FINGERPRINT = runtime.runtime_extractor_fingerprint
_ORIGINAL_BUILD_PROPOSAL = development.build_proposal
_ORIGINAL_RUNTIME_CHECKPOINT_PAYLOAD = runtime.runtime_checkpoint_payload

RELATION_DIAGNOSTICS = {
    'normalised_variable_relations': 0,
    'normalisation_digest': development.sha(development.canonical([])),
}


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
    """Build the v4 request without changing source atoms or base validation."""
    request = _V2_BOUNDED_SYNTHESIS_REQUEST(atoms)
    system = request['messages'][0]['content']
    if RELATION_CONSISTENCY_SUFFIX not in system:
        request['messages'][0]['content'] = system + '\n' + RELATION_CONSISTENCY_SUFFIX
    return request


def relation_scoped_extractor_fingerprint():
    """Bind the exact prompt, decoder contract and relation-normalisation policy."""
    base = _ORIGINAL_RUNTIME_FINGERPRINT()
    return development.sha(development.canonical({
        'base_runtime_fingerprint': base,
        'relation_consistency_prompt': RELATION_CONSISTENCY_SUFFIX,
        'relation_schema_contract': SYNTHESIS_ATOM_SCOPED_SCHEMA,
        'relation_normalisation_policy': RELATION_NORMALISATION_POLICY,
    }))


def legacy_v3_extractor_fingerprint():
    """Reconstruct the exact #712 v3 fingerprint for chunk-only migration."""
    current_contract = runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA
    try:
        runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA = LEGACY_V3_SYNTHESIS_ATOM_SCOPED_SCHEMA
        base = _ORIGINAL_RUNTIME_FINGERPRINT()
        return development.sha(development.canonical({
            'base_runtime_fingerprint': base,
            'relation_consistency_prompt': RELATION_CONSISTENCY_SUFFIX,
            'relation_schema_contract': LEGACY_V3_SYNTHESIS_ATOM_SCOPED_SCHEMA,
        }))
    finally:
        runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA = current_contract


def legacy_v2_extractor_fingerprint():
    """Reconstruct the exact #711 v2 fingerprint for chunk-only migration."""
    current_contract = runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA
    try:
        runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA = LEGACY_V2_SYNTHESIS_ATOM_SCOPED_SCHEMA
        return _ORIGINAL_RUNTIME_FINGERPRINT()
    finally:
        runtime.SYNTHESIS_FIELD_SCOPED_SCHEMA = current_contract


def install_assignment_scope():
    """Install v4 synthesis constraints while preserving a restorable runtime."""
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


def _promote_legacy_checkpoint(service, kwargs, current_identity, legacy_fingerprint):
    legacy_identity = {
        **current_identity,
        'extractor_fingerprint': legacy_fingerprint,
    }
    if legacy_identity['extractor_fingerprint'] == current_identity.get('extractor_fingerprint'):
        return None
    legacy = service(
        'development-checkpoint-get',
        expected_commit=kwargs['expected_commit'],
        checkpoint=legacy_identity,
    )
    if legacy.get('status') == 'missing':
        return None
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


def _migration_service(service):
    """Read exact v3/v2 chunk checkpoints once and promote them into v4 privately."""
    def call(operation, **kwargs):
        if operation != 'development-checkpoint-get' or not _legacy_migration_enabled():
            return service(operation, **kwargs)

        current_identity = kwargs.get('checkpoint')
        current = service(operation, **kwargs)
        if current.get('status') != 'missing' or not isinstance(current_identity, dict):
            return current

        for fingerprint in (
            legacy_v3_extractor_fingerprint(),
            legacy_v2_extractor_fingerprint(),
        ):
            promoted = _promote_legacy_checkpoint(
                service, kwargs, current_identity, fingerprint,
            )
            if promoted is not None:
                return promoted
        return current

    return call


def resumable_post(original, payload, timeout=300, *, service=v2.service_call, candidate_id=None):
    """Reuse current checkpoints, with exact v3/v2 chunk migration before inference."""
    return _V2_RESUMABLE_POST(
        original,
        payload,
        timeout,
        service=_migration_service(service),
        candidate_id=candidate_id,
    )


def reset_relation_diagnostics():
    RELATION_DIAGNOSTICS.update({
        'normalised_variable_relations': 0,
        'normalisation_digest': development.sha(development.canonical([])),
    })


def _normalise_variable_analysis_relations(synthesis):
    """Repair only a uniquely implied variable->analysis edge; otherwise fail closed.

    The model's dataset relation set is retained byte-for-byte. A replacement
    analysis id is allowed only when exactly one already-emitted analysis contains
    every dataset already attached to that variable use. Empty, duplicate,
    unresolved or ambiguous dataset sets are never repaired.
    """
    if not isinstance(synthesis, dict):
        raise ValueError('fulltext_variable_relation_unresolved')
    analyses_raw = synthesis.get('analyses')
    variables_raw = synthesis.get('variable_uses')
    if not isinstance(analyses_raw, list) or not isinstance(variables_raw, list):
        raise ValueError('fulltext_variable_relation_unresolved')

    analyses = {}
    for analysis in analyses_raw:
        if not isinstance(analysis, dict) or not isinstance(analysis.get('id'), str):
            raise ValueError('fulltext_variable_relation_unresolved')
        datasets = analysis.get('dataset_ids')
        if not isinstance(datasets, list) or len(datasets) != len(set(datasets)):
            raise ValueError('fulltext_variable_relation_unresolved')
        analyses[analysis['id']] = set(datasets)

    repaired = copy.deepcopy(synthesis)
    changes = []
    repaired_variables = repaired.get('variable_uses', [])
    for index, variable in enumerate(repaired_variables):
        if not isinstance(variable, dict):
            raise ValueError('fulltext_variable_relation_unresolved')
        dataset_ids = variable.get('dataset_ids')
        analysis_id = variable.get('analysis_id')
        if not isinstance(dataset_ids, list) or not dataset_ids or len(dataset_ids) != len(set(dataset_ids)):
            raise ValueError('fulltext_variable_relation_unresolved')
        requested = set(dataset_ids)
        current = analyses.get(analysis_id)
        if current is not None and requested.issubset(current):
            continue
        compatible = sorted(
            candidate_id for candidate_id, candidate_datasets in analyses.items()
            if requested.issubset(candidate_datasets)
        )
        if len(compatible) != 1:
            raise ValueError('fulltext_variable_relation_unresolved')
        variable['analysis_id'] = compatible[0]
        changes.append({
            'variable_index': index,
            'dataset_count': len(dataset_ids),
            'prior_analysis_known': analysis_id in analyses,
        })

    if not changes:
        raise ValueError('fulltext_variable_relation_unresolved')
    return repaired, changes


def relation_normalising_build_proposal(target, source, atoms, synthesis):
    """Retry base validation once after explicit uniquely-implied graph normalisation."""
    try:
        return _ORIGINAL_BUILD_PROPOSAL(target, source, atoms, synthesis)
    except ValueError as error:
        if str(error) != 'fulltext_variable_relation':
            raise

    repaired, changes = _normalise_variable_analysis_relations(synthesis)
    proposal = _ORIGINAL_BUILD_PROPOSAL(target, source, atoms, repaired)
    synthesis.clear()
    synthesis.update(repaired)
    RELATION_DIAGNOSTICS.update({
        'normalised_variable_relations': len(changes),
        'normalisation_digest': development.sha(development.canonical(changes)),
    })
    return proposal


def relation_checkpoint_payload(payload):
    """Add only non-sensitive normalisation diagnostics to encrypted checkpoints."""
    enriched = _ORIGINAL_RUNTIME_CHECKPOINT_PAYLOAD(payload)
    return {
        **enriched,
        'runtime_relation_normalisation': {
            'policy': RELATION_NORMALISATION_POLICY,
            **RELATION_DIAGNOSTICS,
        },
    }


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
    reset_relation_diagnostics()
    prior_build = development.build_proposal
    prior_checkpoint_payload = runtime.runtime_checkpoint_payload
    development.build_proposal = relation_normalising_build_proposal
    runtime.runtime_checkpoint_payload = relation_checkpoint_payload
    try:
        return v2.main()
    finally:
        development.build_proposal = prior_build
        runtime.runtime_checkpoint_payload = prior_checkpoint_payload


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error)
        if code.startswith('fulltext_') or code.startswith('OA '):
            raise SystemExit(code) from None
        raise SystemExit('fulltext_calibration_development_failed') from None
