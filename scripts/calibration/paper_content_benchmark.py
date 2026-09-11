#!/usr/bin/env python3
"""Bounded abstract-only content benchmark; no production API or authentication."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import tarfile
import tempfile
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, build_opener, HTTPRedirectHandler, urlopen
from scripts.enrichment.pilot import download, model_request, prepare_proposal

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'CILE-ABSTRACT-BENCHMARK-1'
# A preselected heterogeneous pool, not inferred labels or accepted review members.
DOIS = [
 '10.1111/1475-679x.12455', '10.1111/gove.12648',
 '10.1177/17488958241293927', '10.1007/s11156-021-00984-3',
 '10.1016/j.cpa.2018.08.003', '10.1080/17440572.2024.2402848',
 '10.2308/tar-2019-0079', '10.22495/cocv21i3siart10',
 '10.3390/g13010008', '10.1007/s10551-014-2304-7',
 '10.1007/s11187-018-0003-y', '10.1111/jors.12612',
 '10.1108/jpbafm-03-2023-0041', '10.1111/emre.12039',
 '10.1080/17440572.2025.2567277', '10.1007/s11187-020-00439-4',
 '10.1007/s10611-021-09975-w', '10.1177/1748895812465296',
 '10.1086/708870', '10.1111/rego.70194',
 '10.1093/bjc/azv001', '10.1007/s10611-005-5655-2',
 '10.1080/13608746.2019.1575563', '10.1007/s11187-019-00250-w']

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError('benchmark_redirect_refused')

HTTP = build_opener(NoRedirect())

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def normal_title(value):
    text = ''.join(c for c in unicodedata.normalize('NFKD', value).lower()
                   if not unicodedata.category(c).startswith('M'))
    return re.sub(r'[^\w]+', ' ', text, flags=re.UNICODE).replace('_', ' ').strip()

def packet_for(record, message):
    """Preserve the returned original abstract and reject uncertain bibliographic identity."""
    doi = record['doi'].lower()
    if str(message.get('DOI', '')).lower() != doi:
        raise ValueError('benchmark_identity_mismatch')
    titles = message.get('title', [])
    if not titles or normal_title(titles[0]) != normal_title(record['title']):
        raise ValueError('benchmark_identity_mismatch')
    text = message.get('abstract')
    if not isinstance(text, str) or not text.strip():
        raise ValueError('benchmark_abstract_not_returned')
    if len(text) > 14000:
        raise ValueError('benchmark_source_over_limit')
    identity = {k: record[k] for k in ['id', 'title', 'doi', 'sourceLinks']}
    digest = hashlib.sha256(text.encode()).hexdigest()
    target_id = hashlib.sha256((PROTOCOL + record['id']).encode()).hexdigest()
    input_hash = hashlib.sha256(canonical(identity).encode()).hexdigest()
    source = {'source_id': hashlib.sha256((target_id + digest).encode()).hexdigest(),
              'target_id': target_id, 'input_sha256': input_hash, 'evidence_kind': 'abstract',
              'text': text, 'content_sha256': digest, 'provider': 'Crossref',
              'source_url': 'https://api.crossref.org/works/' + quote(doi, safe=''),
              'observed_at': datetime.now(timezone.utc).isoformat(),
              'version_label': 'Crossref original deposited abstract; benchmark only'}
    return {'target': {'target_id': target_id, 'input_sha256': input_hash,
                       'record_id': record['id'], 'record_json': canonical(identity)},
            'sources': [source], 'scope': 'offline_benchmark_not_a_production_receipt'}

def retrieve(record):
    request = Request('https://api.crossref.org/works/' + quote(record['doi'], safe=''),
                      headers={'User-Agent': 'cile-bounded-content-benchmark/1.0',
                               'Accept': 'application/json'})
    with HTTP.open(request, timeout=20) as response:
        data = response.read(3000001)
    if len(data) > 3000000:
        raise ValueError('benchmark_response_limit')
    return packet_for(record, json.loads(data)['message'])

def seal_output(output, payload):
    """Use the already reviewed transport, with a separate short-lived benchmark recipient."""
    js = """import{readFileSync,writeFileSync}from'node:fs';
import{seal}from'./scripts/enrichment/seal-audit.mjs';
let s='';for await(const c of process.stdin)s+=c;
const recipient=JSON.parse(readFileSync('config/enrichment-benchmark-recipient.json','utf8'));
writeFileSync(process.argv[1],JSON.stringify(seal(Buffer.from(s),recipient)),{flag:'wx',mode:0o600});"""
    temporary = output.with_name(output.name + '.next')
    temporary.unlink(missing_ok=True)
    result = subprocess.run(['node', '--input-type=module', '-e', js, str(temporary)],
                            input=canonical(payload), text=True, cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=20, env={'PATH': os.environ.get('PATH', '/usr/bin:/bin')})
    if result.returncode:
        temporary.unlink(missing_ok=True)
        raise RuntimeError('benchmark_sealing_failed')
    os.replace(temporary, output)

def evaluate(binary, weights, work, packets, checkpoint):
    environment = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
                   'HOME': str(work), 'LD_LIBRARY_PATH': str(binary.parent)}
    process = subprocess.Popen([str(binary), '-m', str(weights), '-c', '16384', '-t', '4',
                                '-ngl', '0', '--host', '127.0.0.1', '--port', '8181'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=environment)
    results = []
    try:
        for _ in range(90):
            if process.poll() is not None:
                raise RuntimeError('benchmark_engine_failed')
            try:
                with urlopen('http://127.0.0.1:8181/health', timeout=1) as response:
                    if response.status == 200:
                        break
            except (URLError, TimeoutError):
                time.sleep(1)
        else:
            raise RuntimeError('benchmark_engine_timeout')
        for i, packet in enumerate(packets):
            result = {'record_id': packet['target']['record_id'], 'status': 'failed'}
            try:
                payload = model_request(packet['sources'][0]['text'])
                result['request_sha256'] = hashlib.sha256(canonical(payload).encode()).hexdigest()
                request = Request('http://127.0.0.1:8181/v1/chat/completions',
                                  data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
                with urlopen(request, timeout=300) as response:
                    answer = json.loads(response.read(100001))
                if answer['choices'][0].get('finish_reason') != 'stop':
                    raise ValueError('benchmark_output_incomplete')
                extracted = json.loads(answer['choices'][0]['message']['content'])
                result['model_output'] = extracted
                proposal = prepare_proposal(packet, extracted)
                js = "import{validateExtraction}from'./curator-app/src/paper-enrichment.js';let s='';for await(const c of process.stdin)s+=c;const p=JSON.parse(s);validateExtraction(p.proposal,p.target,p.sources);"
                checked = subprocess.run(['node','--input-type=module','-e',js],
                    input=canonical({'proposal':proposal,**packet}),text=True,cwd=ROOT,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20,env=environment)
                if checked.returncode:
                    raise ValueError('benchmark_native_validation_failed')
                result.update({'status':'structurally_valid_unreviewed','proposal':proposal})
            except Exception as error:
                known = {'benchmark_output_incomplete','benchmark_native_validation_failed',
                         'pilot_summary_required','pilot_fact_shape','pilot_fact_bounds',
                         'pilot_unknown_or_duplicate_block','pilot_variable_shape','pilot_framework_ungrounded',
                         'pilot_framework_shape','pilot_schema_keys','pilot_finding_limit','pilot_variable_limit'}
                result['error_code'] = str(error) if str(error) in known else 'benchmark_case_failed_no_content_logged'
            results.append(result)
            checkpoint(results)
            print(json.dumps({'case':i+1,'status':result['status'],'error_code':result.get('error_code')}), flush=True)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=10)
    return results

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources-output',type=Path,required=True)
    parser.add_argument('--results-output',type=Path,required=True)
    args=parser.parse_args()
    recipient=json.loads((ROOT/'config/enrichment-benchmark-recipient.json').read_text())
    if datetime.now(timezone.utc)>=datetime.fromisoformat(recipient['expires_at'].replace('Z','+00:00')):
        raise RuntimeError('benchmark_recipient_expired')
    records=json.loads((ROOT/'site/data/paper-register.json').read_text())['records']
    by_doi={}
    for record in records:
        by_doi.setdefault(record.get('doi','').lower(),record)
    packets=[];availability=[]
    for doi in DOIS:
        if len(packets)>=18:
            break
        record=by_doi.get(doi)
        if not record:
            availability.append({'doi':doi,'status':'not_in_current_register'});continue
        try:
            packet=retrieve(record);packets.append(packet)
            availability.append({'doi':doi,'status':'abstract_ready'})
        except Exception as error:
            status=str(error) if str(error) in {'benchmark_identity_mismatch','benchmark_abstract_not_returned',
                'benchmark_source_over_limit','benchmark_response_limit','benchmark_redirect_refused'} else 'provider_or_decode_failure'
            availability.append({'doi':doi,'status':status})
        time.sleep(1)
    seal_output(args.sources_output,{'protocol':PROTOCOL,'packets':packets,'availability':availability})
    print(json.dumps({'sources_ready':len(packets),'attempted':len(availability),
                      'production_access':False,'scientific_validation':False}),flush=True)
    if len(packets)<12:
        raise RuntimeError('benchmark_insufficient_source_coverage')
    with tempfile.TemporaryDirectory(prefix='cile-benchmark-',dir=os.environ.get('RUNNER_TEMP')) as directory:
        work=Path(directory);os.chmod(work,0o700)
        archive_path=work/'engine.tar.gz';weights=work/'model.gguf'
        download('https://github.com/ggml-org/llama.cpp/releases/download/b10333/llama-b10333-bin-ubuntu-x64.tar.gz',archive_path,'936ce04d98abe2a977e9dd2ff92659bb96947e136acee8f2bc3e21d8eaebbf23',30000000)
        download('https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen3-4B-Instruct-2507-Q4_K_M.gguf',weights,'3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597',3000000000)
        with tarfile.open(archive_path) as archive:
            archive.extractall(work/'bin',filter='data')
        binary=next((work/'bin').rglob('llama-server'));os.chmod(binary,0o700)
        checkpoint=lambda results: seal_output(args.results_output,{'protocol':PROTOCOL,'results':results,'scientific_validation':False})
        results=evaluate(binary,weights,work,packets,checkpoint)
        seal_output(args.results_output,{'protocol':PROTOCOL,'results':results,'scientific_validation':False})
        valid=sum(r['status']=='structurally_valid_unreviewed' for r in results)
        print(json.dumps({'cases':len(results),'structurally_valid':valid,'scientific_validation':False,
                          'production_proposals_written':0}),flush=True)
        if valid!=len(results):
            raise RuntimeError('benchmark_structural_failures_require_review')

if __name__=='__main__':
    try:
        main()
    except Exception as error:
        known={'benchmark_recipient_expired','benchmark_sealing_failed','benchmark_insufficient_source_coverage',
               'benchmark_engine_failed','benchmark_engine_timeout','benchmark_structural_failures_require_review'}
        raise SystemExit(str(error) if str(error) in known else 'benchmark_failed_no_content_logged') from None
