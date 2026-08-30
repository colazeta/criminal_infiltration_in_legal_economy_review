#!/usr/bin/env python3
"""Fetch and validate aggregate surveillance comments from a GitHub issue."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from surveillance import (
    REPOSITORY_FULL_NAME,
    ROME,
    MetricsError,
    parse_datetime,
    validate_run,
)


MARKER = "<!-- surveillance-run:v1 -->"
LEDGER_COMMENT = re.compile(
    r"\ADaily surveillance batch "
    r"(?P<batch>ACADEMIC-[0-9]{4}-[0-9]{2}-[0-9]{2}): "
    r"(?P<status>completed|partial|failed)\.\n\n"
    + re.escape(MARKER)
    + r"\n```json\n(?P<payload>\{.*\})\n```\s*\Z",
    re.DOTALL,
)
INTAKE_TITLE_PREFIX = "[INTAKE][ACADEMIC]"
INTAKE_BODY_FIELDS = (
    "Batch ID",
    "Search and provenance log",
    "Candidate records",
    "Safeguards",
)
CANDIDATE_MANIFEST_FIELDS = {"schema_version", "batch_id", "candidates"}
CANDIDATE_RECORD_FIELDS = {
    "candidate_id",
    "title",
    "authors",
    "year",
    "venue",
    "work_type",
    "identifiers",
    "source_links",
    "sources",
    "query_ids",
    "verification_status",
    "possible_duplicate",
    "metadata_conflict",
    "intake_assessment",
    "relevance_reason",
    "required_human_action",
}
CANDIDATE_WORK_TYPES = {
    "peer_reviewed",
    "accepted_manuscript",
    "working_paper",
    "preprint",
    "other",
    "unknown",
}
CANDIDATE_VERIFICATION_STATUSES = {
    "metadata_verified",
    "metadata_partial",
    "identifier_unresolved",
}
CANDIDATE_ASSESSMENTS = {"plausible_core", "plausible_contextual", "uncertain"}
CANDIDATE_JSON_BLOCK = re.compile(r"\A```json\s*(\{.*\})\s*```\s*\Z", re.DOTALL)
SEARCH_MANIFEST_FIELDS = {"schema_version", "batch_id", "repository_commit", "sources"}
SEARCH_SOURCE_FIELDS = {"source", "queries"}
SEARCH_QUERY_FIELDS = {"query_id", "query_text"}
SEARCH_JSON_BLOCK = re.compile(r"\A```json\s*(\{.*\})\s*```\s*\Z", re.DOTALL)
REQUIRED_SAFEGUARDS = (
    "No candidate was marked eligible or published.",
    "Canonical records and existing intake issues were checked for duplicates.",
    "No copyrighted full text or long abstract is included.",
)


def api_get(url: str, token: str) -> tuple[object, str | None]:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "criminal-infiltration-research-metrics",
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return payload, response.headers.get("Link")


def next_link(value: str | None) -> str | None:
    if not value:
        return None
    for part in value.split(","):
        match = re.match(r'\s*<([^>]+)>;\s*rel="([^"]+)"', part)
        if match and match.group(2) == "next":
            return match.group(1)
    return None


def extract_run(body: str) -> dict | None:
    if MARKER not in body:
        return None
    if body.count(MARKER) != 1:
        raise MetricsError("Marked ledger comment must use the canonical envelope")
    match = LEDGER_COMMENT.fullmatch(body.strip())
    if not match:
        raise MetricsError("Marked ledger comment must use the canonical envelope")
    try:
        payload = json.loads(match.group("payload"))
    except json.JSONDecodeError as exc:
        raise MetricsError("Marked ledger comment contains invalid JSON") from exc
    run = validate_run(payload)
    if match.group("batch") != run["batch_id"] or match.group("status") != run["status"]:
        raise MetricsError("Marked ledger comment summary disagrees with payload")
    return run


def issue_form_value(body: str, label: str) -> str | None:
    """Return the first non-empty value under one GitHub issue-form heading."""
    pattern = re.compile(
        rf"(?m)^###\s+{re.escape(label)}\s*$\n+(?P<value>.*?)(?=^###\s+|\Z)",
        re.DOTALL,
    )
    matches = list(pattern.finditer(body.replace("\r\n", "\n")))
    if len(matches) != 1:
        return None
    value = matches[0].group("value").strip()
    return value or None


def required_text(value: object, label: str, max_length: int = 500) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > max_length:
        raise MetricsError(f"{label}: expected non-empty text up to {max_length} characters")
    return value.strip()


def optional_text(value: object, label: str, max_length: int = 500) -> str | None:
    if value is None:
        return None
    return required_text(value, label, max_length)


def text_list(
    value: object,
    label: str,
    *,
    minimum: int,
    maximum: int,
    item_length: int = 500,
) -> list[str]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise MetricsError(f"{label}: expected {minimum} to {maximum} text values")
    result = [required_text(item, f"{label}[]", item_length) for item in value]
    if len(result) != len(set(result)):
        raise MetricsError(f"{label}: duplicate values are not allowed")
    return result


def verify_search_manifest(run: dict, section: str) -> dict[str, str]:
    """Validate the exact queries and bind their IDs to governed sources."""
    match = SEARCH_JSON_BLOCK.fullmatch(section.strip())
    if not match:
        raise MetricsError("run.intake_issue: Search log must be one JSON object")
    try:
        manifest = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise MetricsError("run.intake_issue: Search log JSON is invalid") from exc
    if not isinstance(manifest, dict) or set(manifest) != SEARCH_MANIFEST_FIELDS:
        raise MetricsError("run.intake_issue: Search log manifest fields are invalid")
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["batch_id"] != run["batch_id"]
        or manifest["repository_commit"] != run["repository_commit"]
    ):
        raise MetricsError("run.intake_issue: Search log provenance disagrees with run")

    sources = manifest["sources"]
    if not isinstance(sources, list) or len(sources) != len(run["sources"]):
        raise MetricsError("run.intake_issue: Search log source set is incomplete")
    run_sources = {row["source"]: row for row in run["sources"]}
    seen_sources: set[str] = set()
    query_sources: dict[str, str] = {}
    for index, source in enumerate(sources):
        label = f"run.intake_issue.search.sources[{index}]"
        if not isinstance(source, dict) or set(source) != SEARCH_SOURCE_FIELDS:
            raise MetricsError(f"{label}: invalid fields")
        source_name = source["source"]
        if source_name not in run_sources or source_name in seen_sources:
            raise MetricsError(f"{label}.source: unexpected or duplicate source")
        seen_sources.add(source_name)
        queries = source["queries"]
        planned = run_sources[source_name]["queries_planned"]
        if not isinstance(queries, list) or len(queries) != planned:
            raise MetricsError(f"{label}.queries: count disagrees with planned queries")
        prefix = "CONSENSUS" if source_name == "Consensus" else "EXA"
        for query_index, query in enumerate(queries):
            query_label = f"{label}.queries[{query_index}]"
            if not isinstance(query, dict) or set(query) != SEARCH_QUERY_FIELDS:
                raise MetricsError(f"{query_label}: invalid fields")
            query_id = required_text(query["query_id"], f"{query_label}.query_id", 80)
            if not re.fullmatch(rf"{prefix}-[A-Z0-9][A-Z0-9._-]*", query_id):
                raise MetricsError(f"{query_label}.query_id: invalid source-scoped ID")
            if query_id in query_sources:
                raise MetricsError("run.intake_issue: search query IDs must be unique")
            required_text(query["query_text"], f"{query_label}.query_text", 2000)
            query_sources[query_id] = source_name
    if seen_sources != set(run_sources):
        raise MetricsError("run.intake_issue: Search log source set is incomplete")
    return query_sources


def verify_candidate_manifest(
    run: dict, section: str, query_sources: dict[str, str]
) -> None:
    """Require one structured candidate object for every persisted intake count."""
    match = CANDIDATE_JSON_BLOCK.fullmatch(section.strip())
    if not match:
        raise MetricsError("run.intake_issue: Candidate records must be one JSON object")
    try:
        manifest = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise MetricsError("run.intake_issue: Candidate records JSON is invalid") from exc
    if not isinstance(manifest, dict) or set(manifest) != CANDIDATE_MANIFEST_FIELDS:
        raise MetricsError("run.intake_issue: Candidate records manifest fields are invalid")
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["batch_id"] != run["batch_id"]
    ):
        raise MetricsError("run.intake_issue: Candidate records manifest batch is invalid")
    candidates = manifest["candidates"]
    expected_count = run["totals"]["intake_candidates"]
    if not isinstance(candidates, list) or len(candidates) != expected_count:
        raise MetricsError("run.intake_issue: persisted candidate count disagrees with run")

    candidate_ids: list[str] = []
    assessment_counts = {value: 0 for value in CANDIDATE_ASSESSMENTS}
    source_hits = {value: 0 for value in ("Consensus", "Exa")}
    source_exclusives = {value: 0 for value in ("Consensus", "Exa")}
    duplicate_notes = 0
    conflict_notes = 0
    expected_id = re.compile(rf"CAND-{re.escape(run['batch_id'])}-[0-9]{{3}}")
    for index, candidate in enumerate(candidates):
        label = f"run.intake_issue.candidates[{index}]"
        if not isinstance(candidate, dict) or set(candidate) != CANDIDATE_RECORD_FIELDS:
            raise MetricsError(f"{label}: candidate record fields are invalid")
        candidate_id = required_text(candidate["candidate_id"], f"{label}.candidate_id", 80)
        if not expected_id.fullmatch(candidate_id):
            raise MetricsError(f"{label}.candidate_id: invalid batch-scoped ID")
        candidate_ids.append(candidate_id)
        required_text(candidate["title"], f"{label}.title", 500)
        text_list(candidate["authors"], f"{label}.authors", minimum=1, maximum=50)
        year = candidate["year"]
        if year is not None and (
            isinstance(year, bool)
            or not isinstance(year, int)
            or not 1800 <= year <= int(run["run_date"][:4]) + 1
        ):
            raise MetricsError(f"{label}.year: invalid publication year")
        optional_text(candidate["venue"], f"{label}.venue", 300)
        if (
            not isinstance(candidate["work_type"], str)
            or candidate["work_type"] not in CANDIDATE_WORK_TYPES
        ):
            raise MetricsError(f"{label}.work_type: invalid value")
        identifiers = candidate["identifiers"]
        if not isinstance(identifiers, dict) or set(identifiers) != {"doi", "other"}:
            raise MetricsError(f"{label}.identifiers: invalid fields")
        optional_text(identifiers["doi"], f"{label}.identifiers.doi", 200)
        text_list(
            identifiers["other"],
            f"{label}.identifiers.other",
            minimum=0,
            maximum=20,
            item_length=200,
        )
        links = text_list(
            candidate["source_links"],
            f"{label}.source_links",
            minimum=1,
            maximum=20,
            item_length=1000,
        )
        if any(
            urlsplit(link).scheme not in {"http", "https"}
            or not urlsplit(link).netloc
            for link in links
        ):
            raise MetricsError(f"{label}.source_links: invalid URL")
        sources = text_list(
            candidate["sources"], f"{label}.sources", minimum=1, maximum=2, item_length=40
        )
        if not set(sources).issubset({"Consensus", "Exa"}):
            raise MetricsError(f"{label}.sources: source is not governed")
        for source in sources:
            source_hits[source] += 1
        if len(sources) == 1:
            source_exclusives[sources[0]] += 1
        query_ids = text_list(
            candidate["query_ids"],
            f"{label}.query_ids",
            minimum=1,
            maximum=20,
            item_length=80,
        )
        if any(query_id not in query_sources for query_id in query_ids):
            raise MetricsError(f"{label}.query_ids: query is absent from Search log")
        if {query_sources[query_id] for query_id in query_ids} != set(sources):
            raise MetricsError(f"{label}.query_ids: query sources disagree with candidate")
        if (
            not isinstance(candidate["verification_status"], str)
            or candidate["verification_status"]
            not in CANDIDATE_VERIFICATION_STATUSES
        ):
            raise MetricsError(f"{label}.verification_status: invalid value")
        optional_text(candidate["possible_duplicate"], f"{label}.possible_duplicate", 500)
        optional_text(candidate["metadata_conflict"], f"{label}.metadata_conflict", 500)
        duplicate_notes += candidate["possible_duplicate"] is not None
        conflict_notes += candidate["metadata_conflict"] is not None
        if (
            not isinstance(candidate["intake_assessment"], str)
            or candidate["intake_assessment"] not in CANDIDATE_ASSESSMENTS
        ):
            raise MetricsError(f"{label}.intake_assessment: invalid value")
        assessment_counts[candidate["intake_assessment"]] += 1
        required_text(candidate["relevance_reason"], f"{label}.relevance_reason", 1000)
        required_text(
            candidate["required_human_action"], f"{label}.required_human_action", 500
        )
    if len(candidate_ids) != len(set(candidate_ids)):
        raise MetricsError("run.intake_issue: candidate IDs must be unique")
    if assessment_counts != run["assessments"]:
        raise MetricsError("run.intake_issue: persisted assessments disagree with run")
    for source in run["sources"]:
        source_name = source["source"]
        if source_hits[source_name] != source["candidate_hits"]:
            raise MetricsError("run.intake_issue: persisted source hits disagree with run")
        if source_exclusives[source_name] != source["exclusive_candidates"]:
            raise MetricsError("run.intake_issue: persisted source exclusives disagree with run")
    if duplicate_notes > run["totals"]["possible_duplicate_flags"]:
        raise MetricsError("run.intake_issue: persisted duplicate notes exceed run flags")
    if conflict_notes > run["totals"]["metadata_conflicts"]:
        raise MetricsError("run.intake_issue: persisted conflict notes exceed run flags")


def verify_safeguards(section: str) -> None:
    """Require every governed issue-form safeguard to be explicitly checked."""
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    if len(lines) != len(REQUIRED_SAFEGUARDS):
        raise MetricsError(
            "run.intake_issue: safeguards must contain exactly three confirmations"
        )
    for safeguard in REQUIRED_SAFEGUARDS:
        pattern = re.compile(rf"- \[[xX]\] {re.escape(safeguard)}")
        if sum(pattern.fullmatch(line) is not None for line in lines) != 1:
            raise MetricsError(
                "run.intake_issue: every required safeguard must be checked exactly once"
            )


def verify_repository_commit(run: dict, comparison: dict) -> None:
    """Require the recorded registry revision to remain on main's history."""
    repository_commit = run["repository_commit"]
    base_commit = comparison.get("base_commit")
    merge_base_commit = comparison.get("merge_base_commit")
    if (
        comparison.get("status") not in {"ahead", "identical"}
        or not isinstance(base_commit, dict)
        or base_commit.get("sha") != repository_commit
        or not isinstance(merge_base_commit, dict)
        or merge_base_commit.get("sha") != repository_commit
    ):
        raise MetricsError(
            "run.repository_commit: commit is not an ancestor of governed main"
        )


def verify_ledger_comment_time(run: dict, comment: dict) -> None:
    """Bind the daily payload to a ledger comment created after that day's run."""
    created = parse_datetime(comment.get("created_at"), "ledger comment.created_at")
    ended = parse_datetime(run["window_end"], "run.window_end")
    if created < ended or created.astimezone(ROME).date().isoformat() != run["run_date"]:
        raise MetricsError(
            "ledger comment: creation time is incompatible with the daily run window"
        )


def verify_intake_issue(
    run: dict,
    issue: dict,
    allowed_authors: set[str],
    ledger_issue_number: int,
) -> None:
    """Bind a positive candidate count to its real, batch-specific intake issue."""
    intake = run["intake_issue"]
    if not intake["created"]:
        return

    number = intake["number"]
    batch_id = run["batch_id"]
    canonical_url = f"https://github.com/{REPOSITORY_FULL_NAME}/issues/{number}"
    if number == ledger_issue_number:
        raise MetricsError("run.intake_issue: metrics ledger cannot be an intake issue")
    if issue.get("pull_request") is not None:
        raise MetricsError("run.intake_issue: referenced object is a pull request")
    if issue.get("number") != number or issue.get("html_url") != canonical_url:
        raise MetricsError("run.intake_issue: fetched issue identity disagrees with run")
    user = issue.get("user")
    if not isinstance(user, dict):
        raise MetricsError("run.intake_issue: issue author is missing")
    author = (user.get("login") or "").strip()
    if author not in allowed_authors:
        raise MetricsError("run.intake_issue: issue author is not authorised")
    if issue.get("title") != f"{INTAKE_TITLE_PREFIX} {batch_id}":
        raise MetricsError("run.intake_issue: title does not identify this batch")
    issue_created = parse_datetime(issue.get("created_at"), "intake issue.created_at")
    started = parse_datetime(run["window_start"], "run.window_start")
    ended = parse_datetime(run["window_end"], "run.window_end")
    if not started <= issue_created <= ended:
        raise MetricsError("run.intake_issue: issue was not created during the run window")

    body = issue.get("body")
    if not isinstance(body, str):
        raise MetricsError("run.intake_issue: issue body is missing")
    values = {label: issue_form_value(body, label) for label in INTAKE_BODY_FIELDS}
    if any(value is None for value in values.values()):
        raise MetricsError("run.intake_issue: candidate-intake form is incomplete")
    if values["Batch ID"] != batch_id:
        raise MetricsError("run.intake_issue: issue batch ID disagrees with run")
    query_sources = verify_search_manifest(run, values["Search and provenance log"])
    verify_candidate_manifest(run, values["Candidate records"], query_sources)
    verify_safeguards(values["Safeguards"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--issue", required=True, type=int)
    parser.add_argument("--allowed-author", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    args = parser.parse_args()
    if args.repository != REPOSITORY_FULL_NAME:
        raise MetricsError("repository must match the governed repository")
    token = os.environ.get(args.token_env)
    if not token:
        raise MetricsError(f"Missing token environment variable {args.token_env}")

    url = (
        f"https://api.github.com/repos/{args.repository}/issues/"
        f"{args.issue}/comments?per_page=100"
    )
    comments: list[dict] = []
    while url:
        page, links = api_get(url, token)
        if not isinstance(page, list):
            raise MetricsError("GitHub comments response is not a list")
        comments.extend(page)
        url = next_link(links)

    runs = []
    intake_cache: dict[int, dict] = {}
    commit_cache: dict[str, dict] = {}
    allowed_authors = set(args.allowed_author)
    for comment in comments:
        body = comment.get("body") or ""
        if MARKER not in body:
            continue
        author = ((comment.get("user") or {}).get("login") or "").strip()
        if author not in allowed_authors:
            continue
        run = extract_run(body)
        if run is None:
            continue
        verify_ledger_comment_time(run, comment)
        repository_commit = run["repository_commit"]
        if repository_commit not in commit_cache:
            compare_url = (
                f"https://api.github.com/repos/{args.repository}/compare/"
                f"{repository_commit}...main"
            )
            comparison, _ = api_get(compare_url, token)
            if not isinstance(comparison, dict):
                raise MetricsError("GitHub commit comparison response is not an object")
            commit_cache[repository_commit] = comparison
        verify_repository_commit(run, commit_cache[repository_commit])
        intake = run["intake_issue"]
        if intake["created"]:
            number = intake["number"]
            if number not in intake_cache:
                issue_url = (
                    f"https://api.github.com/repos/{args.repository}/issues/{number}"
                )
                issue, _ = api_get(issue_url, token)
                if not isinstance(issue, dict):
                    raise MetricsError("GitHub intake issue response is not an object")
                intake_cache[number] = issue
            verify_intake_issue(run, intake_cache[number], allowed_authors, args.issue)
        runs.append(run)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"runs": runs}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Fetched {len(runs)} validated surveillance run(s) from issue #{args.issue}.")


if __name__ == "__main__":
    try:
        main()
    except (HTTPError, URLError, MetricsError, json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"[FAIL] {exc}") from exc
