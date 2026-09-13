#!/usr/bin/env python3
"""Deterministic, public-safe reading support; never scientific approval.

The candidate register keeps its existing closed worker contract. This separate
release artifact contains only allowlisted paraphrases, locators and assessment
metadata. Reviewer notes, evidence quotations and original text are not copied.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
BIBLIOGRAPHY = ('title', 'authors', 'year', 'venue', 'doi')
KINDS = {'verified_abstract_source', 'publisher_summary', 'full_text_intro',
         'review_synopsis', 'metadata_warning'}
FIELDS = {'id', 'bibliography', 'readingAid', 'abstract', 'retrieval', 'access'}
AID_FIELDS = {'kind', 'sourceLabel', 'sourceUrl', 'synopsis', 'checkedAt'}
ABSTRACT_FIELDS = {'status', 'source', 'sourceUrl', 'checkedAt'}
RETRIEVAL_FIELDS = {'status', 'bestUrl', 'fullTextUrl', 'openAccessUrl',
                    'landingUrl', 'doiUrl', 'resolvedDoi', 'matchMethod',
                    'matchConfidence', 'checkedAt'}
ACCESS_FIELDS = {'status', 'kind', 'url', 'source', 'checkedAt'}


def text(value, limit=600):
    if value is None:
        return ''
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError('Invalid or overlong public support value')
    return value.strip()


def safe_url(value):
    value = text(value, 2000)
    if not value:
        return ''
    try:
        parsed = urlsplit(value)
        if (parsed.scheme == 'https' and parsed.hostname
                and not parsed.username and not parsed.password
                and not any(ord(c) < 32 for c in value)):
            return value
    except ValueError:
        pass
    # Preserve originals in their governed ledger, never rewrite an HTTP URL.
    return ''


def index(rows, key):
    result = {}
    for row in rows:
        cid = row.get(key)
        if not isinstance(cid, str) or not cid or cid in result:
            raise ValueError('Missing or duplicate support candidate identity')
        result[cid] = row
    return result


def csv_index(path):
    if not path.exists():
        return {}
    with path.open(newline='', encoding='utf-8-sig') as handle:
        return index(list(csv.DictReader(handle)), 'candidate_id')


def aid_index(path):
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding='utf-8'))
    if payload.get('schemaVersion') != 1 or not isinstance(payload.get('records'), list):
        raise ValueError('Invalid reading-support source envelope')
    return index(payload['records'], 'candidateId')


def build_payload(root=ROOT, register=None):
    root = Path(root)
    if register is None:
        from scripts.curation.build_paper_register import build_payload as build_register
        register = build_register(root)
    registered = index(register['records'], 'id')
    curation = root / 'data/curation'
    aids = aid_index(curation / 'reading_aids.json')
    aids.update(aid_index(curation / 'reading_aid_overrides.json'))
    abstracts = csv_index(curation / 'abstract_coverage.csv')
    retrieval = csv_index(curation / 'retrieval_coverage.csv')
    access = csv_index(curation / 'access_coverage.csv')
    records = []
    for cid, bibliography in sorted(registered.items()):
        record = dict(id=cid, bibliography={k: bibliography.get(k) for k in BIBLIOGRAPHY},
                      readingAid=None, abstract=None, retrieval=None, access=None)
        aid = aids.get(cid)
        if aid and aid.get('kind') in KINDS:
            record['readingAid'] = dict(
                kind=aid['kind'], sourceLabel=text(aid.get('sourceLabel')),
                sourceUrl=safe_url(aid.get('sourceUrl')),
                synopsis=text(aid.get('synopsis'), 4000),
                checkedAt=text(aid.get('checkedAt'), 64))
        row = abstracts.get(cid)
        if row:
            record['abstract'] = dict(status=text(row.get('coverage_status')),
                source=text(row.get('abstract_source')), sourceUrl=safe_url(row.get('article_url')),
                checkedAt=text(row.get('checked_at'), 64))
        row = retrieval.get(cid)
        if row:
            record['retrieval'] = dict(status=text(row.get('resolution_status')),
                bestUrl=safe_url(row.get('best_url')), fullTextUrl=safe_url(row.get('full_text_url')),
                openAccessUrl=safe_url(row.get('open_access_url')), landingUrl=safe_url(row.get('landing_url')),
                doiUrl=safe_url(row.get('doi_url')), resolvedDoi=text(row.get('resolved_doi')),
                matchMethod=text(row.get('match_method')), matchConfidence=text(row.get('match_confidence')),
                checkedAt=text(row.get('checked_at'), 64))
        row = access.get(cid)
        if row:
            record['access'] = dict(status=text(row.get('access_status')), kind=text(row.get('access_kind')),
                url=safe_url(row.get('access_url')), source=text(row.get('evidence_source')),
                checkedAt=text(row.get('checked_at'), 64))
        records.append(record)
    payload = {'schemaVersion': 1, 'records': records}
    validate_payload(payload)
    return payload


def validate_payload(payload):
    if not isinstance(payload, dict) or set(payload) != {'schemaVersion', 'records'} or payload['schemaVersion'] != 1:
        raise ValueError('Invalid public-support envelope')
    if not isinstance(payload['records'], list) or len(payload['records']) > 10000:
        raise ValueError('Invalid public-support record list')
    records = index(payload['records'], 'id')
    for record in records.values():
        if set(record) != FIELDS or set(record['bibliography']) != set(BIBLIOGRAPHY):
            raise ValueError('Public-support allowlist mismatch')
        for field, allowed in (('readingAid', AID_FIELDS), ('abstract', ABSTRACT_FIELDS),
                               ('retrieval', RETRIEVAL_FIELDS), ('access', ACCESS_FIELDS)):
            section = record[field]
            if section is None:
                continue
            if not isinstance(section, dict) or set(section) != allowed:
                raise ValueError('Public-support nested allowlist mismatch')
            for key, value in section.items():
                text(value, 4000 if key == 'synopsis' else 2000 if key.lower().endswith('url') else 600)
                if key.lower().endswith('url') and value and safe_url(value) != value:
                    raise ValueError('Unsafe public-support locator')
        if record['readingAid'] and record['readingAid']['kind'] not in KINDS:
            raise ValueError('Unsupported public reading-aid kind')
    return records


def write_payload(root=ROOT, register=None):
    payload = build_payload(root, register)
    output = Path(root) / 'site/paper-support.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return payload


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT))
    payload = write_payload()
    print(f"[OK] Public reading support: {len(payload['records'])} registered candidates")
