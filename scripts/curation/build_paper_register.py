"""Owner-authorised bibliographic projection of the existing candidate register.

No copied abstracts, reviewer identities, internal reasons or eligibility inference.
"""
import csv
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

FIELDS = {'id', 'title', 'authors', 'year', 'venue', 'doi', 'sourceLinks',
          'metadataStatus', 'reviewStatus', 'accessStatus', 'registeredAt', 'topicCode'}
CANDIDATE_ID = re.compile(r'^CAND-[A-Za-z0-9-]{1,100}$')


def validate_enrichment_registry(payload):
    """Mirror the deployed enrichment worker's public-registry boundary.

    The worker consumes this same public projection. Reject incompatible records
    before publication so an otherwise-green archive cannot strand hour-40
    delivery with ``invalid_registry_record``.
    """
    if payload.get('schemaVersion') != 1 or not isinstance(payload.get('records'), list) or len(payload['records']) > 10000:
        raise ValueError('Invalid enrichment registry envelope')
    seen = set()
    for record in payload['records']:
        candidate_id = record.get('id', '')
        title = record.get('title')
        links = record.get('sourceLinks')
        if (not CANDIDATE_ID.fullmatch(candidate_id) or candidate_id in seen
                or not isinstance(title, str) or not title or len(title) > 3000
                or not isinstance(record.get('doi'), str)
                or not isinstance(links, list)):
            raise ValueError(f'{candidate_id or "<missing>"}: invalid enrichment registry record')
        seen.add(candidate_id)
        for url in links:
            if not isinstance(url, str) or len(url) > 2000:
                raise ValueError(f'{candidate_id}: invalid enrichment registry source URL')
            parsed = urlsplit(url)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError(f'{candidate_id}: enrichment registry sources must be credential-free HTTPS')
    return payload


def build_payload(root):
    root=Path(root)
    with (root/'data/curation/review_queue.csv').open(newline='',encoding='utf-8-sig') as handle:
        queue=list(csv.DictReader(handle))
    records=[]
    for row in queue:
        links=[]
        for value in row['source_links'].split(';'):
            value=value.strip(); parsed=urlsplit(value)
            if value and parsed.scheme in ('https','http') and parsed.hostname and not parsed.username and not parsed.password:
                links.append(value)
        records.append(dict(id=row['candidate_id'],title=row['title'],authors=row['authors'],
            year=int(row['year']) if row['year'] else None,venue=row['venue'],doi=row['doi'],
            sourceLinks=links,metadataStatus=row['verification_status'],reviewStatus=row['current_status'],
            accessStatus='unknown',registeredAt=row['materialised_at'],topicCode=row['topic_code']))
    # Access assertions retain their specific meaning: discovery alone never verifies OA.
    by_id={r['id']:r for r in records}
    for path in sorted((root/'data/curation/intake_access').glob('*.json')):
        snapshot=json.loads(path.read_text())
        for receipt in snapshot['receipts']:
            if receipt['candidate_id'] in by_id:
                by_id[receipt['candidate_id']]['accessStatus']=receipt['access_status']
    records.sort(key=lambda r:r['id'])
    if len(by_id)!=len(records) or any(set(r)!=FIELDS for r in records):
        raise ValueError('Invalid public register identity or fields')
    return validate_enrichment_registry({'schemaVersion':1,'records':records})


def render_source_link(url, number):
    """Keep original locators but make only credential-free HTTPS clickable.

    Do not silently rewrite HTTP to HTTPS: that would invent a verified locator.
    Legacy HTTP provenance remains visible as escaped, non-interactive text when
    rendering an explicitly supplied legacy locator. The governed registry build
    itself rejects HTTP because the deployed enrichment worker consumes it.
    """
    from html import escape
    parsed = urlsplit(url)
    if parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password:
        return '<a rel="noreferrer" href="' + escape(url, quote=True) + '">Fonte ' + str(number) + '</a>'
    if parsed.scheme == 'http' and parsed.hostname and not parsed.username and not parsed.password:
        return '<span>Fonte ' + str(number) + ' (indirizzo originale HTTP): ' + escape(url) + '</span>'
    raise ValueError('Unsafe public source locator')


def render_page(path,payload):
    from html import escape
    import re
    rows=[]
    for r in payload['records']:
        citation=escape(r['title'])+'<p>'+escape(' · '.join(str(v) for v in (r['authors'],r['year'],r['venue']) if v))+'</p>'
        review='Da analizzare' if r['reviewStatus']=='pending' else r['reviewStatus']
        if r.get('topicCode'): review += ' · '+r['topicCode']
        access='OA verificato all’acquisizione' if r['accessStatus']=='verified_open' else 'Accesso da verificare'
        links=' · '.join(render_source_link(url,i+1) for i,url in enumerate(r['sourceLinks']))
        rows.append('<tr><td>'+citation+'</td><td>'+escape(review)+'</td><td>'+escape(access)+'</td><td>'+links+' · <a href="./curate.html">Analizza nel curatore</a></td></tr>')
    content=path.read_text()
    for pattern,replacement in [(r'(<tbody id="registered-papers">).*?(</tbody>)',''.join(rows)),
            (r'(<p id="register-count"[^>]*>).*?(</p>)',str(len(rows))+' record registrati · analisi individuale e accesso verificati separatamente.')]:
        content,n=re.subn(pattern,lambda m:m[1]+replacement+m[2],content,flags=re.S)
        if n!=1:raise ValueError('Register render target missing or duplicated')
    path.write_text(content)

if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    render_page(root/'site/index.html',build_payload(root))
