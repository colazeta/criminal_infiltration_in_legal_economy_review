"""Read aggregate Cloudflare storage usage; no object IDs, rows or logs exported."""
import datetime as dt
import json
import os
import re
from urllib.request import Request, build_opener, HTTPRedirectHandler
from scripts.review_v2.prepare_cloudflare import resolve_account


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError('quota_redirect_refused')


def query(text):
    token = os.environ.get('CLOUDFLARE_API_TOKEN', '')
    if not token:
        raise RuntimeError('quota_credential_unavailable')
    req = Request('https://api.cloudflare.com/client/v4/graphql',
                  data=json.dumps({'query': text}).encode(), method='POST',
                  headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    try:
        with build_opener(NoRedirect()).open(req, timeout=30) as response:
            raw = response.read(4000001)
        if len(raw) > 4000000:
            raise RuntimeError('quota_response_limit')
        value = json.loads(raw)
    except Exception:
        raise RuntimeError('quota_transport_unavailable') from None
    if value.get('errors'):
        # Error bodies may contain account identifiers; never return them.
        raise RuntimeError('quota_query_not_authorised_or_supported')
    return value['data']


_stage = 'initialise'

def fields(name):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,150}', name):
        raise RuntimeError('quota_schema_invalid')
    type_ref = 'kind name'
    for _ in range(7):
        type_ref = 'kind name ofType{' + type_ref + '}'
    value = query('{__type(name:' + json.dumps(name) + '){fields{name type{' + type_ref + '}}}}').get('__type')
    if not isinstance(value, dict) or not isinstance(value.get('fields'), list):
        raise RuntimeError('quota_schema_unavailable')
    return value['fields']


def named(field):
    value = field['type']
    for _ in range(8):
        if isinstance(value, dict) and value.get('name'):
            return value['name']
        value = value.get('ofType') if isinstance(value, dict) else None
    raise RuntimeError('quota_type_wrapper_unavailable')


def observe():
    global _stage
    _stage = 'account_resolution'
    account = resolve_account()
    if not re.fullmatch(r'[a-f0-9]{32}', account):
        raise RuntimeError('quota_account_unavailable')
    _stage = 'query_root'
    root = query('{__schema{queryType{name}}}')['__schema']['queryType']['name']
    def child(parent, name):
        found = next((f for f in fields(parent) if f['name'] == name), None)
        if not found:
            raise RuntimeError('quota_schema_unavailable')
        return named(found)
    _stage = 'account_type'
    account_type = child(child(root, 'viewer'), 'accounts')
    _stage = 'dataset_selection'
    available = fields(account_type)
    # Runtime introspection supplies case-sensitive names; do not guess Account.
    # SQL storage and legacy KV metrics are separate datasets when both exist.
    dataset = next((f for name in ['durableObjectsSqlStorageGroups', 'durableObjectsStorageGroups']
                    for f in available if f['name'] == name), None)
    if not dataset:
        raise RuntimeError('quota_dataset_unavailable')
    dataset_name = dataset['name']
    _stage = 'metric_selection'
    groups = fields(named(dataset))
    aggregate = next((f for f in groups if f['name'] == 'sum'), None)
    if not aggregate:
        raise RuntimeError('quota_metrics_unavailable')
    metrics = fields(named(aggregate))
    allowed = {'rowsRead', 'rowsWritten', 'sqlRowsRead', 'sqlRowsWritten', 'readUnits', 'writeUnits', 'deleteUnits'}
    selected = sorted(f['name'] for f in metrics if f['name'] in allowed)
    if not selected:
        raise RuntimeError('quota_metrics_unavailable')
    day = dt.datetime.now(dt.timezone.utc).date().isoformat()
    _stage = 'aggregate_read'
    data = query('{viewer{accounts(filter:{accountTag:' + json.dumps(account) + '}){' + dataset_name + '(limit:1,filter:{datetime_geq:' + json.dumps(day + 'T00:00:00Z') + '}){sum{' + ' '.join(selected) + '}}}}}')
    _stage = 'aggregate_validation'
    totals = data['viewer']['accounts'][0][dataset_name]
    if not totals:
        raise RuntimeError('quota_measurement_unavailable')
    values = totals[0]['sum']
    if set(values) != set(selected) or any(type(v) not in (int, float) or v < 0 for v in values.values()):
        raise RuntimeError('quota_measurement_invalid')
    return {'contract': 'CILE-STORAGE-USAGE-1', 'scope': 'account_aggregate', 'utc_day': day, 'dataset': dataset_name,
            'metrics': values, 'object_data_exported': False, 'billing_changed': False}


if __name__ == '__main__':
    try:
        print(json.dumps(observe(), sort_keys=True))
    except Exception as error:
        safe = {'quota_credential_unavailable', 'quota_account_unavailable', 'quota_transport_unavailable',
                'quota_query_not_authorised_or_supported', 'quota_metrics_unavailable', 'quota_measurement_unavailable',
                'quota_schema_unavailable', 'quota_dataset_unavailable'}
        category = str(error) if str(error) in safe else 'quota_diagnostic_unavailable'
        print(json.dumps({'diagnostic': category, 'stage': _stage, 'exception_type': type(error).__name__ if type(error).__name__ in {'RuntimeError','KeyError','IndexError','TypeError','StopIteration'} else 'other'}))
        raise SystemExit(1) from None
