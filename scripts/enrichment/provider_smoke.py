#!/usr/bin/env python3
"""Bounded live-provider preflight on two existing candidates; never retain text.

This is connectivity/identity testing, not scientific extraction or calibration.
No D1/R2/registry write, key or paid provider is used. Only aggregate observations
are printed; full provider responses and abstracts remain transient in memory.
"""
import json
import re
import unicodedata
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]


def normal_title(value):
    value = ''.join(c for c in unicodedata.normalize('NFKD', str(value)) if not unicodedata.combining(c)).lower()
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in value).split())


def fetch(url):
    req = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'CILE-ENRICH-1 bounded preflight'})
    with urlopen(req, timeout=12) as response:
        raw = response.read(3_000_001)
    if len(raw) > 3_000_000:
        raise ValueError('response_limit')
    return json.loads(raw)


def main():
    records = json.loads((ROOT / 'site/data/paper-register.json').read_text())['records']
    selected = [r for r in records if re.fullmatch(r'10\.\d{4,9}/\S+', r.get('doi', ''))][:2]
    observations = []
    for record in selected:
        doi = record['doi'].lower()
        for provider in ('Crossref', 'OpenAlex'):
            item = {'candidate_id': record['id'], 'provider': provider}
            try:
                if provider == 'Crossref':
                    data = fetch('https://api.crossref.org/works/' + quote(doi, safe=''))['message']
                    matched = data.get('DOI', '').lower() == doi and normal_title(data.get('title', [''])[0]) == normal_title(record['title'])
                    item.update(status='identity_matched' if matched else 'identity_conflict', abstract_returned=isinstance(data.get('abstract'), str) and bool(data['abstract'].strip()))
                else:
                    data = fetch('https://api.openalex.org/works/https://doi.org/' + quote(doi, safe='') + '?select=id,doi,title,referenced_works,cited_by_count')
                    matched = data.get('doi', '').lower() == 'https://doi.org/' + doi and normal_title(data.get('title')) == normal_title(record['title'])
                    item.update(status='identity_matched' if matched else 'identity_conflict', outgoing_identifiers=len(data.get('referenced_works', [])))
            except HTTPError as error:
                item.update(status='provider_blocked', http_status=error.code)
            except (URLError, TimeoutError, ValueError, KeyError, TypeError):
                item.update(status='request_or_contract_failed')
            observations.append(item)
    print(json.dumps({'purpose': 'transient_connectivity_and_identity_only', 'scientific_calibration': False, 'persisted_source_texts': 0, 'observations': observations}, indent=2))


if __name__ == '__main__':
    main()
