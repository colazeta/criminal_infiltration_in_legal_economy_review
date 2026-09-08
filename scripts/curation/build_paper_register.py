"""Owner-authorised bibliographic projection of the existing candidate register.

No copied abstracts, reviewer identities, internal reasons or eligibility inference.
"""
import csv
import json
from pathlib import Path
from urllib.parse import urlsplit

FIELDS = {'id', 'title', 'authors', 'year', 'venue', 'doi', 'sourceLinks',
          'metadataStatus', 'reviewStatus', 'accessStatus', 'registeredAt'}

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
            accessStatus='unknown',registeredAt=row['materialised_at']))
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
    return {'schemaVersion':1,'records':records}


def render_page(path,payload):
    from html import escape
    import re
    rows=[]
    for r in payload['records']:
        citation=escape(r['title'])+'<p>'+escape(' · '.join(str(v) for v in (r['authors'],r['year'],r['venue']) if v))+'</p>'
        review='Da analizzare' if r['reviewStatus']=='pending' else r['reviewStatus']
        access='OA verificato all’acquisizione' if r['accessStatus']=='verified_open' else 'Accesso da verificare'
        links=' · '.join('<a rel="noreferrer" href="'+escape(url,quote=True)+'">Fonte '+str(i+1)+'</a>' for i,url in enumerate(r['sourceLinks']))
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
