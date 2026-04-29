#!/usr/bin/env python3
"""Run E0R1 identifier-first metadata discovery from OpenAlex and Crossref."""
import csv, json, os, re, urllib.parse, urllib.request
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'data/raw/e0_identifier_first_query_plan.csv'
RAW_DIR = ROOT / 'data/raw/e0_identifier_first_raw'
OUT = ROOT / 'data/raw/e0_verified_seed_candidates_rebuild.csv'
RAW_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_SCOPE = {'direct','contextual_strong','contextual_weak','outside_scope','unresolved'}


def norm_title(t):
    return re.sub(r'\W+',' ',(t or '').lower()).strip()

def fetch_json(url):
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.load(r)
    except Exception:
        return {}

def classify_scope(title, abstract):
    txt = f"{title} {abstract}".lower()
    oc = any(k in txt for k in ['mafia','organized crime','organised crime','criminal organization','criminal organisation'])
    legal = any(k in txt for k in ['legal economy','legitimate economy','firm','company','enterprise','market','procurement','ownership','laundering'])
    infil = any(k in txt for k in ['infiltration','control','collusion','corruption','capture','penetration'])
    if oc and legal and infil:
        return 'direct','core_seed'
    if (oc and legal) or ('money laundering' in txt and legal):
        return 'contextual_strong','contextual_seed'
    if oc or legal:
        return 'contextual_weak','candidate_seed'
    return 'outside_scope','reject'

queries = list(csv.DictReader(open(PLAN)))
raw_counts = {'openalex':0,'crossref':0,'semanticscholar':0}
records = []

for i,q in enumerate(queries, start=1):
    qid = q['query_id']
    qstr = q['query_string']

    oa_url = 'https://api.openalex.org/works?per-page=5&search=' + urllib.parse.quote(qstr)
    oa = fetch_json(oa_url)
    (RAW_DIR / f'openalex_{qid}.json').write_text(json.dumps(oa, ensure_ascii=False, indent=2))
    oa_res = oa.get('results', [])
    raw_counts['openalex'] += len(oa_res)
    for r in oa_res:
        title = r.get('display_name','')
        doi = (r.get('doi') or '').replace('https://doi.org/','') if r.get('doi') else ''
        authors = '; '.join(a.get('author',{}).get('display_name','') for a in r.get('authorships',[])[:6])
        year = r.get('publication_year') or ''
        venue = (r.get('host_venue',{}) or {}).get('display_name','')
        abstract = ''
        scope, seed_status = classify_scope(title, abstract)
        records.append({
            'source_query_id': qid,'title': title,'doi': doi,'authors': authors,'year': year,'venue': venue,
            'abstract': abstract,'openalex_id': r.get('id',''),'semantic_scholar_id':'','crossref_id':'','source':'OpenAlex',
            'metadata_confidence':'high' if (doi or r.get('id')) else 'low','scope_fit':scope,
            'proposed_seed_status': seed_status if scope!='outside_scope' else 'reject',
            'reason_for_inclusion':'Identifier-first retrieval from OpenAlex query plan.',
            'verification_notes':'Raw OpenAlex record saved.'
        })

    cr_url = 'https://api.crossref.org/works?rows=5&query=' + urllib.parse.quote(qstr)
    cr = fetch_json(cr_url)
    (RAW_DIR / f'crossref_{qid}.json').write_text(json.dumps(cr, ensure_ascii=False, indent=2))
    cr_res = cr.get('message',{}).get('items',[])
    raw_counts['crossref'] += len(cr_res)
    for r in cr_res:
        title = (r.get('title') or [''])[0]
        doi = r.get('DOI','')
        authors = '; '.join((a.get('family','') + ' ' + a.get('given','')).strip() for a in r.get('author',[])[:6])
        year = (r.get('issued',{}).get('date-parts',[[None]])[0][0] or '')
        venue = (r.get('container-title') or [''])[0]
        abstract = ''
        scope, seed_status = classify_scope(title, abstract)
        records.append({
            'source_query_id': qid,'title': title,'doi': doi,'authors': authors,'year': year,'venue': venue,
            'abstract': abstract,'openalex_id':'','semantic_scholar_id':'','crossref_id':r.get('DOI',''),'source':'Crossref',
            'metadata_confidence':'high' if doi else 'medium','scope_fit':scope,
            'proposed_seed_status': seed_status if scope!='outside_scope' else 'reject',
            'reason_for_inclusion':'Identifier-first retrieval from Crossref query plan.',
            'verification_notes':'Raw Crossref record saved.'
        })

# dedup
seen = set(); dedup=[]
for r in records:
    key = r['doi'] or r['openalex_id'] or (norm_title(r['title']) + '|' + str(r['year']))
    if not key or key in seen:
        continue
    seen.add(key)
    # reject insufficient identifiers unless stable book/report metadata
    has_id = bool(r['doi'] or r['openalex_id'] or r['semantic_scholar_id'])
    stable_book = bool(r['title'] and r['authors'] and r['year'] and r['venue'])
    if not has_id and not stable_book:
        r['proposed_seed_status'] = 'reject'
        r['scope_fit'] = 'unresolved'
        r['verification_notes'] += ' Rejected: insufficient identifiers.'
    dedup.append(r)

headers = ['candidate_id','source_query_id','title','doi','authors','year','venue','abstract','openalex_id','semantic_scholar_id','crossref_id','source','metadata_confidence','scope_fit','proposed_seed_status','reason_for_inclusion','verification_notes']
with open(OUT,'w',newline='') as f:
    w=csv.DictWriter(f, fieldnames=headers)
    w.writeheader()
    for i,r in enumerate(dedup,1):
        r['candidate_id']=f'E0R1-C{i:03d}'
        if r['scope_fit'] not in ALLOWED_SCOPE:
            r['scope_fit']='unresolved'
        w.writerow({k:r.get(k,'') for k in headers})

print(f"Saved {len(dedup)} deduplicated candidates. Raw counts: {raw_counts}")
