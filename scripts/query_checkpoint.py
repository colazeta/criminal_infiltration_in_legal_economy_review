#!/usr/bin/env python3
"""Immutable query-observation checkpoints, separate from intake and metrics terminals.

Render locally, append to the configured operational issue, read back before the next
query. Existing connector actions may perform the same append/read. No checkpoint
can supply a missing terminal, eligibility decision or publication receipt.
"""
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl, unquote
from urllib.request import Request, build_opener, HTTPRedirectHandler
from scripts.surveillance_identity import BATCH_PATTERN
ROOT=Path(__file__).resolve().parents[1]
ISSUE=696
REPOSITORY='colazeta/criminal_infiltration_in_legal_economy_review'
MARKER='<!-- cile-query-checkpoint:1 -->'
FIELDS={'protocol','cycle_id','batch_id','provider','query_id','attempt','query','observed_at','query_status','occurrences','limitation'}
ROW={'rank','url','title','doi','year'}

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        raise RuntimeError('checkpoint_redirect_refused')

_HTTP = build_opener(NoRedirect())

def canonical(data):return json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))

def validate(data,now=None):
    if not isinstance(data,dict) or set(data)!=FIELDS or data['protocol']!='CILE-QUERY-CHECKPOINT-1':raise ValueError('checkpoint_schema')
    if not re.fullmatch(BATCH_PATTERN,str(data['batch_id'])):raise ValueError('checkpoint_batch')
    if data['provider'] not in {'Exa','Parallel Search'}:raise ValueError('checkpoint_provider')
    prefix='EXA' if data['provider']=='Exa' else 'PARALLEL'
    if not re.fullmatch(prefix+r'-W[1-7]-Q[1-9][0-9]*',str(data['query_id'])):raise ValueError('checkpoint_query_identity')
    if type(data['attempt']) is not int or not 1<=data['attempt']<=100:raise ValueError('checkpoint_attempt')
    if not isinstance(data['cycle_id'],str) or not data['cycle_id'] or len(data['cycle_id'])>100:raise ValueError('checkpoint_cycle')
    for k,n in [('query',3000),('limitation',1000)]:
        if not isinstance(data[k],str) or len(data[k])>n or (k=='query' and not data[k].strip()):raise ValueError('checkpoint_text')
    when=datetime.fromisoformat(data['observed_at'].replace('Z','+00:00'))
    if when.tzinfo is None or when>(now or datetime.now(timezone.utc))+timedelta(minutes=5):raise ValueError('checkpoint_observation_time')
    if data['query_status'] not in {'completed','partial','failed'}:raise ValueError('checkpoint_status')
    if data['query_status']!='completed' and not data['limitation'].strip():raise ValueError('checkpoint_failure_reason')
    if not isinstance(data['occurrences'],list) or len(data['occurrences'])>1000:raise ValueError('checkpoint_size')
    ranks=set()
    for row in data['occurrences']:
        if not isinstance(row,dict) or set(row)!=ROW:raise ValueError('checkpoint_occurrence_schema')
        if type(row['rank']) is not int or row['rank']<1 or row['rank'] in ranks:raise ValueError('checkpoint_rank')
        ranks.add(row['rank'])
        u=urlsplit(row['url'])
        if u.scheme!='https' or not u.hostname or u.username or u.password or len(row['url'])>2000:raise ValueError('checkpoint_source_url')
        if any(re.search(r'token|secret|signature|session|api.?key|authorization|^sig$|^key$|x-amz|x-goog',k,re.I) for k in [unquote(key) for key,_ in parse_qsl(u.query,keep_blank_values=True)]):raise ValueError('checkpoint_private_locator')
        if not isinstance(row['title'],str) or not row['title'].strip() or len(row['title'])>2000:raise ValueError('checkpoint_title')
        if row['doi'] is not None and (not isinstance(row['doi'],str) or len(row['doi'])>500):raise ValueError('checkpoint_doi')
        if row['year'] is not None and (type(row['year']) is not int or not 1000<=row['year']<=when.year+1):raise ValueError('checkpoint_year')
    if re.search(r'Bearer\s+|gh[pousr]_|sk-proj-|-----BEGIN .*PRIVATE KEY',canonical(data)):raise ValueError('checkpoint_private_material')
    return data

def identity(data):return hashlib.sha256(canonical([data[k] for k in ['cycle_id','batch_id','provider','query_id','attempt']]).encode()).hexdigest()

def render_parts(data):
    validate(data)
    # Multipart prevents one long enumerable query exceeding GitHub's comment limit.
    encoded=canonical(data);digest=hashlib.sha256(encoded.encode()).hexdigest();chunks=[encoded[i:i+20000] for i in range(0,len(encoded),20000)]
    return [MARKER+'\n```json\n'+json.dumps({'checkpoint_id':identity(data),'sha256':digest,'part':i+1,'parts':len(chunks),'content':chunk},ensure_ascii=False)+'\n```' for i,chunk in enumerate(chunks)]

def collect(comments):
    bundles={}
    for comment in comments:
        body=comment.get('body','')
        if not body.startswith(MARKER):continue
        if comment.get('user',{}).get('login') not in {'colazeta','github-actions[bot]'}:raise ValueError('checkpoint_author')
        m=re.fullmatch(re.escape(MARKER)+r'\n```json\n(.*)\n```\s*',body,re.S)
        if not m:raise ValueError('checkpoint_envelope')
        value=json.loads(m.group(1));keys={'checkpoint_id','sha256','part','parts','content'}
        if set(value)!=keys or not re.fullmatch(r'[a-f0-9]{64}',value['checkpoint_id']) or not re.fullmatch(r'[a-f0-9]{64}',value['sha256']) or not 1<=value['part']<=value['parts']<=200:raise ValueError('checkpoint_envelope')
        key=value['checkpoint_id'];old=bundles.setdefault(key,{'sha256':value['sha256'],'parts':value['parts'],'chunks':{}})
        if old['sha256']!=value['sha256'] or old['parts']!=value['parts']:raise ValueError('checkpoint_conflict')
        part=value['part']
        if part in old['chunks'] and old['chunks'][part]!=value['content']:raise ValueError('checkpoint_conflict')
        old['chunks'][part]=value['content']
    complete={};partial=[]
    for key,b in bundles.items():
        if len(b['chunks'])<b['parts']:partial.append(key);continue
        encoded=''.join(b['chunks'][i] for i in range(1,b['parts']+1))
        if hashlib.sha256(encoded.encode()).hexdigest()!=b['sha256']:raise ValueError('checkpoint_hash')
        data=validate(json.loads(encoded))
        if identity(data)!=key:raise ValueError('checkpoint_identity')
        complete[key]=data
    return {'complete_checkpoints':complete,'incomplete_checkpoints':partial}

def request(method,path,payload=None):
    token=os.environ.get('GITHUB_TOKEN','')
    if not token:raise RuntimeError('checkpoint_github_authentication_required')
    req=Request('https://api.github.com/repos/'+REPOSITORY+path,method=method,data=None if payload is None else json.dumps(payload).encode(),headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Content-Type':'application/json','User-Agent':'cile-query-checkpoint/1'})
    with _HTTP.open(req,timeout=20) as response:return json.load(response)

def read_comments():
    result=[]
    for page in range(1,1001):
        part=request('GET',f'/issues/{ISSUE}/comments?per_page=100&page={page}');result.extend(part)
        if len(part)<100:return result
    raise RuntimeError('checkpoint_pagination_incomplete')

def publish(data):
    parts=render_parts(data);comments=read_comments();state=collect(comments);key=identity(data)
    if key in state['complete_checkpoints']:
        if canonical(state['complete_checkpoints'][key])!=canonical(data):raise ValueError('checkpoint_conflict')
        return {'checkpoint_id':key,'replayed':True,'readback_verified':True}
    existing={c['body'] for c in comments}
    for body in parts:
        if body in existing:continue
        try:request('POST',f'/issues/{ISSUE}/comments',{'body':body})
        except Exception:
            # Ambiguous POST is resolved by exact readback, never blind retry.
            if body not in {c['body'] for c in read_comments()}:raise RuntimeError('checkpoint_write_unverified') from None
    reread=collect(read_comments())
    if canonical(reread['complete_checkpoints'].get(key))!=canonical(data):raise RuntimeError('checkpoint_write_unverified')
    return {'checkpoint_id':key,'replayed':False,'readback_verified':True}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('--publish',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args();data=json.loads(a.input.read_text())
    result=publish(data) if a.publish else {'issue':ISSUE,'comments':render_parts(data),'persisted':False}
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output:a.output.write_text(text)
    else:print(text)

if __name__=='__main__':main()
