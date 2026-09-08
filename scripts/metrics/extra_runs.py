"""Public execution telemetry, deliberately outside the scheduled-day totals."""
from datetime import datetime
from scripts.surveillance_identity import batch_day, is_extra, validate_cycle_run

FIELDS = {'batchId', 'date', 'startedAt', 'finishedAt', 'status',
          'queriesPlanned', 'queriesCompleted', 'occurrencesReturned',
          'uniqueResults', 'intakeCandidates', 'failureCode'}


def project_extra_runs(runs, cycle):
    if __package__:
        from .surveillance import validate_run
    else:
        from surveillance import validate_run
    rows = []
    for original in runs:
        run = validate_run(original)
        if not is_extra(run['batch_id']):
            continue
        validate_cycle_run(run, cycle)
        source = run['sources'][0]
        rows.append(dict(batchId=run['batch_id'], date=run['run_date'],
                         startedAt=run['window_start'], finishedAt=run['window_end'],
                         status=run['status'], queriesPlanned=source['queries_planned'],
                         queriesCompleted=source['queries_completed'],
                         occurrencesReturned=run['totals']['occurrences_returned'],
                         uniqueResults=run['totals']['unique_results'],
                         intakeCandidates=run['totals']['intake_candidates'],
                         failureCode=source['failure_code']))
    rows.sort(key=lambda r: (r['startedAt'], r['batchId']))
    validate_extra_rows(rows, cycle)
    return rows


def validate_extra_rows(rows, cycle, *, as_of=None):
    from zoneinfo import ZoneInfo
    import re
    if not isinstance(rows, list):
        raise ValueError('extraRuns must be an array')
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError('invalid or private extra execution fields')
        batch = row['batchId']
        if not is_extra(batch) or batch in seen or batch_day(batch).isoformat() != row['date']:
            raise ValueError('duplicate or inconsistent extra execution identity')
        seen.add(batch)
        started = datetime.fromisoformat(row['startedAt'].replace('Z', '+00:00'))
        ended = datetime.fromisoformat(row['finishedAt'].replace('Z', '+00:00'))
        if (started.tzinfo is None or ended.tzinfo is None or ended < started
                or any(t.astimezone(ZoneInfo('Europe/Rome')).date() != batch_day(batch) for t in (started, ended))
                or (as_of is not None and ended > datetime.fromisoformat(as_of.replace('Z', '+00:00')))):
            raise ValueError('invalid extra execution window')
        validate_cycle_run({'batch_id': batch, 'run_date': row['date'], 'window_start': row['startedAt']}, cycle)
        planned, completed = row['queriesPlanned'], row['queriesCompleted']
        if type(planned) is not int or type(completed) is not int or not 7 <= planned <= 1000 or not 0 <= completed <= planned:
            raise ValueError('invalid extra query counts')
        status = 'completed' if completed == planned else ('partial' if completed else 'failed')
        if row['status'] != status:
            raise ValueError('extra status disagrees with query completion')
        volumes = [row[k] for k in ('intakeCandidates', 'uniqueResults', 'occurrencesReturned')]
        if status == 'completed':
            if any(type(v) is not int or v < 0 for v in volumes) or volumes != sorted(volumes) or row['failureCode'] is not None:
                raise ValueError('invalid completed extra volumes')
        elif any(v is not None for v in volumes) or not isinstance(row['failureCode'], str) or not re.fullmatch(r'[a-z][a-z0-9_]{2,79}', row['failureCode']):
            raise ValueError('failed/partial extra must retain null volumes and a technical failure')
