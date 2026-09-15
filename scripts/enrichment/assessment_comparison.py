#!/usr/bin/env python3
"""Private source-first F3 reference/comparison persistence.

This helper deliberately separates the reference pass from proposal inspection:
`source-packet` returns only current private source material; a reference assessment
must be persisted and read back before `comparison-packet` will fetch the public,
privacy-filtered current proposal projection. Nothing in this helper creates human
acceptance, calibration acceptance, F5 completion, or a public scientific decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from scripts.enrichment.service_client import ORIGIN, call, current_commit

REFERENCE_PROTOCOL = 'CILE-ASSESSMENT-REFERENCE-1'
COMPARISON_PROTOCOL = 'CILE-ASSESSMENT-COMPARISON-1'
HEX64 = set('0123456789abcdef')
ROOT = Path(__file__).resolve().parents[2]


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(value) -> str:
    raw = value if isinstance(value, (bytes, bytearray)) else canonical(value).encode()
    return hashlib.sha256(raw).hexdigest()


def private_write(path: Path, value) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, 'O_NOFOLLOW'):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, separators=(',', ':'))


def load_object(path: Path, label: str):
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise RuntimeError('invalid_' + label)
    return value


def source_snapshot(packet: dict) -> str:
    target = packet.get('target') or {}
    sources = packet.get('sources') or []
    if not sources or not any(source.get('evidence_kind') == 'full_text' for source in sources):
        raise RuntimeError('full_text_source_required')
    rows = []
    for source in sources:
        digest = source.get('content_sha256')
        text = source.get('text')
        if not isinstance(digest, str) or len(digest) != 64 or not isinstance(text, str) or hashlib.sha256(text.encode()).hexdigest() != digest:
            raise RuntimeError('source_integrity_failure')
        rows.append({key: source.get(key) for key in ('source_id','content_sha256','evidence_kind','source_url','version_label','observed_at')})
    rows.sort(key=canonical)
    return sha({'candidate_id': target.get('record_id'), 'input_sha256': target.get('input_sha256'), 'sources': rows})


def current_source_packet(candidate_id: str, expected_commit: str) -> dict:
    result = call('packet', expected_commit=expected_commit, target_id=None)
    # Packet without a target may select another candidate, so use the candidate's
    # target id only after resolving it from an explicitly retained packet file.
    if result.get('status') != 'source_ready' or result.get('target', {}).get('record_id') != candidate_id:
        raise RuntimeError('candidate_source_packet_not_selected')
    return result


def source_packet_by_target(target_id: str, candidate_id: str, expected_commit: str) -> dict:
    result = call('packet', expected_commit=expected_commit, target_id=target_id)
    if result.get('status') != 'source_ready' or result.get('target', {}).get('record_id') != candidate_id:
        raise RuntimeError('candidate_source_packet_unavailable')
    source_snapshot(result)
    return result


def native_validate(packet: dict, assessment: dict) -> None:
    payload = {'proposal': assessment, 'target': packet['target'], 'sources': packet['sources']}
    js = """import{validateExtraction}from'./curator-app/src/paper-enrichment.js';
import{inspectCompletionFacts,validateFrameworkAssessment}from'./curator-app/src/completion-policy.js';
let s='';for await(const c of process.stdin)s+=c;const p=JSON.parse(s);
validateExtraction(p.proposal,p.target,p.sources);if(p.proposal.source_coverage!=='full_text')throw Error('full_text_required');
const facts=inspectCompletionFacts(p.proposal);if(facts.unresolved)throw Error('unresolved_mandatory_facts');
validateFrameworkAssessment(p.proposal.framework);"""
    env = {'PATH': os.environ.get('PATH','/usr/bin:/bin'), 'HOME': os.environ.get('RUNNER_TEMP','/tmp')}
    checked = subprocess.run(['node','--input-type=module','-e',js], input=canonical(payload), text=True,
                             cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30, env=env)
    if checked.returncode:
        raise RuntimeError('reference_assessment_native_validation_failed')


def persist_reference(args) -> None:
    commit = args.expected_commit or current_commit()
    retained = load_object(args.packet, 'source_packet')
    target = retained.get('target') or {}
    candidate_id = target.get('record_id')
    target_id = target.get('target_id')
    if candidate_id != args.candidate_id or not isinstance(target_id, str):
        raise RuntimeError('reference_candidate_binding_failure')
    current = source_packet_by_target(target_id, candidate_id, commit)
    retained_snapshot, current_snapshot = source_snapshot(retained), source_snapshot(current)
    if retained_snapshot != current_snapshot or target.get('input_sha256') != current['target'].get('input_sha256'):
        raise RuntimeError('reference_source_packet_stale')
    assessment = load_object(args.assessment, 'reference_assessment')
    native_validate(current, assessment)
    if assessment.get('target_id') != target_id or assessment.get('input_sha256') != target.get('input_sha256'):
        raise RuntimeError('reference_assessment_binding_failure')
    agent = (assessment.get('generated_by') or {}).get('agent','')
    if not isinstance(agent, str) or not agent.startswith('independent-reference:'):
        raise RuntimeError('independent_reference_agent_required')
    assessment_sha = sha(assessment)
    request_sha = sha({'protocol':REFERENCE_PROTOCOL,'candidate_id':candidate_id,'input_sha256':target['input_sha256'],
                       'source_snapshot_sha256':current_snapshot,'assessment_sha256':assessment_sha,
                       'generated_by':assessment.get('generated_by')})
    checkpoint = {'protocol':REFERENCE_PROTOCOL,'candidate_id':candidate_id,'input_sha256':target['input_sha256'],
                  'source_snapshot_sha256':current_snapshot,'request_sha256':request_sha,'stage':'reference',
                  'output':{'assessment':assessment}}
    receipt = call('development-checkpoint-put', expected_commit=commit, checkpoint=checkpoint)
    identity = {key: checkpoint[key] for key in ('protocol','candidate_id','input_sha256','source_snapshot_sha256','request_sha256','stage')}
    readback = call('development-checkpoint-get', expected_commit=commit, checkpoint=identity)
    if readback.get('status') != 'found' or sha(readback['checkpoint']['output']['assessment']) != assessment_sha:
        raise RuntimeError('reference_checkpoint_readback_failed')
    if args.identity_output:
        private_write(args.identity_output, identity)
    print(canonical({'status':'reference_persisted_readback_verified','candidate_id':candidate_id,'reference_sha256':assessment_sha,
                     'source_snapshot_sha256':current_snapshot,'request_sha256':request_sha,'scientific_validation':False,'assessment_completed':False}))


def source_packet(args) -> None:
    commit = args.expected_commit or current_commit()
    packet = source_packet_by_target(args.target_id, args.candidate_id, commit)
    snapshot = source_snapshot(packet)
    private_write(args.output, packet)
    print(canonical({'status':'source_first_packet_written','candidate_id':args.candidate_id,'input_sha256':packet['target']['input_sha256'],
                     'source_snapshot_sha256':snapshot,'private_output_written':True}))


def read_reference(identity: dict, commit: str) -> dict:
    result = call('development-checkpoint-get', expected_commit=commit, checkpoint=identity)
    if result.get('status') != 'found' or result.get('checkpoint',{}).get('protocol') != REFERENCE_PROTOCOL:
        raise RuntimeError('reference_checkpoint_required')
    return result['checkpoint']


def public_research(candidate_id: str) -> dict:
    url = ORIGIN + '/api/public-paper-research?id=' + quote(candidate_id, safe='')
    with urlopen(Request(url, headers={'Accept':'application/json','User-Agent':'cile-assessment-comparison/1.0'}), timeout=20) as response:
        data = json.load(response)
    if data.get('availability') != 'available' or not isinstance(data.get('revision'), str) or len(data['revision']) != 64 or not isinstance(data.get('research'), dict):
        raise RuntimeError('current_proposal_projection_unavailable')
    return data


def comparison_packet(args) -> None:
    commit = args.expected_commit or current_commit()
    identity = load_object(args.reference_identity, 'reference_identity')
    reference = read_reference(identity, commit)
    if reference.get('candidate_id') != args.candidate_id:
        raise RuntimeError('reference_candidate_binding_failure')
    proposal = public_research(args.candidate_id)
    packet = {'protocol':COMPARISON_PROTOCOL,'candidate_id':args.candidate_id,'input_sha256':reference['input_sha256'],
              'source_snapshot_sha256':reference['source_snapshot_sha256'],'reference_sha256':sha(reference['output']['assessment']),
              'proposal_revision':proposal['revision'],'reference_assessment':reference['output']['assessment'],
              'proposal_projection':proposal}
    private_write(args.output, packet)
    print(canonical({'status':'comparison_packet_written_after_reference_readback','candidate_id':args.candidate_id,
                     'reference_sha256':packet['reference_sha256'],'proposal_revision':packet['proposal_revision'],'private_output_written':True}))


def persist_comparison(args) -> None:
    commit = args.expected_commit or current_commit()
    packet = load_object(args.packet, 'comparison_packet')
    result = load_object(args.comparison, 'comparison_result')
    required = {'assessor','source_fidelity','omissions','classification_agreement','field_accuracy','mandatory_disagreement_paths','optional_disagreement_paths','compared_at'}
    if set(result) != required:
        raise RuntimeError('invalid_comparison_result_fields')
    candidate_id = packet.get('candidate_id')
    if candidate_id != args.candidate_id:
        raise RuntimeError('comparison_candidate_binding_failure')
    # The current proposal projection is re-read immediately before persistence;
    # any changed revision invalidates the comparison rather than silently inheriting it.
    current = public_research(candidate_id)
    if current.get('revision') != packet.get('proposal_revision'):
        raise RuntimeError('comparison_proposal_projection_stale')
    comparison = {'protocol':COMPARISON_PROTOCOL,'candidate_id':candidate_id,'input_sha256':packet['input_sha256'],
                  'source_snapshot_sha256':packet['source_snapshot_sha256'],'proposal_revision':packet['proposal_revision'],
                  'reference_sha256':packet['reference_sha256'],**result}
    request_sha = sha({'protocol':COMPARISON_PROTOCOL,'candidate_id':candidate_id,'input_sha256':packet['input_sha256'],
                       'source_snapshot_sha256':packet['source_snapshot_sha256'],'proposal_revision':packet['proposal_revision'],
                       'reference_sha256':packet['reference_sha256'],'assessor':result['assessor']})
    checkpoint = {'protocol':COMPARISON_PROTOCOL,'candidate_id':candidate_id,'input_sha256':packet['input_sha256'],
                  'source_snapshot_sha256':packet['source_snapshot_sha256'],'proposal_revision':packet['proposal_revision'],
                  'reference_sha256':packet['reference_sha256'],'request_sha256':request_sha,'stage':'comparison',
                  'output':{'comparison':comparison}}
    receipt = call('development-checkpoint-put', expected_commit=commit, checkpoint=checkpoint)
    identity = {key: checkpoint[key] for key in ('protocol','candidate_id','input_sha256','source_snapshot_sha256','proposal_revision','reference_sha256','request_sha256','stage')}
    readback = call('development-checkpoint-get', expected_commit=commit, checkpoint=identity)
    if readback.get('status') != 'found' or sha(readback['checkpoint']['output']['comparison']) != sha(comparison):
        raise RuntimeError('comparison_checkpoint_readback_failed')
    if args.identity_output:
        private_write(args.identity_output, identity)
    print(canonical({'status':'independent_comparison_persisted_readback_verified','candidate_id':candidate_id,
                     'proposal_revision':packet['proposal_revision'],'reference_sha256':packet['reference_sha256'],
                     'source_snapshot_sha256':packet['source_snapshot_sha256'],'request_sha256':request_sha,
                     'assessment_frontier':'F3','scientific_validation':False,'assessment_completed':False}))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    def common(q):
        q.add_argument('--candidate-id', required=True);q.add_argument('--expected-commit')
    q=sub.add_parser('source-packet');common(q);q.add_argument('--target-id',required=True);q.add_argument('--output',type=Path,required=True);q.set_defaults(func=source_packet)
    q=sub.add_parser('persist-reference');common(q);q.add_argument('--packet',type=Path,required=True);q.add_argument('--assessment',type=Path,required=True);q.add_argument('--identity-output',type=Path);q.set_defaults(func=persist_reference)
    q=sub.add_parser('comparison-packet');common(q);q.add_argument('--reference-identity',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.set_defaults(func=comparison_packet)
    q=sub.add_parser('persist-comparison');common(q);q.add_argument('--packet',type=Path,required=True);q.add_argument('--comparison',type=Path,required=True);q.add_argument('--identity-output',type=Path);q.set_defaults(func=persist_comparison)
    return p


def main() -> None:
    args=parser().parse_args();args.func(args)

if __name__=='__main__':
    try: main()
    except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as error: raise SystemExit(str(error)) from None
