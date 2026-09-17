#!/usr/bin/env python3
"""Withhold unverified research counts, not the independently published bibliography.

The release notice is server-rendered, including with JavaScript disabled. Keep
removing the statistics renderer in this failure branch: an empty fallback file
must not overwrite an unavailable publication with a misleading no-results state.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
WARNING = ('L’ultimo aggiornamento non ha prodotto statistiche pubblicabili. '
           'I conteggi delle ricerche non sono mostrati, per evitare di presentare dati non verificati.')
IMPACT = ('Questo non significa che non siano stati trovati paper o che le ricerche siano ferme. '
          'L’avviso riguarda soltanto i conteggi delle ricerche bibliografiche; '
          'bibliometria e analisi dei paper hanno controlli separati.')


def replace_text(content: str, element_id: str, text: str, *, required: bool = False) -> str:
    pattern = rf'(<(?P<tag>p|h3|span)\b[^>]*\bid="{re.escape(element_id)}"[^>]*>).*?(</(?P=tag)>)'
    content, matches = re.subn(pattern, lambda m: m[1] + escape(text) + m[3], content, flags=re.S)
    if matches > 1 or (required and matches != 1):
        raise ValueError('Statistics warning target missing or duplicated')
    return content


def mark_unavailable(page: Path, statistics: Path, *, as_of: datetime | None = None) -> None:
    payload = json.loads(statistics.read_text(encoding='utf-8'))
    if payload.get('dataThrough') is not None or payload.get('daily') or payload.get('extraRuns') or payload.get('calendar'):
        raise ValueError('Only the empty deterministic statistics baseline may be marked unavailable')
    if payload['summary']['allTime']['newCandidates'] is not None:
        raise ValueError('Unavailable candidate counts must remain null')
    # The canonical JSON is never rewritten. No counts or ledger entries are repaired here.
    content = replace_text(page.read_text(encoding='utf-8'), 'latest-execution', WARNING, required=True)
    content = replace_text(content, 'statistics-notice-title', 'Statistiche delle ricerche non disponibili')
    content = replace_text(content, 'statistics-notice-impact', IMPACT)
    content = replace_text(content, 'research-statistics-state', '· Dati non disponibili')
    stamp = as_of or datetime.now(timezone.utc)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError('Statistics notice time must be timezone-aware')
    detail = ('Avviso aggiornato il ' + stamp.astimezone(ZoneInfo('Europe/Rome')).strftime('%d/%m/%Y alle %H:%M') +
              ' (ora di Roma). È necessaria una verifica della pubblicazione; cambiare i filtri o ricaricare questa versione non corregge il problema.')
    content = replace_text(content, 'run-status', detail)
    content = re.sub(r'(<p\b[^>]*\bid="run-status"[^>]*?)\s+hidden(?=[\s>])', r'\1', content)
    content = re.sub(r'(<div\b[^>]*\bid="statistics-notice"[^>]*\bdata-state=")[^"]*(")', r'\1unavailable\2', content)
    # Hide the affected indicators in static HTML too, rather than displaying five dashes.
    content = re.sub(r'(<section\b[^>]*\bid="research-kpis"[^>]*)(>)',
                     lambda m: m[1] + ('' if re.search(r'\bhidden\b', m[1]) else ' hidden') + m[2], content)
    content = re.sub(r'<script\b[^>]*\bsrc=["\'](?:\./)?stats\.js(?:\?[^"\']*)?["\'][^>]*>\s*</script>', '', content)
    # No unbounded retries or fake repair button for a release-time validation failure.
    content = re.sub(r'(<button\b[^>]*\bid="statistics-retry"[^>]*)(>)',
                     lambda m: m[1] + ('' if re.search(r'\bhidden\b', m[1]) else ' hidden') + m[2], content)
    content = re.sub(r'<noscript><p>Per visualizzare i conteggi e i grafici è necessario JavaScript\.</p></noscript>', '', content)
    page.write_text(content, encoding='utf-8')


if __name__ == '__main__':
    mark_unavailable(ROOT / 'site/stats.html', ROOT / 'site/data/research-stats.json')
