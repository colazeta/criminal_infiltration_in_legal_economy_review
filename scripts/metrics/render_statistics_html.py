"""Render published run dates without exposing failed or partial attempts."""
from datetime import datetime
from html import escape
import re
from zoneinfo import ZoneInfo


def render_statistics_page(path, payload):
    rows = [row for row in payload.get('daily', []) if row.get('status') == 'completed']
    extras = [row for row in payload.get('extraRuns', []) if row.get('status') == 'completed']
    parts = []
    if rows:
        last = max(rows, key=lambda row: row['date'])
        parts.append('Ultima giornata ordinaria pubblicata: ' + datetime.fromisoformat(last['date']).strftime('%d/%m/%Y') + '.')
    if extras:
        last = max(extras, key=lambda row: datetime.fromisoformat(row['finishedAt'].replace('Z', '+00:00')))
        when = datetime.fromisoformat(last['startedAt'].replace('Z', '+00:00')).astimezone(ZoneInfo('Europe/Rome')).strftime('%d/%m/%Y %H:%M')
        parts.append(f'Ultima ricerca straordinaria pubblicata: {when} (ora di Roma).')
    text = ' '.join(parts) if parts else 'Nessuna esecuzione completata è pubblicabile in questa versione. Questo non dimostra che non siano state svolte ricerche o trovati paper.'
    content, count = re.subn(r'(<p id="latest-execution"[^>]*>).*?(</p>)',
                            lambda m: m[1] + escape(text) + m[2], path.read_text(encoding='utf-8'), flags=re.S)
    if count != 1:
        raise ValueError('Statistics summary target missing or duplicated')
    title = 'Risultati pubblicati · caricamento dei grafici' if parts else 'Nessuna esecuzione pubblicabile in questa versione'
    content = re.sub(r'(<h3 id="statistics-notice-title"[^>]*>).*?(</h3>)', lambda m: m[1] + title + m[2], content, flags=re.S)
    badge = '· Risultati pubblicati' if parts else '· Nessuna esecuzione pubblicabile'
    content = re.sub(r'(<span id="research-statistics-state"[^>]*>).*?(</span>)', lambda m: m[1] + badge + m[2], content, flags=re.S)
    path.write_text(content, encoding='utf-8')
