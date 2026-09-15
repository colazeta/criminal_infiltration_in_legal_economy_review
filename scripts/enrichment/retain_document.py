#!/usr/bin/env python3
"""Retain reviewed PDFs in the existing private store.

The fixed reviewed seed remains hash-pinned. After its readback, a bounded B-shard
frontier reuses only already-governed public-full-text access evidence and the
candidate-bound F1 lease. No model, citation search, public redistribution or
scientific decision is performed. Original PDF/text bodies are never printed,
committed or uploaded as workflow artifacts.
"""
import argparse
import base64
import hashlib
import json
import os
import re
from pathlib import Path
from scripts.calibration.full_text_source_case import candidate, extract_text, norm
from scripts.oa_acquisition import acquire_pdf
from scripts.enrichment.service_client import call
from scripts.enrichment.retain_frontier_documents import run_frontier

ROOT = Path(__file__).resolve().parents[2]
FIELDS = {'protocol','candidate_id','source_url','pdf_sha256','text_sha256','version_label',
          'retention_basis','licence_status','attribution','visibility','licence_url','rights_verified'}

def validate_manifest(data):
    if not isinstance(data, dict) or set(data) != FIELDS or data['protocol'] != 'CILE-VERIFIED-DOCUMENT-1':
        raise RuntimeError('invalid_document_manifest')
    for key in ('pdf_sha256','text_sha256'):
        if not re.fullmatch(r'[a-f0-9]{64}', str(data[key])):
            raise RuntimeError('invalid_document_manifest')
    if data['visibility'] not in {'private','public'} or type(data['rights_verified']) is not bool:
        raise RuntimeError('invalid_document_manifest')
    for key in ('retention_basis','licence_status','attribution','version_label'):
        if not isinstance(data[key],str) or not data[key].strip():
            raise RuntimeError('document_rights_basis_missing')
    if data['visibility']=='public' and not data['rights_verified']:
        raise RuntimeError('document_redistribution_not_authorised')
    candidate(data['candidate_id'],data['source_url'])
    return data


def retain(manifest, expected_commit, service=call, acquire=acquire_pdf, extract=extract_text):
    data=validate_manifest(manifest)
    record=candidate(data['candidate_id'],data['source_url'])
    cycle=json.loads((ROOT/'config/archive-cycle.json').read_text())['review_id']
    target_id=hashlib.sha256((cycle+':candidate:'+record['id']).encode()).hexdigest()
    packet=service('packet',expected_commit=expected_commit,target_id=target_id)
    target=packet.get('target')
    if not target or target.get('record_id')!=record['id']:
        raise RuntimeError('document_target_unavailable')
    current=json.loads(target['record_json'])
    if current['title']!=record['title'] or current['sourceLinks']!=record['sourceLinks']:
        raise RuntimeError('document_target_changed')
    existing=service('documents',expected_commit=expected_commit,target_id=target_id)['documents']
    # Reuse only the same bytes, manifestation and rights; read the real reader route.
    for doc in existing:
        if all(doc.get(k)==data[k] for k in ('pdf_sha256','source_url','version_label','visibility','licence_status','licence_url','attribution')):
            checked=service('document-check',expected_commit=expected_commit,target_id=target_id,document_id=doc['document_id'])
            if checked.get('readable') is not True or checked.get('content_type')!='application/pdf':
                raise RuntimeError('document_reader_not_verified')
            return {'candidate_id':record['id'],'status':'retained_readback_verified','replayed':True,'pdf_sha256':data['pdf_sha256'],'byte_length':doc['byte_length'],'visibility':doc['visibility'],'reader_check':checked,'scientific_validation':False}
    pdf, observation=acquire(data['source_url'])
    if len(pdf)>4194304 or hashlib.sha256(pdf).hexdigest()!=data['pdf_sha256'] or observation['full_text_sha256']!=data['pdf_sha256']:
        raise RuntimeError('document_pdf_changed')
    text=extract(pdf)
    if hashlib.sha256(text.encode()).hexdigest()!=data['text_sha256']:
        raise RuntimeError('document_text_changed')
    # The hash pins independently inspected bytes; the title adds a visible-identity check.
    title=norm(record['title']).split(':')[0]
    if title not in norm(text[:20000]):
        raise RuntimeError('document_title_mismatch')
    source=service('source',expected_commit=expected_commit,target_id=target_id,source={
        'input_sha256':target['input_sha256'],'source_url':observation['full_text_url'],
        'evidence_kind':'full_text','text':text,'version_label':data['version_label'],'language':None,
        'retention_basis':data['retention_basis'],'licence_status':data['licence_status']})
    result=service('document',expected_commit=expected_commit,target_id=target_id,document={
        'input_sha256':target['input_sha256'],'source_id':source['source_id'],
        'pdf_sha256':data['pdf_sha256'],'source_text_sha256':data['text_sha256'],
        'bytes_base64':base64.b64encode(pdf).decode(),
        **{k:data[k] for k in ('retention_basis','licence_status','licence_url','attribution','visibility','rights_verified')}})
    checked=service('document-check',expected_commit=expected_commit,target_id=target_id,document_id=result['document_id'])
    if checked.get('readable') is not True or checked.get('byte_length')!=len(pdf):
        raise RuntimeError('document_reader_not_verified')
    return {'candidate_id':record['id'],'status':'retained_readback_verified','replayed':result['replayed'],
            'pdf_sha256':data['pdf_sha256'],'text_sha256':data['text_sha256'],'byte_length':len(pdf),
            'visibility':data['visibility'],'reader_check':checked,'scientific_validation':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,default=ROOT/'config/verified-document-seed.json')
    p.add_argument('--expected-commit',default=os.environ.get('GITHUB_SHA'))
    p.add_argument('--frontier-limit',type=int,default=3)
    a=p.parse_args()
    if not re.fullmatch(r'[a-f0-9]{40}',a.expected_commit or ''):
        p.error('An exact reviewed/deployed commit is required.')
    if a.frontier_limit < 1 or a.frontier_limit > 6:
        p.error('--frontier-limit must be between 1 and 6')
    seed=retain(json.loads(a.manifest.read_text()),a.expected_commit)
    cycle=json.loads((ROOT/'config/archive-cycle.json').read_text())['review_id']
    target_id=hashlib.sha256((cycle+':candidate:'+seed['candidate_id']).encode()).hexdigest()
    seed['provider_bibliography']=call('provider-bibliography',expected_commit=a.expected_commit,target_id=target_id)
    frontier=run_frontier(a.expected_commit,a.frontier_limit)
    print(json.dumps({'seed':seed,'frontier':frontier},indent=2))
    if frontier and not any(item['status'] in {'retained_readback_verified','already_retained_current_input'} for item in frontier):
        raise RuntimeError('frontier_retention_no_success')

if __name__=='__main__':
    try:main()
    except Exception as error:
        code=str(error)
        if not re.fullmatch(r'(?:document_[a-z_]+|frontier_[a-z_]+|enrichment_service_[a-z0-9_:]+|invalid_document_manifest)',code):code='document_retention_failed'
        raise SystemExit(code) from None
