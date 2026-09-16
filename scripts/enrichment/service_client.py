#!/usr/bin/env python3
"""Narrow authenticated enrichment operations; never print credentials or source/proposal bodies."""
import argparse
import hashlib
import hmac
import json
import os
import re
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

_SAFE_CODES = {'service_authentication_required', 'service_auth_state_unavailable', 'private_storage_required', 'stale_deployment',
               'service_operation_failed', 'enrichment_inactive', 'payload_too_large',
               'development_checkpoint_conflict', 'development_checkpoint_invalid',
               'development_checkpoint_corrupt', 'development_checkpoint_identity_mismatch',
               'development_checkpoint_too_large', 'sqlite_storage_required',
               'migration_bundle_integrity', 'additive_migration_required',
               'schedule_migration_integrity', 'additive_schedule_migration_required',
               'adjudication_migration_integrity', 'additive_adjudication_migration_required',
               'delivery_migration_integrity', 'additive_delivery_migration_required',
               'storage_readback_failed', 'store_init_sqlite_failed',
               'store_init_base_migration_failed', 'store_init_schedule_migration_failed',
               'store_init_adjudication_migration_failed', 'store_init_delivery_migration_failed',
               'store_init_adapters_failed', 'store_init_scheduler_failed', 'store_init_unknown_failed'}


def classify_private_error(value):
    """Return a closed diagnostic class; never return the server-supplied text."""
    if not isinstance(value, str) or not value:
        return None
    if value in _SAFE_CODES:
        return value
    lowered = value.casefold()
    patterns = (
        (r'no such table', 'store_sql_missing_table'),
        (r'no such column', 'store_sql_missing_column'),
        (r'(?:table|index|trigger).*(?:already exists)|already exists', 'store_sql_already_exists'),
        (r'(?:constraint|unique constraint|foreign key)', 'store_sql_constraint_error'),
        (r'(?:database is locked|database is busy|\bbusy\b|\blocked\b)', 'store_sql_busy'),
        (r'(?:cannot start a transaction|within a transaction|transaction)', 'store_transaction_error'),
        (r'(?:sqlite|sql error|syntax error|near .+ syntax)', 'store_sql_error'),
        (r'(?:storage|durable object storage|kv)', 'store_storage_error'),
        (r'(?:is not a function|cannot read propert|undefined|null is not|not iterable)', 'store_runtime_shape_error'),
        (r'(?:maximum call stack|out of memory|memory limit|cpu time)', 'store_runtime_resource_error'),
    )
    for pattern, category in patterns:
        if re.search(pattern, lowered):
            return category
    fingerprint = hashlib.sha256(value.encode('utf-8', errors='replace')).hexdigest()[:12]
    return 'store_unknown_error_' + fingerprint


def call(operation, *, expected_commit, target_id=None, proposal=None, run_key=None, source=None, document=None,
         bibliography=None, document_id=None, checkpoint=None):
    secret = os.environ.get('CURATOR_SESSION_SECRET', '')
    if len(secret) < 32:
        raise RuntimeError('service_credential_unavailable')
    payload = {'operation': operation, 'expected_commit': expected_commit}
    if target_id is not None: payload['target_id'] = target_id
    if proposal is not None: payload['proposal'] = proposal
    for name, value in [('source', source), ('document', document), ('bibliography', bibliography),
                        ('document_id', document_id), ('checkpoint', checkpoint)]:
        if value is not None: payload[name] = value
    if operation == 'run': payload['run_key'] = run_key or 'manual:' + str(uuid.uuid4())
    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()
    timestamp, nonce = str(int(time.time() * 1000)), str(uuid.uuid4())
    derived = hmac.new(secret.encode(), DOMAIN.encode(), hashlib.sha256).digest()
    signature = hmac.new(derived, (DOMAIN + '\n' + timestamp + '\n' + nonce + '\n').encode() + body, hashlib.sha256).hexdigest()
    req = Request(ORIGIN + '/api/paper-enrichment-machine', data=body, headers={
        'Content-Type': 'application/json', 'Accept': 'application/json',
        'User-Agent': 'cile-enrichment-service/1.0', 'X-Enrichment-Timestamp': timestamp,
        'X-Enrichment-Nonce': nonce, 'X-Enrichment-Signature': signature,
    }, method='POST')
    try:
        with _PRIVATE_HTTP.open(req, timeout=90) as response:
            raw = response.read(9000001)
        if len(raw) > 9000000: raise RuntimeError('service_response_limit')
        return json.loads(raw)
    except HTTPError as error:
        suffix = ''
        try:
            raw = error.read(4096)
            data = json.loads(raw)
            code = data.get('error_code') or (data.get('error', {}).get('code') if isinstance(data.get('error'), dict) else None)
            category = classify_private_error(code)
            if category:
                suffix = ':' + category
        except (ValueError, TypeError, AttributeError):
            suffix = ':non_json_response'
        raise RuntimeError('enrichment_service_http_' + str(error.code) + suffix) from None
    except (URLError, TimeoutError, ValueError):
        raise RuntimeError('enrichment_service_transport_or_decode_failure') from None


def current_commit():
    with urlopen(Request(ORIGIN + '/version', headers={'Accept':'application/json','User-Agent':'cile-enrichment-service/1.0'}), timeout=15) as response:
        data = json.load(response)
    commit = data.get('commit', '')
    if not isinstance(commit, str) or len(commit) != 40: raise RuntimeError('invalid_deployment_version')
    return commit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=['verify','activate','deactivate','run','status','packet','proposal','public-research-audit'])
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
    if args.operation == 'run' and result.get('status') not in {'completed','partial','empty','slot_already_observed','leased'}:
        raise RuntimeError('enrichment_job_not_successful')

if __name__=='__main__':
    try: main()
    except RuntimeError as error: raise SystemExit(str(error)) from None