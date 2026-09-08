"""Render aggregate run evidence into HTML, without relying on a second fetch."""
from datetime import datetime
from html import escape
import re
from zoneinfo import ZoneInfo

def render_statistics_page(path,payload):
    rows=payload.get('extraRuns',[])
    if rows:
        last=max(rows,key=lambda r:r['finishedAt'])
        count=lambda v:'non misurato' if v is None else str(v)
        text=(f"Ultima esecuzione straordinaria: {datetime.fromisoformat(last['startedAt']).astimezone(ZoneInfo('Europe/Rome')).strftime('%d/%m/%Y %H:%M')} Europe/Rome. "
              f"Query: {last['queriesCompleted']}/{last['queriesPlanned']}. Occorrenze: {count(last['occurrencesReturned'])}. "
              f"Risultati: {count(last['uniqueResults'])}. Candidati inviati alla coda: {count(last['intakeCandidates'])}. Stato: {last['status']}.")
    else:
        text='Nessuna esecuzione straordinaria registrata. Le giornate programmate sono riportate separatamente.'
    content=path.read_text()
    content,n=re.subn(r'(<p id="latest-execution"[^>]*>).*?(</p>)',lambda m:m[1]+escape(text)+m[2],content,flags=re.S)
    if n!=1:raise ValueError('Statistics summary target missing or duplicated')
    path.write_text(content)
