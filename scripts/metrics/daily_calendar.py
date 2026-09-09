"""A calendar is an expectation, never a fabricated surveillance ledger record."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import json

CYCLE = json.loads((Path(__file__).resolve().parents[2] / "config/archive-cycle.json").read_text())
SCOPES = {"legacy": date(2026, 8, 31), CYCLE["review_id"]: date.fromisoformat(CYCLE["daily_start_date"])}
SOURCE_COUNTS = {"legacy": 2, CYCLE["review_id"]: 1}

ROME = ZoneInfo("Europe/Rome")
START = date(2026, 8, 31)  # Effective date of the governed aggregate metrics ledger.
ERRORS = {"quota_exceeded", "rate_limited", "timeout", "authentication_failed", "provider_unavailable", "not_run", "budget_exhausted"}
FIELDS = {"date", "status", "ledgerPresent", "startedAt", "finishedAt", "attemptCount", "queriesPlanned", "queriesCompleted", "completedSources", "expectedSources", "failureCodes"}


def calendar_projection(runs, as_of, start=START, review_id="legacy"):
    if SCOPES.get(review_id) != start:
        raise ValueError("calendar scope/start mismatch")
    if any(date.fromisoformat(r["run_date"]) < start for r in runs):
        raise ValueError("run predates this calendar")
    expected_sources = SOURCE_COUNTS[review_id]
    expected_versions = {1} if review_id == "legacy" else {2, 3}
    if any(r.get("schema_version") not in expected_versions or len(r["expected_sources"]) != expected_sources for r in runs):
        raise ValueError("run source policy does not belong to this calendar")
    if isinstance(as_of, str):
        as_of = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    if as_of.tzinfo is None:
        raise ValueError("calendar clock must be timezone-aware")
    as_of = as_of.astimezone(ROME)
    if any(date.fromisoformat(r["run_date"]) > as_of.date() for r in runs):
        raise ValueError("run follows calendar clock")
    by_date = {r["run_date"]: r for r in runs}
    if len(by_date) != len(runs):
        raise ValueError("duplicate calendar batch")
    rows = []
    day = start
    while day <= as_of.date():
        key = day.isoformat()
        run = by_date.get(key)
        due = as_of >= datetime.combine(day, time(7, 20), ROME)
        sources = run["sources"] if run else []
        failures = sorted({code if code in ERRORS else "other_provider_failure"
                           for s in sources if (code := s.get("failure_code"))})
        rows.append({
            "date": key, "status": run["status"] if run else "missing" if due else "planned",
            "ledgerPresent": run is not None,
            "startedAt": run["window_start"] if run else None,
            "finishedAt": run["window_end"] if run else None,
            # Legacy ledger does not measure retries: one comment is not one attempt.
            "attemptCount": None,
            "queriesPlanned": sum(s["queries_planned"] for s in sources) if run else 7 * expected_sources,
            "queriesCompleted": sum(s["queries_completed"] for s in sources) if run else None,
            "completedSources": sum(s["status"] == "completed" for s in sources) if run else 0,
            "expectedSources": expected_sources, "failureCodes": failures,
        })
        day += timedelta(days=1)
    due_rows = [r for r in rows if r["status"] != "planned"]
    recent = [r for r in due_rows if date.fromisoformat(r["date"]) >= as_of.date() - timedelta(days=29)]
    completed = sum(r["status"] == "completed" for r in due_rows)
    return {
        "reviewId": review_id, "timezone": "Europe/Rome", "scheduledLocalTime": "07:00",
        "asOf": as_of.isoformat(), "coverageStart": start.isoformat(), "lastLedgerDate": max(by_date, default=None),
        "rows": rows, "expectedDays": len(due_rows), "completedDays": completed,
        "missingDays": sum(r["status"] == "missing" for r in rows),
        "completionRate": completed / len(due_rows) if due_rows else None,
        "sourceCompletionRate30": sum(r["completedSources"] for r in recent) / sum(r["expectedSources"] for r in recent) if recent else None,
    }


def validate_calendar(calendar, daily):
    expected_keys = {"reviewId", "timezone", "scheduledLocalTime", "asOf", "coverageStart", "lastLedgerDate", "rows", "expectedDays", "completedDays", "missingDays", "completionRate", "sourceCompletionRate30"}
    if not isinstance(calendar, dict) or set(calendar) != expected_keys:
        raise ValueError("invalid calendar fields")
    if calendar["reviewId"] not in SCOPES or (calendar["timezone"], calendar["scheduledLocalTime"]) != ("Europe/Rome", "07:00"):
        raise ValueError("invalid calendar scope")
    end = datetime.fromisoformat(calendar["asOf"])
    if end.tzinfo is None:
        raise ValueError("calendar asOf needs timezone")
    start = date.fromisoformat(calendar["coverageStart"])
    if start != SCOPES[calendar["reviewId"]]:
        raise ValueError("unexpected calendar coverage start")
    expected_sources = SOURCE_COUNTS[calendar["reviewId"]]
    expected_dates = [(start + timedelta(days=i)).isoformat() for i in range((end.astimezone(ROME).date() - start).days + 1)]
    if [r.get("date") for r in calendar["rows"]] != expected_dates:
        raise ValueError("calendar must represent every day exactly once")
    logged = {r["date"]: r for r in daily}
    if len(logged) != len(daily) or any(key not in expected_dates for key in logged):
        raise ValueError("daily data belong to a retired calendar")
    if calendar["lastLedgerDate"] != max(logged, default=None):
        raise ValueError("calendar freshness mismatch")
    for row in calendar["rows"]:
        if set(row) != FIELDS or row["status"] not in {"completed", "partial", "failed", "missing", "planned"}:
            raise ValueError("invalid calendar row")
        source = logged.get(row["date"])
        due_at = datetime.combine(date.fromisoformat(row["date"]), time(7, 20), ROME)
        if not source and row["status"] != ("missing" if end >= due_at else "planned"):
            raise ValueError("calendar status disagrees with ledger absence and clock")
        if not source and row["failureCodes"] != []:
            raise ValueError("missing day cannot invent provider failures")
        if type(row["ledgerPresent"]) is not bool or row["ledgerPresent"] != bool(source):
            raise ValueError("calendar ledger presence mismatch")
        if source and (source["status"] != row["status"] or source["completedSourceCount"] != row["completedSources"] or source["expectedSourceCount"] != expected_sources):
            raise ValueError("calendar status mismatch")
        if not source and (row["attemptCount"] is not None or row["queriesCompleted"] is not None or row["startedAt"] is not None or row["finishedAt"] is not None or row["completedSources"] != 0):
            raise ValueError("missing day cannot have invented execution data")
        if row["expectedSources"] != expected_sources or row["attemptCount"] is not None:
            raise ValueError("legacy attempts cannot be inferred")
        if not source and row["queriesPlanned"] != 7 * expected_sources:
            raise ValueError("calendar planned query count disagrees with source policy")
        if not isinstance(row["failureCodes"], list) or any(c not in ERRORS | {"other_provider_failure"} for c in row["failureCodes"]):
            raise ValueError("private failure details are forbidden")
    due = [r for r in calendar["rows"] if r["status"] != "planned"]
    complete = sum(r["status"] == "completed" for r in due)
    missing = sum(r["status"] == "missing" for r in due)
    recent = [r for r in due if date.fromisoformat(r["date"]) >= end.astimezone(ROME).date() - timedelta(days=29)]
    expected = [len(due), complete, missing, complete / len(due) if due else None,
                sum(r["completedSources"] for r in recent) / sum(r["expectedSources"] for r in recent) if recent else None]
    actual = [calendar[k] for k in ["expectedDays", "completedDays", "missingDays", "completionRate", "sourceCompletionRate30"]]
    if actual != expected:
        raise ValueError("calendar totals mismatch")
