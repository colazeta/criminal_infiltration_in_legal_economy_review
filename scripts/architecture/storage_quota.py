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


def fields(name):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,150}', name):
        raise RuntimeError('quota_schema_invalid')
    return query('{__type(name:' + json.dumps(name) + '){fields{name type{kind name ofType{kind name ofType{kind name}}}}}}')['__type']['fields']


def named(field):
    value = field['type']
    while not value.get('name'):
        value = value['ofType']
    return value['name']


def observe():
    account = resolve_account()
    if not re.fullmatch(r'[a-f0-9]{32}', account):
        raise RuntimeError('quota_account_unavailable')
    dataset = next(f for f in fields('Account') if f['name'] == 'durableObjectsStorageGroups')
    groups = fields(named(dataset))
    metrics = fields(named(next(f for f in groups if f['name'] == 'sum')))
    allowed = {'rowsRead', 'rowsWritten', 'sqlRowsRead', 'sqlRowsWritten', 'readUnits', 'writeUnits', 'deleteUnits'}
    selected = sorted(f['name'] for f in metrics if f['name'] in allowed)
    if not selected:
        raise RuntimeError('quota_metrics_unavailable')
    day = dt.datetime.now(dt.timezone.utc).date().isoformat()
    data = query('{viewer{accounts(filter:{accountTag:' + json.dumps(account) + '}){durableObjectsStorageGroups(limit:1,filter:{datetime_geq:' + json.dumps(day + 'T00:00:00Z') + '}){sum{' + ' '.join(selected) + '}}}}}')
    totals = data['viewer']['accounts'][0]['durableObjectsStorageGroups']
    if not totals:
        raise RuntimeError('quota_measurement_unavailable')
    values = totals[0]['sum']
    if set(values) != set(selected) or any(type(v) not in (int, float) or v < 0 for v in values.values()):
        raise RuntimeError('quota_measurement_invalid')
    return {'contract': 'CILE-STORAGE-USAGE-1', 'scope': 'account_aggregate', 'utc_day': day,
            'metrics': values, 'object_data_exported': False, 'billing_changed': False}


if __name__ == '__main__':
    try:
        print(json.dumps(observe(), sort_keys=True))
    except Exception as error:
        safe = {'quota_credential_unavailable', 'quota_account_unavailable', 'quota_transport_unavailable',
                'quota_query_not_authorised_or_supported', 'quota_metrics_unavailable', 'quota_measurement_unavailable'}
        raise SystemExit(str(error) if str(error) in safe else 'quota_diagnostic_unavailable') from None
