#!/usr/bin/env python3
"""Withhold invalid aggregate telemetry without withholding validated bibliography.

Use only the existing empty baseline, never invalid counts or invented zeroes.
Withhold the statistics renderer for this release so the failure banner cannot
be overwritten by an apparent no-results message.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[2]
WARNING = ('Statistiche delle ricerche temporaneamente non disponibili: il registro '
           'delle esecuzioni non ha superato la validazione. Questo non indica zero '
           'risultati. I record bibliografici sono pubblicati e verificati separatamente.')

def mark_unavailable(page: Path, statistics: Path) -> None:
    payload = json.loads(statistics.read_text())
    if payload.get('dataThrough') is not None or payload.get('daily') or payload.get('extraRuns'):
        raise ValueError('Only the empty deterministic statistics baseline may be marked unavailable')
    if payload['summary']['allTime']['newCandidates'] is not None:
        raise ValueError('Unavailable candidate counts must remain null')
    content, count = re.subn(r'(<p id="latest-execution"[^>]*>).*?(</p>)',
                            lambda m: m[1] + WARNING + m[2], page.read_text(), flags=re.S)
    if count != 1:
        raise ValueError('Statistics warning target missing or duplicated')
    content = re.sub(r'<script\b[^>]*\bsrc=["\'](?:\./)?stats\.js(?:\?[^"\']*)?["\'][^>]*>\s*</script>', '', content)
    page.write_text(content)

if __name__ == '__main__':
    mark_unavailable(ROOT/'site/stats.html', ROOT/'site/data/research-stats.json')
