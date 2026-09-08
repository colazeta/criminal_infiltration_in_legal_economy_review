"""Execution identities: one scheduled batch per day, distinct manual batches."""
import re
from datetime import date

BATCH_PATTERN = r"ACADEMIC-\d{4}-\d{2}-\d{2}(?:-EXTRA-[0-9a-f]{12})?"


def batch_day(value):
    if not isinstance(value, str) or not re.fullmatch(BATCH_PATTERN, value):
        raise ValueError("invalid surveillance batch identity")
    return date.fromisoformat(value[9:19])


def is_extra(value):
    batch_day(value)
    return len(value) > 19


def validate_cycle_run(run, cycle):
    from datetime import datetime
    start = datetime.fromisoformat(run['window_start'].replace('Z', '+00:00'))
    reset = datetime.fromisoformat(cycle['reset_at'].replace('Z', '+00:00'))
    if start < reset or (not is_extra(run['batch_id']) and run['run_date'] < cycle['daily_start_date']):
        raise ValueError("run belongs to the retired archive cycle")


def candidate_keys(candidate):
    """Collision checks only: do not merge bibliographic identities automatically."""
    import unicodedata
    identifiers = candidate.get('identifiers', {})
    doi = identifiers.get('doi') or candidate.get('doi') or ''
    doi = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', doi.strip().lower())
    keys = {('doi', doi)} if doi else set()
    for value in identifiers.get('other', []):
        keys.add(('id', value.strip().casefold()))
    def normal(value):
        return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', str(value)).casefold()))
    authors = candidate.get('authors') or []
    if isinstance(authors, str):
        authors = authors.split(';')
    if candidate.get('title') and candidate.get('year') and authors:
        keys.add(('citation', normal(candidate['title']), str(candidate['year']), tuple(sorted(normal(a) for a in authors))))
    return keys
