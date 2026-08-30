#!/usr/bin/env python3
"""Validate daily surveillance telemetry and build a public-safe aggregate."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Iterable
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo


SCHEMA_VERSION = 1
ROME = ZoneInfo("Europe/Rome")
ACTIVE_SOURCES = frozenset({"Consensus", "Exa"})
REPOSITORY_FULL_NAME = "colazeta/criminal_infiltration_in_legal_economy_review"
STATUS_VALUES = {"completed", "partial", "failed"}
SOURCE_STATUS_VALUES = {"completed", "failed", "not_run"}
TOTAL_FIELDS = (
    "occurrences_returned",
    "unique_results",
    "known_matches",
    "intake_candidates",
    "not_forwarded",
    "unresolved_identity",
    "possible_duplicate_flags",
    "metadata_conflicts",
)
ASSESSMENT_FIELDS = ("plausible_core", "plausible_contextual", "uncertain")
RUN_FIELDS = {
    "schema_version",
    "batch_id",
    "run_date",
    "window_start",
    "window_end",
    "timezone",
    "status",
    "repository_commit",
    "expected_sources",
    "sources",
    "totals",
    "assessments",
    "intake_issue",
    "notes",
}
SOURCE_FIELDS = {
    "source",
    "status",
    "queries_planned",
    "queries_completed",
    "occurrences_returned",
    "unique_results",
    "candidate_hits",
    "exclusive_candidates",
    "failure_code",
    "limitations",
}
INTAKE_FIELDS = {"created", "number", "url"}
PUBLIC_FIELDS = {
    "schemaVersion",
    "ledgerIssue",
    "dataThrough",
    "dateRange",
    "summary",
    "definitions",
    "daily",
    "sources",
}
PUBLIC_DAILY_FIELDS = {
    "date",
    "batchId",
    "status",
    "expectedSourceCount",
    "completedSourceCount",
    "sourceCompleteness",
    "occurrencesReturned",
    "uniqueResults",
    "knownMatches",
    "intakeCandidates",
    "notForwarded",
    "unresolvedIdentity",
    "possibleDuplicateFlags",
    "metadataConflicts",
    "candidateRate",
    "knownOverlapRate",
    "deduplicationShare",
    "intakeIssueCreated",
}
PUBLIC_SOURCE_FIELDS = {
    "source",
    "expectedRuns",
    "completedRuns",
    "completionRate",
    "queriesCompleted",
    "occurrencesReturned",
    "uniqueResults",
    "candidateHits",
    "exclusiveCandidates",
}
DEFINITION_FIELDS = {
    "occurrencesReturned",
    "uniqueResults",
    "knownMatches",
    "newCandidates",
    "candidateRate",
    "sourceCompletionRate",
}
FORBIDDEN_PUBLIC_KEYS = {
    "title",
    "authors",
    "abstract",
    "doi",
    "evidence_quote",
    "reviewer",
    "notes",
    "query",
    "query_string",
}


class MetricsError(ValueError):
    """Raised when surveillance telemetry violates its contract."""


def require_exact_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if extra:
            details.append(f"unexpected {', '.join(extra)}")
        raise MetricsError(f"{label}: {'; '.join(details)}")


def parse_date(value: Any, label: str) -> date:
    if not isinstance(value, str):
        raise MetricsError(f"{label}: expected YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise MetricsError(f"{label}: invalid date") from exc


def parse_datetime(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise MetricsError(f"{label}: expected an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MetricsError(f"{label}: invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise MetricsError(f"{label}: timezone offset is required")
    return parsed


def count_or_none(value: Any, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MetricsError(f"{label}: expected a non-negative integer or null")
    return value


def count(value: Any, label: str) -> int:
    parsed = count_or_none(value, label)
    if parsed is None:
        raise MetricsError(f"{label}: null is not allowed")
    return parsed


def safe_text_list(value: Any, label: str, maximum: int, length: int) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise MetricsError(f"{label}: expected at most {maximum} text values")
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or len(item) > length:
            raise MetricsError(f"{label}: invalid text value")
        result.append(item.strip())
    return result


def validate_run(run: dict[str, Any]) -> dict[str, Any]:
    """Validate and return one normalised surveillance-run envelope."""

    if not isinstance(run, dict):
        raise MetricsError("run: expected an object")
    require_exact_fields(run, RUN_FIELDS, "run")
    if type(run["schema_version"]) is not int or run["schema_version"] != SCHEMA_VERSION:
        raise MetricsError("run: unsupported schema_version")

    batch_id = run["batch_id"]
    if not isinstance(batch_id, str) or not re.fullmatch(
        r"ACADEMIC-\d{4}-\d{2}-\d{2}", batch_id
    ):
        raise MetricsError("run: invalid batch_id")
    run_date = parse_date(run["run_date"], "run.run_date")
    if batch_id != f"ACADEMIC-{run_date.isoformat()}":
        raise MetricsError("run: batch_id date differs from run_date")
    started = parse_datetime(run["window_start"], "run.window_start")
    ended = parse_datetime(run["window_end"], "run.window_end")
    if ended < started:
        raise MetricsError("run: window_end precedes window_start")
    if any(
        moment.utcoffset() != moment.astimezone(ROME).utcoffset()
        for moment in (started, ended)
    ):
        raise MetricsError("run: window timestamps use an offset incompatible with Europe/Rome")
    if started.astimezone(ROME).date() != run_date:
        raise MetricsError("run: window_start date differs from run_date")
    if ended.astimezone(ROME).date() != run_date:
        raise MetricsError("run: window_end date differs from run_date")
    if run["timezone"] != "Europe/Rome":
        raise MetricsError("run: timezone must be Europe/Rome")
    status = run["status"]
    if status not in STATUS_VALUES:
        raise MetricsError("run: invalid status")
    if not isinstance(run["repository_commit"], str) or not re.fullmatch(
        r"[0-9a-f]{40}", run["repository_commit"]
    ):
        raise MetricsError("run: repository_commit must be a full lowercase SHA")

    expected_sources = run["expected_sources"]
    if (
        not isinstance(expected_sources, list)
        or not expected_sources
        or len(expected_sources) > 10
        or len(expected_sources) != len(set(expected_sources))
    ):
        raise MetricsError("run: expected_sources must be a short unique list")
    for source_name in expected_sources:
        if not isinstance(source_name, str) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9 ._-]{1,39}", source_name
        ):
            raise MetricsError("run: invalid expected source name")
    if set(expected_sources) != ACTIVE_SOURCES:
        raise MetricsError(
            "run: expected_sources must match the governed active source set"
        )

    sources = run["sources"]
    if not isinstance(sources, list) or len(sources) != len(expected_sources):
        raise MetricsError("run: sources must contain every expected source exactly once")
    normalised_sources = []
    seen_sources: set[str] = set()
    completed_sources = 0
    for index, source in enumerate(sources):
        label = f"run.sources[{index}]"
        if not isinstance(source, dict):
            raise MetricsError(f"{label}: expected an object")
        require_exact_fields(source, SOURCE_FIELDS, label)
        source_name = source["source"]
        if source_name not in expected_sources or source_name in seen_sources:
            raise MetricsError(f"{label}: unexpected or duplicate source")
        seen_sources.add(source_name)
        source_status = source["status"]
        if source_status not in SOURCE_STATUS_VALUES:
            raise MetricsError(f"{label}: invalid status")
        planned = count(source["queries_planned"], f"{label}.queries_planned")
        completed = count(source["queries_completed"], f"{label}.queries_completed")
        if planned < 1:
            raise MetricsError(f"{label}: an expected source requires a planned query")
        if completed > planned:
            raise MetricsError(f"{label}: completed queries exceed planned queries")
        if source_status == "not_run" and completed != 0:
            raise MetricsError(f"{label}: a source that was not run cannot complete queries")
        source_counts = {
            field: count_or_none(source[field], f"{label}.{field}")
            for field in (
                "occurrences_returned",
                "unique_results",
                "candidate_hits",
                "exclusive_candidates",
            )
        }
        if source_status == "completed":
            completed_sources += 1
            if any(value is None for value in source_counts.values()):
                raise MetricsError(f"{label}: completed source counts cannot be null")
            if completed != planned:
                raise MetricsError(f"{label}: completed source must finish planned queries")
            if source_counts["unique_results"] > source_counts["occurrences_returned"]:
                raise MetricsError(f"{label}: unique results exceed occurrences")
            if source_counts["candidate_hits"] > source_counts["unique_results"]:
                raise MetricsError(f"{label}: candidate hits exceed unique results")
            if source_counts["exclusive_candidates"] > source_counts["candidate_hits"]:
                raise MetricsError(f"{label}: exclusive candidates exceed candidate hits")
        elif any(value is not None for value in source_counts.values()):
            raise MetricsError(f"{label}: incomplete source counts must be null")

        failure_code = source["failure_code"]
        if failure_code is not None and (
            not isinstance(failure_code, str) or not failure_code.strip() or len(failure_code) > 80
        ):
            raise MetricsError(f"{label}: invalid failure_code")
        if source_status == "completed" and failure_code is not None:
            raise MetricsError(f"{label}: completed source cannot have a failure_code")
        if source_status != "completed" and failure_code is None:
            raise MetricsError(f"{label}: incomplete source requires a failure_code")
        limitations = safe_text_list(source["limitations"], f"{label}.limitations", 10, 180)
        normalised_sources.append(
            {
                "source": source_name,
                "status": source_status,
                "queries_planned": planned,
                "queries_completed": completed,
                **source_counts,
                "failure_code": failure_code.strip() if failure_code else None,
                "limitations": limitations,
            }
        )

    expected_status = (
        "completed"
        if completed_sources == len(expected_sources)
        else "failed"
        if completed_sources == 0
        else "partial"
    )
    if status != expected_status:
        raise MetricsError("run: status disagrees with source completion")

    totals = run["totals"]
    if not isinstance(totals, dict):
        raise MetricsError("run.totals: expected an object")
    require_exact_fields(totals, set(TOTAL_FIELDS), "run.totals")
    normalised_totals = {
        field: count_or_none(totals[field], f"run.totals.{field}")
        for field in TOTAL_FIELDS
    }

    assessments = run["assessments"]
    if not isinstance(assessments, dict):
        raise MetricsError("run.assessments: expected an object")
    require_exact_fields(assessments, set(ASSESSMENT_FIELDS), "run.assessments")
    normalised_assessments = {
        field: count(assessments[field], f"run.assessments.{field}")
        for field in ASSESSMENT_FIELDS
    }

    intake = run["intake_issue"]
    if not isinstance(intake, dict):
        raise MetricsError("run.intake_issue: expected an object")
    require_exact_fields(intake, INTAKE_FIELDS, "run.intake_issue")
    created = intake["created"]
    if not isinstance(created, bool):
        raise MetricsError("run.intake_issue.created: expected boolean")
    number = intake["number"]
    if number is not None and (isinstance(number, bool) or not isinstance(number, int) or number < 1):
        raise MetricsError("run.intake_issue.number: invalid issue number")
    url = intake["url"]
    if url is not None:
        if not isinstance(url, str):
            raise MetricsError("run.intake_issue.url: expected URL or null")
        parsed_url = urlsplit(url)
        if parsed_url.scheme != "https" or parsed_url.netloc != "github.com":
            raise MetricsError("run.intake_issue.url: only GitHub HTTPS URLs are allowed")
    if created != (number is not None and url is not None):
        raise MetricsError("run.intake_issue: created, number and URL disagree")
    if created and url != f"https://github.com/{REPOSITORY_FULL_NAME}/issues/{number}":
        raise MetricsError(
            "run.intake_issue: URL must match the canonical repository and issue number"
        )

    if status == "completed":
        if any(value is None for value in normalised_totals.values()):
            raise MetricsError("run.totals: completed run counts cannot be null")
        total_occurrences = normalised_totals["occurrences_returned"]
        unique_results = normalised_totals["unique_results"]
        known_matches = normalised_totals["known_matches"]
        intake_candidates = normalised_totals["intake_candidates"]
        not_forwarded = normalised_totals["not_forwarded"]
        unresolved_identity = normalised_totals["unresolved_identity"]
        if unique_results > total_occurrences:
            raise MetricsError("run.totals: unique results exceed occurrences")
        if (
            known_matches + intake_candidates + not_forwarded + unresolved_identity
            != unique_results
        ):
            raise MetricsError("run.totals: unique-result disposition does not reconcile")
        if normalised_totals["possible_duplicate_flags"] > unique_results:
            raise MetricsError("run.totals: duplicate flags exceed unique results")
        if normalised_totals["metadata_conflicts"] > unique_results:
            raise MetricsError("run.totals: metadata conflicts exceed unique results")
        if sum(normalised_assessments.values()) != intake_candidates:
            raise MetricsError("run.assessments: counts do not equal intake candidates")
        source_occurrences = sum(row["occurrences_returned"] for row in normalised_sources)
        source_unique = sum(row["unique_results"] for row in normalised_sources)
        source_candidate_hits = sum(row["candidate_hits"] for row in normalised_sources)
        source_exclusive = sum(row["exclusive_candidates"] for row in normalised_sources)
        if source_occurrences != total_occurrences:
            raise MetricsError("run.totals: occurrences do not equal source occurrences")
        if unique_results > source_unique:
            raise MetricsError("run.totals: cross-source unique results exceed source totals")
        if unique_results < max(
            row["unique_results"] for row in normalised_sources
        ):
            raise MetricsError(
                "run.totals: cross-source unique results fall below a source total"
            )
        if any(row["candidate_hits"] > intake_candidates for row in normalised_sources):
            raise MetricsError("run.sources: candidate hits exceed total intake candidates")
        if source_candidate_hits < intake_candidates or source_exclusive > intake_candidates:
            raise MetricsError("run.sources: candidate attribution does not reconcile")
        for row in normalised_sources:
            other = next(
                candidate
                for candidate in normalised_sources
                if candidate["source"] != row["source"]
            )
            if row["exclusive_candidates"] != (
                intake_candidates - other["candidate_hits"]
            ):
                raise MetricsError(
                    "run.sources: exclusive candidate attribution does not reconcile"
                )
        if created != (intake_candidates > 0):
            raise MetricsError("run.intake_issue: issue creation disagrees with intake count")
    else:
        if any(value is not None for value in normalised_totals.values()):
            raise MetricsError("run.totals: incomplete-run totals must be null")
        if any(normalised_assessments.values()):
            raise MetricsError("run.assessments: incomplete runs cannot report assessments")
        if created:
            raise MetricsError("run.intake_issue: incomplete run cannot create intake")

    notes = safe_text_list(run["notes"], "run.notes", 10, 280)
    return {
        "schema_version": SCHEMA_VERSION,
        "batch_id": batch_id,
        "run_date": run_date.isoformat(),
        "window_start": started.isoformat(),
        "window_end": ended.isoformat(),
        "timezone": "Europe/Rome",
        "status": status,
        "repository_commit": run["repository_commit"],
        "expected_sources": list(expected_sources),
        "sources": normalised_sources,
        "totals": normalised_totals,
        "assessments": normalised_assessments,
        "intake_issue": {"created": created, "number": number, "url": url},
        "notes": notes,
    }


def safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def source_summary(runs: list[dict[str, Any]], start: date) -> list[dict[str, Any]]:
    expected: dict[str, int] = defaultdict(int)
    completed: dict[str, int] = defaultdict(int)
    contribution_runs: dict[str, int] = defaultdict(int)
    totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for run in runs:
        if parse_date(run["run_date"], "run.run_date") < start:
            continue
        by_name = {row["source"]: row for row in run["sources"]}
        for name in run["expected_sources"]:
            expected[name] += 1
            row = by_name[name]
            totals[name]["queries_completed"] += row["queries_completed"]
            if row["status"] != "completed":
                continue
            completed[name] += 1
            if run["status"] == "completed":
                contribution_runs[name] += 1
                for field in (
                    "occurrences_returned",
                    "unique_results",
                    "candidate_hits",
                    "exclusive_candidates",
                ):
                    totals[name][field] += row[field]
    return [
        {
            "source": name,
            "expectedRuns": expected[name],
            "completedRuns": completed[name],
            "completionRate": safe_rate(completed[name], expected[name]),
            "queriesCompleted": totals[name]["queries_completed"],
            "occurrencesReturned": (
                totals[name]["occurrences_returned"] if contribution_runs[name] else None
            ),
            "uniqueResults": (
                totals[name]["unique_results"] if contribution_runs[name] else None
            ),
            "candidateHits": (
                totals[name]["candidate_hits"] if contribution_runs[name] else None
            ),
            "exclusiveCandidates": (
                totals[name]["exclusive_candidates"] if contribution_runs[name] else None
            ),
        }
        for name in sorted(expected)
    ]


def build_public_payload(
    runs: Iterable[dict[str, Any]], ledger_issue: int, repository: str
) -> dict[str, Any]:
    """Create the public aggregate. Candidate metadata is never accepted or emitted."""

    if not isinstance(ledger_issue, int) or ledger_issue < 1:
        raise MetricsError("ledger_issue must be a positive integer")
    if repository != REPOSITORY_FULL_NAME:
        raise MetricsError("repository must match the governed repository")
    validated = [validate_run(run) for run in runs]
    validated.sort(key=lambda row: row["run_date"])
    batch_ids = [row["batch_id"] for row in validated]
    dates = [row["run_date"] for row in validated]
    if len(batch_ids) != len(set(batch_ids)) or len(dates) != len(set(dates)):
        raise MetricsError("ledger contains a duplicate batch or run date")

    if validated:
        anchor = parse_date(validated[-1]["run_date"], "run.run_date")
        first = validated[0]["run_date"]
        last = validated[-1]["run_date"]
    else:
        anchor = date.min
        first = None
        last = None
    seven_start = anchor - timedelta(days=6) if validated else date.min
    thirty_start = anchor - timedelta(days=29) if validated else date.min

    daily = []
    for run in validated:
        totals = run["totals"]
        if run["status"] == "completed":
            candidate_rate = safe_rate(
                totals["intake_candidates"], totals["unique_results"]
            )
            known_overlap_rate = safe_rate(
                totals["known_matches"], totals["unique_results"]
            )
            deduplication_share = safe_rate(
                totals["occurrences_returned"] - totals["unique_results"],
                totals["occurrences_returned"],
            )
        else:
            candidate_rate = known_overlap_rate = deduplication_share = None
        source_complete = sum(row["status"] == "completed" for row in run["sources"])
        daily.append(
            {
                "date": run["run_date"],
                "batchId": run["batch_id"],
                "status": run["status"],
                "expectedSourceCount": len(run["expected_sources"]),
                "completedSourceCount": source_complete,
                "sourceCompleteness": safe_rate(source_complete, len(run["expected_sources"])),
                "occurrencesReturned": totals["occurrences_returned"],
                "uniqueResults": totals["unique_results"],
                "knownMatches": totals["known_matches"],
                "intakeCandidates": totals["intake_candidates"],
                "notForwarded": totals["not_forwarded"],
                "unresolvedIdentity": totals["unresolved_identity"],
                "possibleDuplicateFlags": totals["possible_duplicate_flags"],
                "metadataConflicts": totals["metadata_conflicts"],
                "candidateRate": candidate_rate,
                "knownOverlapRate": known_overlap_rate,
                "deduplicationShare": deduplication_share,
                "intakeIssueCreated": run["intake_issue"]["created"],
            }
        )

    def complete_since(start: date) -> list[dict[str, Any]]:
        return [
            run
            for run in validated
            if parse_date(run["run_date"], "run.run_date") >= start
            and run["status"] == "completed"
        ]

    seven_complete = complete_since(seven_start)
    thirty_complete = complete_since(thirty_start)
    thirty_runs = [
        run
        for run in validated
        if parse_date(run["run_date"], "run.run_date") >= thirty_start
    ]
    expected_source_runs = sum(len(run["expected_sources"]) for run in thirty_runs)
    completed_source_runs = sum(
        row["status"] == "completed"
        for run in thirty_runs
        for row in run["sources"]
    )

    def summed(runs_subset: list[dict[str, Any]], field: str) -> int | None:
        if not runs_subset:
            return None
        return sum(run["totals"][field] for run in runs_subset)

    summary = {
        "runDays": len(validated),
        "completedRuns": sum(run["status"] == "completed" for run in validated),
        "partialRuns": sum(run["status"] == "partial" for run in validated),
        "failedRuns": sum(run["status"] == "failed" for run in validated),
        "lastRunStatus": validated[-1]["status"] if validated else None,
        "last7Days": {
            "completedRuns": len(seven_complete),
            "uniqueResults": summed(seven_complete, "unique_results"),
            "knownMatches": summed(seven_complete, "known_matches"),
            "newCandidates": summed(seven_complete, "intake_candidates"),
        },
        "last30Days": {
            "loggedRuns": len(thirty_runs),
            "completedRuns": len(thirty_complete),
            "partialRuns": sum(run["status"] == "partial" for run in thirty_runs),
            "failedRuns": sum(run["status"] == "failed" for run in thirty_runs),
            "sourceCompletionRate": safe_rate(completed_source_runs, expected_source_runs),
            "uniqueResults": summed(thirty_complete, "unique_results"),
            "knownMatches": summed(thirty_complete, "known_matches"),
            "newCandidates": summed(thirty_complete, "intake_candidates"),
            "metadataConflicts": summed(thirty_complete, "metadata_conflicts"),
        },
        "allTime": {
            "newCandidates": summed(
                [run for run in validated if run["status"] == "completed"],
                "intake_candidates",
            )
        },
    }

    return {
        "schemaVersion": SCHEMA_VERSION,
        "ledgerIssue": {
            "number": ledger_issue,
            "url": f"https://github.com/{repository}/issues/{ledger_issue}",
        },
        "dataThrough": last,
        "dateRange": {"first": first, "last": last},
        "summary": summary,
        "definitions": {
            "occurrencesReturned": "All result occurrences returned across source queries; repeats are included.",
            "uniqueResults": "Results remaining after within-run identifier and title/year reconciliation.",
            "knownMatches": "Unique results already represented in the registry or an earlier intake issue.",
            "newCandidates": "Records not already known that were forwarded to the human intake queue with a plausible or uncertain assessment.",
            "candidateRate": "New intake candidates divided by unique results in a completed run; this is not screening yield.",
            "sourceCompletionRate": "Completed expected source runs divided by all expected source runs; failures are not treated as zero-result searches.",
        },
        "daily": daily,
        "sources": source_summary(validated, thirty_start),
    }


def validate_public_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a rendered public payload without requiring private ledger input."""

    if not isinstance(payload, dict):
        raise MetricsError("public statistics: expected an object")
    require_exact_fields(payload, PUBLIC_FIELDS, "public statistics")
    if (
        type(payload["schemaVersion"]) is not int
        or payload["schemaVersion"] != SCHEMA_VERSION
    ):
        raise MetricsError("public statistics: unsupported schemaVersion")

    def reject_forbidden_keys(value: Any) -> None:
        if isinstance(value, dict):
            forbidden = FORBIDDEN_PUBLIC_KEYS.intersection(value)
            if forbidden:
                raise MetricsError(
                    "public statistics: forbidden field(s): "
                    + ", ".join(sorted(forbidden))
                )
            for child in value.values():
                reject_forbidden_keys(child)
        elif isinstance(value, list):
            for child in value:
                reject_forbidden_keys(child)

    reject_forbidden_keys(payload)

    ledger = payload["ledgerIssue"]
    if not isinstance(ledger, dict):
        raise MetricsError("public statistics: invalid ledgerIssue")
    require_exact_fields(ledger, {"number", "url"}, "public statistics.ledgerIssue")
    issue_number = count(ledger["number"], "public statistics.ledgerIssue.number")
    if issue_number < 1:
        raise MetricsError("public statistics: ledger issue must be positive")
    issue_url = ledger["url"]
    parsed = urlsplit(issue_url) if isinstance(issue_url, str) else None
    expected_ledger_url = (
        f"https://github.com/{REPOSITORY_FULL_NAME}/issues/{issue_number}"
    )
    if (
        not parsed
        or parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or issue_url != expected_ledger_url
    ):
        raise MetricsError("public statistics: invalid ledger URL")

    daily = payload["daily"]
    if not isinstance(daily, list):
        raise MetricsError("public statistics: daily must be a list")
    normalised_daily = []
    seen_dates: set[str] = set()
    for index, row in enumerate(daily):
        label = f"public statistics.daily[{index}]"
        if not isinstance(row, dict):
            raise MetricsError(f"{label}: expected an object")
        require_exact_fields(row, PUBLIC_DAILY_FIELDS, label)
        row_date = parse_date(row["date"], f"{label}.date")
        if row["date"] in seen_dates:
            raise MetricsError("public statistics: duplicate daily date")
        seen_dates.add(row["date"])
        if row["batchId"] != f"ACADEMIC-{row_date.isoformat()}":
            raise MetricsError(f"{label}: batch ID and date disagree")
        status = row["status"]
        if status not in STATUS_VALUES:
            raise MetricsError(f"{label}: invalid status")
        expected_sources = count(row["expectedSourceCount"], f"{label}.expectedSourceCount")
        completed_sources = count(row["completedSourceCount"], f"{label}.completedSourceCount")
        if expected_sources < 1 or completed_sources > expected_sources:
            raise MetricsError(f"{label}: invalid source counts")
        if row["sourceCompleteness"] != safe_rate(completed_sources, expected_sources):
            raise MetricsError(f"{label}: source completeness does not reconcile")
        count_values = {
            field: count_or_none(row[field], f"{label}.{field}")
            for field in (
                "occurrencesReturned",
                "uniqueResults",
                "knownMatches",
                "intakeCandidates",
                "notForwarded",
                "unresolvedIdentity",
                "possibleDuplicateFlags",
                "metadataConflicts",
            )
        }
        if status == "completed":
            if completed_sources != expected_sources:
                raise MetricsError(f"{label}: completed status disagrees with sources")
            if any(value is None for value in count_values.values()):
                raise MetricsError(f"{label}: completed counts cannot be null")
            occurrences = count_values["occurrencesReturned"]
            unique_results = count_values["uniqueResults"]
            known_matches = count_values["knownMatches"]
            intake_candidates = count_values["intakeCandidates"]
            not_forwarded = count_values["notForwarded"]
            unresolved_identity = count_values["unresolvedIdentity"]
            if unique_results > occurrences:
                raise MetricsError(f"{label}: unique results exceed occurrences")
            if (
                known_matches + intake_candidates + not_forwarded + unresolved_identity
                != unique_results
            ):
                raise MetricsError(f"{label}: unique-result disposition does not reconcile")
            if count_values["possibleDuplicateFlags"] > unique_results:
                raise MetricsError(f"{label}: duplicate flags exceed unique results")
            if count_values["metadataConflicts"] > unique_results:
                raise MetricsError(f"{label}: metadata conflicts exceed unique results")
            expected_rates = {
                "candidateRate": safe_rate(intake_candidates, unique_results),
                "knownOverlapRate": safe_rate(known_matches, unique_results),
                "deduplicationShare": safe_rate(
                    occurrences - unique_results, occurrences
                ),
            }
            for field, expected_rate in expected_rates.items():
                if row[field] != expected_rate:
                    raise MetricsError(f"{label}: {field} does not reconcile")
        else:
            if any(value is not None for value in count_values.values()):
                raise MetricsError(f"{label}: incomplete counts must be null")
            if any(row[field] is not None for field in ("candidateRate", "knownOverlapRate", "deduplicationShare")):
                raise MetricsError(f"{label}: incomplete rates must be null")
            if row["intakeIssueCreated"] is not False:
                raise MetricsError(f"{label}: incomplete run cannot create an intake issue")
        if not isinstance(row["intakeIssueCreated"], bool):
            raise MetricsError(f"{label}: intakeIssueCreated must be boolean")
        if status == "completed" and row["intakeIssueCreated"] != (
            count_values["intakeCandidates"] > 0
        ):
            raise MetricsError(f"{label}: intake issue state disagrees with candidate count")
        normalised_daily.append(row)

    if [row["date"] for row in normalised_daily] != sorted(seen_dates):
        raise MetricsError("public statistics: daily rows must be sorted")
    first = normalised_daily[0]["date"] if normalised_daily else None
    last = normalised_daily[-1]["date"] if normalised_daily else None
    if payload["dataThrough"] != last:
        raise MetricsError("public statistics: dataThrough disagrees with daily rows")
    date_range = payload["dateRange"]
    if not isinstance(date_range, dict):
        raise MetricsError("public statistics: invalid dateRange")
    require_exact_fields(date_range, {"first", "last"}, "public statistics.dateRange")
    if date_range != {"first": first, "last": last}:
        raise MetricsError("public statistics: dateRange disagrees with daily rows")

    definitions = payload["definitions"]
    if not isinstance(definitions, dict):
        raise MetricsError("public statistics: invalid definitions")
    require_exact_fields(definitions, DEFINITION_FIELDS, "public statistics.definitions")
    if any(not isinstance(value, str) or not value.strip() for value in definitions.values()):
        raise MetricsError("public statistics: definitions cannot be blank")

    sources = payload["sources"]
    if not isinstance(sources, list):
        raise MetricsError("public statistics: sources must be a list")
    if normalised_daily:
        source_window_start = (
            parse_date(normalised_daily[-1]["date"], "daily date")
            - timedelta(days=29)
        )
        source_window_rows = [
            row
            for row in normalised_daily
            if parse_date(row["date"], "daily date") >= source_window_start
        ]
        has_completed_day = any(
            daily_row["status"] == "completed" for daily_row in source_window_rows
        )
    else:
        source_window_rows = []
        has_completed_day = False
    source_names = []
    source_volume_rows = []
    source_completed_runs = 0
    for index, row in enumerate(sources):
        label = f"public statistics.sources[{index}]"
        if not isinstance(row, dict):
            raise MetricsError(f"{label}: expected an object")
        require_exact_fields(row, PUBLIC_SOURCE_FIELDS, label)
        if not isinstance(row["source"], str) or not row["source"].strip():
            raise MetricsError(f"{label}: invalid source")
        if row["source"] not in ACTIVE_SOURCES:
            raise MetricsError(f"{label}: source is not in the governed active set")
        source_names.append(row["source"])
        expected_runs = count(row["expectedRuns"], f"{label}.expectedRuns")
        completed_runs = count(row["completedRuns"], f"{label}.completedRuns")
        if expected_runs != len(source_window_rows):
            raise MetricsError(f"{label}: expected runs disagree with daily rows")
        if completed_runs > expected_runs:
            raise MetricsError(f"{label}: completed runs exceed expected runs")
        source_completed_runs += completed_runs
        if row["completionRate"] != safe_rate(completed_runs, expected_runs):
            raise MetricsError(f"{label}: completion rate does not reconcile")
        count(row["queriesCompleted"], f"{label}.queriesCompleted")
        volume_values = {
            field: count_or_none(row[field], f"{label}.{field}")
            for field in (
                "occurrencesReturned",
                "uniqueResults",
                "candidateHits",
                "exclusiveCandidates",
            )
        }
        if has_completed_day and any(
            value is None for value in volume_values.values()
        ):
            raise MetricsError(f"{label}: completed-window source volumes cannot be null")
        if not has_completed_day and any(
            value is not None for value in volume_values.values()
        ):
            raise MetricsError(f"{label}: source volumes require a completed day")
        if has_completed_day:
            source_volume_rows.append(volume_values)
            if volume_values["uniqueResults"] > volume_values["occurrencesReturned"]:
                raise MetricsError(f"{label}: unique results exceed occurrences")
            if volume_values["exclusiveCandidates"] > volume_values["candidateHits"]:
                raise MetricsError(f"{label}: exclusive candidates exceed candidate hits")
    if source_names != sorted(set(source_names)):
        raise MetricsError("public statistics: sources must be unique and sorted")
    if normalised_daily and set(source_names) != ACTIVE_SOURCES:
        raise MetricsError("public statistics: source summary must contain the active set")
    if not normalised_daily and source_names:
        raise MetricsError("public statistics: an empty series cannot contain source summaries")
    expected_completed_sources = sum(
        row["completedSourceCount"] for row in source_window_rows
    )
    if source_completed_runs != expected_completed_sources:
        raise MetricsError(
            "public statistics: source completion totals disagree with daily rows"
        )
    if has_completed_day:
        completed_days = [
            row for row in source_window_rows if row["status"] == "completed"
        ]
        global_occurrences = sum(row["occurrencesReturned"] for row in completed_days)
        global_unique = sum(row["uniqueResults"] for row in completed_days)
        global_candidates = sum(row["intakeCandidates"] for row in completed_days)
        if (
            sum(row["occurrencesReturned"] for row in source_volume_rows)
            != global_occurrences
        ):
            raise MetricsError(
                "public statistics: source occurrences disagree with daily rows"
            )
        source_unique = [row["uniqueResults"] for row in source_volume_rows]
        if global_unique < max(source_unique) or global_unique > sum(source_unique):
            raise MetricsError("public statistics: source unique totals disagree with daily rows")
        source_candidate_hits = [
            row["candidateHits"] for row in source_volume_rows
        ]
        source_exclusive = sum(
            row["exclusiveCandidates"] for row in source_volume_rows
        )
        if (
            any(value > global_candidates for value in source_candidate_hits)
            or sum(source_candidate_hits) < global_candidates
            or source_exclusive > global_candidates
        ):
            raise MetricsError(
                "public statistics: source candidate totals disagree with daily rows"
            )
        source_by_name = dict(zip(source_names, source_volume_rows))
        for name, row in source_by_name.items():
            other_name = next(source for source in ACTIVE_SOURCES if source != name)
            if row["exclusiveCandidates"] != (
                global_candidates - source_by_name[other_name]["candidateHits"]
            ):
                raise MetricsError(
                    "public statistics: exclusive candidate totals disagree with daily rows"
                )

    summary = payload["summary"]
    if not isinstance(summary, dict):
        raise MetricsError("public statistics: invalid summary")
    expected_summary = build_public_payload_from_daily(normalised_daily)
    if summary != expected_summary:
        raise MetricsError("public statistics: summary disagrees with daily rows")
    return payload


def build_public_payload_from_daily(daily: list[dict[str, Any]]) -> dict[str, Any]:
    """Recompute the public summary from already validated daily rows."""

    if daily:
        anchor = parse_date(daily[-1]["date"], "daily date")
        seven_start = anchor - timedelta(days=6)
        thirty_start = anchor - timedelta(days=29)
    else:
        seven_start = thirty_start = date.min

    seven_complete = [
        row
        for row in daily
        if parse_date(row["date"], "daily date") >= seven_start
        and row["status"] == "completed"
    ]
    thirty_rows = [
        row
        for row in daily
        if parse_date(row["date"], "daily date") >= thirty_start
    ]
    thirty_complete = [row for row in thirty_rows if row["status"] == "completed"]

    def total(rows: list[dict[str, Any]], field: str) -> int | None:
        if not rows:
            return None
        return sum(row[field] for row in rows)

    expected_source_runs = sum(row["expectedSourceCount"] for row in thirty_rows)
    completed_source_runs = sum(row["completedSourceCount"] for row in thirty_rows)
    all_complete = [row for row in daily if row["status"] == "completed"]
    return {
        "runDays": len(daily),
        "completedRuns": len(all_complete),
        "partialRuns": sum(row["status"] == "partial" for row in daily),
        "failedRuns": sum(row["status"] == "failed" for row in daily),
        "lastRunStatus": daily[-1]["status"] if daily else None,
        "last7Days": {
            "completedRuns": len(seven_complete),
            "uniqueResults": total(seven_complete, "uniqueResults"),
            "knownMatches": total(seven_complete, "knownMatches"),
            "newCandidates": total(seven_complete, "intakeCandidates"),
        },
        "last30Days": {
            "loggedRuns": len(thirty_rows),
            "completedRuns": len(thirty_complete),
            "partialRuns": sum(row["status"] == "partial" for row in thirty_rows),
            "failedRuns": sum(row["status"] == "failed" for row in thirty_rows),
            "sourceCompletionRate": safe_rate(completed_source_runs, expected_source_runs),
            "uniqueResults": total(thirty_complete, "uniqueResults"),
            "knownMatches": total(thirty_complete, "knownMatches"),
            "newCandidates": total(thirty_complete, "intakeCandidates"),
            "metadataConflicts": total(thirty_complete, "metadataConflicts"),
        },
        "allTime": {"newCandidates": total(all_complete, "intakeCandidates")},
    }
