"""Persist repository issue/comment input through the fixed private archive writer.

No source bodies, usernames or credentials are printed or uploaded as artifacts.
The workflow uses trusted main code and a read-only GitHub token.
"""
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from urllib.request import Request, build_opener, HTTPRedirectHandler

from scripts.enrichment.service_client import call, current_commit

REPOSITORY = 'colazeta/criminal_infiltration_in_legal_economy_review'
API = 'https://api.github.com/repos/' + REPOSITORY
VERSION = 'CILE-ANNOTATION-ARCHIVE-1'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError('github_ingress_redirect_refused')


def request(path):
    if not path.startswith('/issues'):
        raise RuntimeError('github_ingress_route_refused')
    token = os.environ.get('GH_TOKEN', '')
    if not token:
        raise RuntimeError('github_ingress_credential_missing')
    req = Request(API + path, headers={'Accept': 'application/vnd.github+json',
                  'Authorization': 'Bearer ' + token, 'User-Agent': 'cile-archive-ingress/1'})
    with build_opener(NoRedirect()).open(req, timeout=30) as response:
        data = response.read(12000001)
    if len(data) > 12000000:
        raise RuntimeError('github_ingress_response_limit')
    return json.loads(data)


def pages(path):
    records, seen = [], set()
    for page in range(1, 201):
        data = request(path + ('&' if '?' in path else '?') + f'per_page=100&page={page}')
        if not isinstance(data, list) or len(data) > 100:
            raise RuntimeError('github_ingress_page_invalid')
        for row in data:
            if type(row.get('id')) is not int or row['id'] in seen:
                raise RuntimeError('github_ingress_population_changed')
            seen.add(row['id']); records.append(row)
        if len(data) < 100:
            return records
    raise RuntimeError('github_ingress_population_limit')


def entity(row, issue=False):
    out = {key: row[key] for key in ['id', 'body', 'created_at', 'updated_at', 'html_url']}
    out['actor'] = (row.get('user') or {}).get('login')
    if issue:
        out.update(number=row['number'], is_pull_request='pull_request' in row)
    return out


def fingerprint(items):
    return hashlib.sha256(json.dumps(items, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def population():
    issues = {row['number']: entity(row, True) for row in pages('/issues?state=all&sort=created&direction=asc')}
    comments = []
    for row in pages('/issues/comments?sort=created&direction=asc'):
        match = re.fullmatch(re.escape(API) + r'/issues/(\d+)', row['issue_url'])
        if not match or int(match[1]) not in issues:
            raise RuntimeError('github_ingress_parent_missing')
        comments.append({'action': 'observe', 'issue': issues[int(match[1])], 'comment': entity(row)})
    return comments


def validate_receipt(receipt):
    allowed = {'contract', 'captured', 'annotation', 'snapshot_id', 'annotation_id',
               'binding_state', 'replayed', 'visibility'}
    if (not isinstance(receipt, dict) or set(receipt) - allowed
            or receipt.get('contract') != VERSION or receipt.get('captured') is not True
            or type(receipt.get('annotation')) is not bool):
        raise RuntimeError('annotation_ingest_receipt_invalid')
    if receipt['annotation'] and (receipt.get('binding_state') not in
            {'candidate_bound', 'unresolved', 'conflict', 'unregistered'}
            or not re.fullmatch('[a-f0-9]{64}', receipt.get('annotation_id', ''))
            or type(receipt.get('replayed')) is not bool):
        raise RuntimeError('annotation_ingest_receipt_invalid')
    return receipt


def ingest(items, commit):
    counts = dict(inputs=0, annotations=0, new_annotations=0, replayed=0,
                  candidate_bound=0, unresolved=0, conflict=0, unregistered=0)
    for offset in range(0, len(items), 25):
        batch = items[offset:offset + 25]
        result = call('archive-annotation-batch', expected_commit=commit, ingress=batch)
        if (set(result) != {'contract', 'receipts'} or result['contract'] != VERSION
                or not isinstance(result['receipts'], list) or len(result['receipts']) != len(batch)):
            raise RuntimeError('annotation_batch_receipt_invalid')
        for value in result['receipts']:
            receipt = validate_receipt(value)
            counts['inputs'] += 1
            if receipt['annotation']:
                counts['annotations'] += 1
                counts['replayed' if receipt['replayed'] else 'new_annotations'] += 1
                counts[receipt['binding_state']] += 1
    return counts


def run():
    commit = current_commit()
    if not re.fullmatch('[a-f0-9]{40}', commit):
        raise RuntimeError('annotation_ingress_invalid_deployment')
    if os.environ.get('GITHUB_EVENT_NAME') == 'issue_comment':
        event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
        if event['repository']['full_name'] != REPOSITORY:
            raise RuntimeError('annotation_ingress_wrong_repository')
        action = 'withdraw' if event['action'] == 'deleted' else 'observe'
        items = [{'action': action, 'issue': entity(event['issue'], True), 'comment': entity(event['comment'])}]
    else:
        observed_before = datetime.now(timezone.utc).isoformat()
        items = population()
        # A mutable paginated response is not a consistent full-population capture.
        if fingerprint(items) != fingerprint(population()):
            raise RuntimeError('github_ingress_population_changed')
    first = ingest(items, commit)
    replay = ingest(items, commit)
    if replay['new_annotations']:
        raise RuntimeError('annotation_ingress_replay_failed')
    census = None
    if os.environ.get('GITHUB_EVENT_NAME') != 'issue_comment':
        # Recheck the upstream set immediately before retiring an absent comment.
        if fingerprint(items) != fingerprint(population()):
            raise RuntimeError('github_ingress_population_changed')
        value = dict(comment_ids=[item['comment']['id'] for item in items], source_sha256=fingerprint(items), observed_before=observed_before)
        census = call('annotation-census', expected_commit=commit, ingress=value)
        repeated = call('annotation-census', expected_commit=commit, ingress=value)
        keys = {'contract', 'observed_comments', 'withdrawn', 'deferred', 'source_sha256', 'history_deleted'}
        for receipt in [census, repeated]:
            if (set(receipt) != keys or receipt['contract'] != VERSION
                    or receipt['observed_comments'] != len(items)
                    or receipt['source_sha256'] != value['source_sha256']
                    or receipt['history_deleted'] is not False
                    or any(type(receipt[k]) is not int or receipt[k] < 0 for k in ['withdrawn', 'deferred'])):
                raise RuntimeError('annotation_census_receipt_invalid')
        if repeated['withdrawn'] != 0:
            raise RuntimeError('annotation_census_replay_failed')
    audit = call('annotation-audit', expected_commit=commit)
    if (set(audit) != {'snapshots', 'annotations', 'binding_states', 'integrity_verified'}
            or audit['integrity_verified'] is not True
            or set(audit['binding_states']) != {'candidate_bound', 'unresolved', 'conflict', 'unregistered'}
            or any(type(v) is not int or v < 0 for v in audit['binding_states'].values())):
        raise RuntimeError('annotation_ingress_audit_invalid')
    return dict(contract=VERSION, commit=commit, input_sha256=fingerprint(items),
                source_population=len(items), migration=first, replay=replay, census=census, audit=audit,
                idempotency_verified=True, scientific_decisions_changed=False,
                private_content_exported=False, full_architecture_cutover_complete=False)


if __name__ == '__main__':
    try:
        print(json.dumps(run(), indent=2))
    except Exception:
        raise SystemExit('annotation_ingress_gate_failed') from None
