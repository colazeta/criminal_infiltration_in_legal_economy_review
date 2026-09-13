#!/usr/bin/env python3
"""Read the governed surveillance ledger with audited recovery handling.

Historical terminal comments that were proven invalid remain on GitHub for audit
but are excluded by exact comment ID and batch ID.  A single audited replacement
terminal is allowed to cross the Rome-calendar-day boundary created by recovery.

Candidate identity collisions across *different* valid intake runs are discovery
occurrences, not ledger-corruption events.  The operational register reconciles
those exact collisions when materialising a batch.  Consequently this wrapper
keeps every other canonical ledger validation but disables only the base reader's
cross-run candidate-novelty assertion.  Batch identity, issue identity, immutable
terminal timing, source/query counts, repository ancestry and intake contents
remain fail-closed.

For intake materialisation, ``fetch_validated_run_for_intake`` validates only the
terminal belonging to the target issue.  An unrelated malformed terminal must not
prevent a valid target batch from being staged; a malformed or duplicated target
terminal still fails immediately.
"""

from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError

import fetch_surveillance_ledger as _base
from scripts.surveillance_identity import validate_cycle_run


QUARANTINED_LEDGER_COMMENTS = {
    5631393628: "ACADEMIC-2026-09-11-EXTRA-2520dfa54e12",
    5639689529: "ACADEMIC-2026-09-11-EXTRA-f28583e91573",
    5633517951: "ACADEMIC-2026-09-11-EXTRA-61e4d03af5c4",
    5641872719: "ACADEMIC-2026-09-12-EXTRA-724679219793",
    5643146365: "ACADEMIC-2026-09-12-EXTRA-4faa0ba491c4",
    5643786921: "ACADEMIC-2026-09-12-EXTRA-9bdb3c1e67c7",
    5644330070: "ACADEMIC-2026-09-12-EXTRA-d6b0ffff25fd",
    5644553677: "ACADEMIC-2026-09-12-EXTRA-335f7df7ae34",
    5646294694: "ACADEMIC-2026-09-12-EXTRA-570dae192194",
}

# These batches are not merely superseded malformed terminals: the audited run
# itself must never be materialised because it repeated already-known candidate
# identities rather than representing a valid new intake batch.
PERMANENTLY_QUARANTINED_BATCHES = {
    "ACADEMIC-2026-09-11-EXTRA-2520dfa54e12",
    "ACADEMIC-2026-09-11-EXTRA-f28583e91573",
}

LATE_RECOVERY_TERMINALS = {
    5647832949: {
        "batch_id": "ACADEMIC-2026-09-11-EXTRA-61e4d03af5c4",
        "run_date": "2026-09-11",
        "created_rome_date": "2026-09-12",
    }
}

_RAW_API_GET = _base.api_get
_RAW_VERIFY_LEDGER_COMMENT_TIME = _base.verify_ledger_comment_time
_LEDGER_BATCH_CLAIM = re.compile(
    rf"\ADaily surveillance batch (?P<batch>{_base.BATCH_PATTERN}): "
)


def _quarantine_api_get(url: str, token: str):
    payload, links = _RAW_API_GET(url, token)
    if isinstance(payload, list) and "/issues/30/comments" in url:
        kept = []
        for item in payload:
            comment_id = item.get("id") if isinstance(item, dict) else None
            expected_batch = QUARANTINED_LEDGER_COMMENTS.get(comment_id)
            if expected_batch is None:
                kept.append(item)
                continue
            body = str(item.get("body") or "")
            if expected_batch not in body:
                raise _base.MetricsError(
                    "quarantined ledger comment identity disagrees with recovery record"
                )
        payload = kept
    return payload, links


def _verify_ledger_comment_time_with_recovery(run: dict, comment: dict) -> None:
    recovery = LATE_RECOVERY_TERMINALS.get(comment.get("id"))
    if recovery is None:
        _RAW_VERIFY_LEDGER_COMMENT_TIME(run, comment)
        return

    if run.get("batch_id") != recovery["batch_id"] or run.get("run_date") != recovery["run_date"]:
        raise _base.MetricsError("late recovery terminal identity disagrees with recovery record")

    created = _base.parse_datetime(comment.get("created_at"), "ledger comment.created_at")
    updated = _base.parse_datetime(comment.get("updated_at"), "ledger comment.updated_at")
    ended = _base.parse_datetime(run.get("window_end"), "run.window_end")
    created_rome_date = created.astimezone(_base.ROME).date().isoformat()
    if (
        created != updated
        or created < ended
        or created_rome_date != recovery["created_rome_date"]
    ):
        raise _base.MetricsError(
            "late recovery terminal timestamps disagree with audited recovery record"
        )


def _occurrence_keys(_candidate: dict) -> set:
    """Do not turn rediscovery across valid runs into a ledger-integrity error."""
    return set()


def fetch_validated_runs(repository, ledger_issue, allowed_author, token, cycle=None):
    """Run canonical validation after exact recovery/occurrence handling."""
    original_api = _base.api_get
    original_time = _base.verify_ledger_comment_time
    original_keys = _base.candidate_keys
    _base.api_get = _quarantine_api_get
    _base.verify_ledger_comment_time = _verify_ledger_comment_time_with_recovery
    _base.candidate_keys = _occurrence_keys
    try:
        return _base.fetch_validated_runs(
            repository, ledger_issue, allowed_author, token, cycle
        )
    finally:
        _base.api_get = original_api
        _base.verify_ledger_comment_time = original_time
        _base.candidate_keys = original_keys


def _target_batch(issue: dict) -> str:
    title = str(issue.get("title") or "")
    prefix = f"{_base.INTAKE_TITLE_PREFIX} "
    if not title.startswith(prefix):
        raise _base.MetricsError("target issue is not an academic intake")
    batch_id = title[len(prefix):].strip()
    if not re.fullmatch(_base.BATCH_PATTERN, batch_id):
        raise _base.MetricsError("target intake batch identity is invalid")
    return batch_id


def _comment_claims_batch(body: str, batch_id: str) -> bool:
    """Return whether malformed ledger evidence claims exactly ``batch_id``.

    Ordinary daily batch IDs are prefixes of same-day ``-EXTRA-`` batch IDs.  A
    substring test therefore turns a malformed EXTRA terminal into a false error
    for the ordinary batch.  Prefer the immutable ledger summary identity and use
    an exact JSON ``batch_id`` field only as a fail-closed fallback when the
    summary itself is malformed.
    """
    text = body.strip()
    summary = _LEDGER_BATCH_CLAIM.match(text)
    if summary is not None:
        return summary.group("batch") == batch_id
    return (
        re.search(
            rf'"batch_id"\s*:\s*"{re.escape(batch_id)}"',
            text,
        )
        is not None
    )


def fetch_validated_run_for_intake(
    repository: str,
    ledger_issue: int,
    allowed_author,
    token: str,
    cycle: dict | None,
    issue: dict,
) -> dict | None:
    """Validate only the authenticated terminal belonging to ``issue``.

    The function deliberately ignores malformed terminals for unrelated batches.
    If a malformed comment claims the target batch, or more than one valid target
    terminal survives audited quarantine, materialisation fails closed.
    """
    batch_id = _target_batch(issue)
    if batch_id in PERMANENTLY_QUARANTINED_BATCHES:
        raise _base.MetricsError("target intake batch is permanently quarantined")

    allowed_authors = set(allowed_author)
    url = (
        f"https://api.github.com/repos/{repository}/issues/"
        f"{ledger_issue}/comments?per_page=100"
    )
    matches: list[dict] = []
    while url:
        page, links = _quarantine_api_get(url, token)
        if not isinstance(page, list):
            raise _base.MetricsError("GitHub comments response is not a list")
        for comment in page:
            author = ((comment.get("user") or {}).get("login") or "").strip()
            if author not in allowed_authors:
                continue
            body = str(comment.get("body") or "")
            try:
                run = _base.extract_run(body)
            except _base.MetricsError:
                if _comment_claims_batch(body, batch_id):
                    raise
                continue
            if run is None or run.get("batch_id") != batch_id:
                continue
            if cycle:
                try:
                    validate_cycle_run(run, cycle)
                except ValueError as exc:
                    raise _base.MetricsError("target run belongs to the retired archive cycle") from exc
            _verify_ledger_comment_time_with_recovery(run, comment)
            matches.append(run)
        url = _base.next_link(links)

    if not matches:
        return None
    if len(matches) != 1:
        raise _base.MetricsError("target intake has more than one validated terminal")
    run = matches[0]
    if run.get("status") != "completed":
        raise _base.MetricsError("target intake terminal is not completed")
    intake = run.get("intake_issue") or {}
    if intake.get("number") != issue.get("number") or not intake.get("created"):
        raise _base.MetricsError("target terminal does not identify this intake issue")

    # Preserve the canonical uniqueness check for the *target issue identity*.
    repository_issues: list[dict] = []
    issues_url = f"https://api.github.com/repos/{repository}/issues?state=all&per_page=100"
    while issues_url:
        page, links = _RAW_API_GET(issues_url, token)
        if not isinstance(page, list):
            raise _base.MetricsError("GitHub issues response is not a list")
        repository_issues.extend(page)
        issues_url = _base.next_link(links)
    _base.verify_intake_issue_uniqueness(run, repository_issues)

    comparison, _ = _RAW_API_GET(
        f"https://api.github.com/repos/{repository}/compare/{run['repository_commit']}...main",
        token,
    )
    if not isinstance(comparison, dict):
        raise _base.MetricsError("GitHub commit comparison response is not an object")
    _base.verify_repository_commit(run, comparison)
    _base.verify_intake_issue(run, issue, allowed_authors, ledger_issue)
    return run


api_get = _base.api_get
verify_intake_issue = _base.verify_intake_issue
extract_run = _base.extract_run


def main() -> None:
    original_api = _base.api_get
    original_time = _base.verify_ledger_comment_time
    original_keys = _base.candidate_keys
    _base.api_get = _quarantine_api_get
    _base.verify_ledger_comment_time = _verify_ledger_comment_time_with_recovery
    _base.candidate_keys = _occurrence_keys
    try:
        _base.main()
    finally:
        _base.api_get = original_api
        _base.verify_ledger_comment_time = original_time
        _base.candidate_keys = original_keys


if __name__ == "__main__":
    try:
        main()
    except (HTTPError, URLError, _base.MetricsError, json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"[FAIL] {exc}") from exc
