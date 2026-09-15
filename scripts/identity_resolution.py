#!/usr/bin/env python3
"""Validate and render durable unresolved-identity queue/terminal comments.

The protocol is deliberately bibliographic and non-decisional. It may preserve an
unresolved discovery identity and later record its operational terminal outcome,
but it cannot decide scientific eligibility or canonical ScholarlyWork identity.
Resolved `new_candidate` outcomes must point to a CandidateRecord already created
through the normal governed intake path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


PROTOCOL = "CILE-IDENTITY-RESOLUTION-1"
MARKER = "<!-- cile-identity-resolution:1 -->"
PENDING = "pending"
OUTCOMES = {
    "known_exact_work",
    "known_work_new_manifestation",
    "new_candidate",
    "not_forwarded",
}
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
CANDIDATE_RE = re.compile(r"^CAND-[A-Z0-9][A-Z0-9._-]*$", re.IGNORECASE)
QUERY_RE = re.compile(r"^(?:PARALLEL|EXA)-W[1-7]-Q[1-9][0-9]*$")


class IdentityResolutionProtocolError(ValueError):
    pass


def clean(value: Any) -> str:
    return str(value or "").strip()


def require_text(value: Any, name: str, limit: int) -> str:
    text = clean(value)
    if not text or len(text) > limit:
        raise IdentityResolutionProtocolError(f"{name} must be 1..{limit} characters")
    return text


def optional_text(value: Any, name: str, limit: int) -> str | None:
    text = clean(value)
    if not text:
        return None
    if len(text) > limit:
        raise IdentityResolutionProtocolError(f"{name} exceeds {limit} characters")
    return text


def stable_key(item: dict[str, Any]) -> str:
    seed = "\x1f".join(
        [
            clean(item.get("provider")).lower(),
            clean(item.get("doi")).lower(),
            clean(item.get("title")).lower(),
            clean(item.get("year")),
            clean(item.get("url")),
        ]
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def validate_item(raw: Any, common: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise IdentityResolutionProtocolError("item must be an object")
    title = require_text(raw.get("title"), "title", 500)
    url = require_text(raw.get("url"), "url", 2000)
    if not url.startswith("https://"):
        raise IdentityResolutionProtocolError("url must be https")
    doi = optional_text(raw.get("doi"), "doi", 300)
    if doi and not DOI_RE.fullmatch(doi):
        raise IdentityResolutionProtocolError("invalid DOI")
    year = raw.get("year")
    if year is not None:
        if not isinstance(year, int) or year < 1500 or year > 2100:
            raise IdentityResolutionProtocolError("year must be null or a plausible integer")
    query_ids = raw.get("source_query_ids")
    if not isinstance(query_ids, list) or not query_ids or not all(isinstance(x, str) and QUERY_RE.fullmatch(x) for x in query_ids):
        raise IdentityResolutionProtocolError("source_query_ids must contain governed W1-W7 query ids")
    if len(set(query_ids)) != len(query_ids):
        raise IdentityResolutionProtocolError("source_query_ids contains duplicates")

    status = clean(raw.get("status"))
    outcome = optional_text(raw.get("outcome"), "outcome", 64)
    candidate_id = optional_text(raw.get("candidate_id"), "candidate_id", 200)
    rationale = require_text(raw.get("rationale"), "rationale", 1000)
    if status == PENDING:
        if outcome or candidate_id:
            raise IdentityResolutionProtocolError("pending identity cannot have outcome/candidate_id")
    elif status == "resolved":
        if outcome not in OUTCOMES:
            raise IdentityResolutionProtocolError("resolved identity has invalid outcome")
        if outcome in {"known_exact_work", "known_work_new_manifestation", "new_candidate"}:
            if not candidate_id or not CANDIDATE_RE.fullmatch(candidate_id):
                raise IdentityResolutionProtocolError("resolved known/new outcome requires CandidateRecord id")
        elif candidate_id:
            raise IdentityResolutionProtocolError("not_forwarded must not carry candidate_id")
    else:
        raise IdentityResolutionProtocolError("status must be pending or resolved")

    item = {
        "protocol": PROTOCOL,
        "cycle_id": common["cycle_id"],
        "batch_id": common["batch_id"],
        "attempt": common["attempt"],
        "provider": common["provider"],
        "observed_at": common["observed_at"],
        "identity_key": "",
        "title": title,
        "url": url,
        "doi": doi,
        "year": year,
        "source_query_ids": query_ids,
        "status": status,
        "outcome": outcome,
        "candidate_id": candidate_id,
        "rationale": rationale,
    }
    item["identity_key"] = stable_key(item)
    explicit_key = optional_text(raw.get("identity_key"), "identity_key", 64)
    if explicit_key and explicit_key != item["identity_key"]:
        raise IdentityResolutionProtocolError("identity_key disagrees with bibliographic identity")
    return item


def validate(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise IdentityResolutionProtocolError("payload must be an object")
    if clean(payload.get("protocol")) != PROTOCOL:
        raise IdentityResolutionProtocolError(f"protocol must be {PROTOCOL}")
    common = {
        "cycle_id": require_text(payload.get("cycle_id"), "cycle_id", 100),
        "batch_id": require_text(payload.get("batch_id"), "batch_id", 160),
        "provider": require_text(payload.get("provider"), "provider", 100),
        "observed_at": require_text(payload.get("observed_at"), "observed_at", 80),
    }
    attempt = payload.get("attempt")
    if not isinstance(attempt, int) or attempt < 1:
        raise IdentityResolutionProtocolError("attempt must be a positive integer")
    common["attempt"] = attempt
    items = payload.get("items")
    if not isinstance(items, list) or not items or len(items) > 100:
        raise IdentityResolutionProtocolError("items must contain 1..100 identities")
    validated = [validate_item(item, common) for item in items]
    keys = [item["identity_key"] for item in validated]
    if len(keys) != len(set(keys)):
        raise IdentityResolutionProtocolError("duplicate identity_key in one payload")
    return validated


def render_comments(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    comments: list[dict[str, str]] = []
    for item in items:
        canonical = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        envelope = {
            "record_id": digest,
            "sha256": digest,
            "content": canonical,
        }
        comments.append(
            {
                "identity_key": item["identity_key"],
                "status": item["status"],
                "body": MARKER + "\n```json\n" + json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n```",
            }
        )
    return comments


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    comments = render_comments(validate(payload))
    rendered = json.dumps({"protocol": PROTOCOL, "comments": comments}, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, IdentityResolutionProtocolError) as exc:
        raise SystemExit(f"[IDENTITY RESOLUTION PROTOCOL BLOCKED] {exc}") from exc
