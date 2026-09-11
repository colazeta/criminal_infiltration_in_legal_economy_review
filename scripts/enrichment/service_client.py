#!/usr/bin/env python3
"""Narrow authenticated enrichment operations; never print credentials or source/proposal bodies."""
import argparse
import hashlib
import hmac
import json
import os
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler

ORIGIN = 'https://criminal-infiltration-curator.colazeta-research.workers.dev'
DOMAIN = 'CILE-ENRICH-SERVICE-v1'

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        raise RuntimeError('service_redirect_refused')

_PRIVATE_HTTP = build_opener(NoRedirect())


def call(operation, *, expected_commit, target_id=None, proposal=None, run_key=None):
    secret = os.environ.get('CURATOR_SESSION_SECRET', '')
    if len(secret) < 32:
        raise RuntimeError('service_credential_unavailable')
    payload = {'operation': operation, 'expected_commit': expected_commit}
    if target_id is not None: payload['target_id'] = target_id
    if proposal is not None: payload['proposal'] = proposal
    if operation == 'run': payload['run_key'] = run_key or 'manual:' + str(uuid.uuid4())
    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()
    timestamp, nonce = str(int(time.time() * 1000)), str(uuid.uuid4())
    derived = hmac.new(secret.encode(), DOMAIN.encode(), hashlib.sha256).digest()
    signature = hmac.new(derived, (DOMAIN + '\n' + timestamp + '\n' + nonce + '\n').encode() + body, hashlib.sha256).hexdigest()
    req = Request(ORIGIN + '/api/paper-enrichment-machine', data=body, headers={
        'Content-Type': 'application/json', 'X-Enrichment-Timestamp': timestamp,
        'X-Enrichment-Nonce': nonce, 'X-Enrichment-Signature': signature,
    }, method='POST')
    try:
        with _PRIVATE_HTTP.open(req, timeout=90) as response:
            raw = response.read(9000001)
        if len(raw) > 9000000: raise RuntimeError('service_response_limit')
        return json.loads(raw)
    except HTTPError as error:
        # No raw server body, input, signature, or authentication material enters logs.
        raise RuntimeError('enrichment_service_http_' + str(error.code)) from None
    except (URLError, TimeoutError, ValueError):
        raise RuntimeError('enrichment_service_transport_or_decode_failure') from None


def current_commit():
    with urlopen(Request(ORIGIN + '/version', headers={'Accept':'application/json'}), timeout=15) as response:
        data = json.load(response)
    commit = data.get('commit', '')
    if not isinstance(commit, str) or len(commit) != 40: raise RuntimeError('invalid_deployment_version')
    return commit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=['verify','activate','deactivate','run','status','packet','proposal'])
    p.add_argument('--expected-commit', default=os.environ.get('GITHUB_SHA'))
    p.add_argument('--target-id');p.add_argument('--input',type=Path);p.add_argument('--output',type=Path)
    args=p.parse_args()
    if args.operation=='packet' and args.output is None: p.error('Private packets require --output; stdout is prohibited.')
    if args.operation=='proposal' and args.input is None: p.error('Proposal import requires --input.')
    result=call(args.operation,expected_commit=args.expected_commit or current_commit(),target_id=args.target_id,
                proposal=json.loads(args.input.read_text()) if args.input else None)
    if args.output:
        fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w') as out: json.dump(result,out,ensure_ascii=False)
        print(json.dumps({'operation':args.operation,'private_output_written':True,'status':result.get('status')}))
    else:
        print(json.dumps(result,indent=2))

if __name__=='__main__':
    try: main()
    except RuntimeError as error: raise SystemExit(str(error)) from None
