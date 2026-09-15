#!/usr/bin/env python3
"""Validate and render stateful discovery-identity resolution records.

CILE-IDENTITY-RESOLUTION-2 distinguishes a provider observation from a
provider-independent bibliographic identity and validates append-only state
transitions. It is bibliographic/operational only: no scientific eligibility,
canonical ScholarlyWork merge, source-rights or publication decision is made.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "CILE-IDENTITY-RESOLUTION-2"
MARKER = "<!-- cile-identity-resolution:2 -->"
STATUSES = {"pending", "forwarded_to_intake", "resolved"}
OUTCOMES = {
    "known_exact_work",
    "known_work_new_manifestation",
    "new_candidate",
    "not_forwarded",
}
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
CANDIDATE_RE = re.compile(r"^CAND-[A-Z0-9][A-Z0-9._-]*$", re.IGNORECASE)
QUERY_RE = re.compile(r"^(?:PARALLEL|EXA)-W[1-7]-Q[1-9][0-9]*$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


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


def normalise_doi(value: Any) -> str:
    doi = clean(value).lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi.rstrip(" .")


def normalise_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", clean(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _sha(parts: list[str]) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def observation_key(item: dict[str, Any]) -> str:
    """Key one provider observation/manifestation, not the underlying work."""
    return _sha([
        clean(item.get("provider")).lower(),
        normalise_doi(item.get("doi")),
        normalise_text(item.get("title")),
        clean(item.get("year")),
        clean(item.get("url")),
    ])


def identity_key(item: dict[str, Any]) -> tuple[str, str]:
    """Return a conservative provider-independent bibliographic grouping key."""
    doi = normalise_doi(item.get("doi"))
    if doi:
        return _sha(["doi", doi]), "doi"
    authors = [normalise_text(x) for x in item.get("authors", []) if normalise_text(x)]
    title = normalise_text(item.get("title"))
    year = clean(item.get("year"))
    basis = "title_year_authors" if authors else "title_year"
    return _sha([basis, title, year, "|".join(authors)]), basis


def load_candidate_ids(root: Path) -> set[str]:
    path = root / "data" / "curation" / "review_queue.csv"
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return {clean(row.get("candidate_id")) for row in reader if clean(row.get("candidate_id"))}


def validate_item(raw: Any, common: dict[str, Any], candidate_ids: set[str] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise IdentityResolutionProtocolError("item must be an object")
    title = require_text(raw.get("title"), "title", 500)
    url = require_text(raw.get("url"), "url", 2000)
    if not url.startswith("https://"):
        raise IdentityResolutionProtocolError("url must be https")
    doi = optional_text(raw.get("doi"), "doi", 300)
    if doi:
        doi = normalise_doi(doi)
        if not DOI_RE.fullmatch(doi):
            raise IdentityResolutionProtocolError("invalid DOI")
    year = raw.get("year")
    if year is not None and (not isinstance(year, int) or year < 1500 or year > 2100):
        raise IdentityResolutionProtocolError("year must be null or a plausible integer")
    authors_raw = raw.get("authors", [])
    if not isinstance(authors_raw, list) or not all(isinstance(x, str) and clean(x) for x in authors_raw):
        raise IdentityResolutionProtocolError("authors must be an array of non-empty strings")
    authors = [clean(x)[:300] for x in authors_raw]
    query_ids = raw.get("source_query_ids")
    if not isinstance(query_ids, list) or not query_ids or not all(isinstance(x, str) and QUERY_RE.fullmatch(x) for x in query_ids):
        raise IdentityResolutionProtocolError("source_query_ids must contain governed W1-W7 query ids")
    if len(set(query_ids)) != len(query_ids):
        raise IdentityResolutionProtocolError("source_query_ids contains duplicates")

    status = clean(raw.get("status"))
    if status not in STATUSES:
        raise IdentityResolutionProtocolError("invalid status")
    outcome = optional_text(raw.get("outcome"), "outcome", 64)
    candidate_id = optional_text(raw.get("candidate_id"), "candidate_id", 200)
    rationale = require_text(raw.get("rationale"), "rationale", 1000)

    if status == "pending":
        if outcome or candidate_id:
            raise IdentityResolutionProtocolError("pending identity cannot have outcome/candidate_id")
    elif status == "forwarded_to_intake":
        if outcome or candidate_id:
            raise IdentityResolutionProtocolError("forwarded_to_intake cannot pre-claim outcome/candidate_id")
    else:
        if outcome not in OUTCOMES:
            raise IdentityResolutionProtocolError("resolved identity has invalid outcome")
        if outcome in {"known_exact_work", "known_work_new_manifestation", "new_candidate"}:
            if not candidate_id or not CANDIDATE_RE.fullmatch(candidate_id):
                raise IdentityResolutionProtocolError("resolved known/new outcome requires CandidateRecord id")
            if candidate_ids is not None and candidate_id not in candidate_ids:
                raise IdentityResolutionProtocolError("resolved outcome references an absent CandidateRecord")
        elif candidate_id:
            raise IdentityResolutionProtocolError("not_forwarded must not carry candidate_id")

    item = {
        "protocol": PROTOCOL,
        "cycle_id": common["cycle_id"],
        "batch_id": common["batch_id"],
        "attempt": common["attempt"],
        "provider": common["provider"],
        "observed_at": common["observed_at"],
        "observation_key": "",
        "identity_key": "",
        "identity_basis": "",
        "title": title,
        "authors": authors,
        "url": url,
        "doi": doi,
        "year": year,
        "source_query_ids": query_ids,
        "status": status,
        "outcome": outcome,
        "candidate_id": candidate_id,
        "rationale": rationale,
    }
    item["observation_key"] = observation_key(item)
    item["identity_key"], item["identity_basis"] = identity_key(item)
    explicit_observation = optional_text(raw.get("observation_key"), "observation_key", 64)
    explicit_identity = optional_text(raw.get("identity_key"), "identity_key", 64)
    if explicit_observation and (not HEX64_RE.fullmatch(explicit_observation) or explicit_observation != item["observation_key"]):
        raise IdentityResolutionProtocolError("observation_key disagrees with observation")
    if explicit_identity and (not HEX64_RE.fullmatch(explicit_identity) or explicit_identity != item["identity_key"]):
        raise IdentityResolutionProtocolError("identity_key disagrees with bibliographic identity")
    return item


def validate(payload: Any, candidate_ids: set[str] | None = None) -> list[dict[str, Any]]:
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
    validated = [validate_item(item, common, candidate_ids) for item in items]
    keys = [item["observation_key"] for item in validated]
    if len(keys) != len(set(keys)):
        raise IdentityResolutionProtocolError("duplicate observation_key in one payload")
    return validated


def canonical_record(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_transition(previous: dict[str, Any] | None, current: dict[str, Any]) -> None:
    """Validate append-only state for one provider observation."""
    if previous is None:
        if current["status"] != "pending":
            raise IdentityResolutionProtocolError("first observation record must be pending")
        return
    if previous["observation_key"] != current["observation_key"]:
        raise IdentityResolutionProtocolError("transition observation_key mismatch")
    if previous["identity_key"] != current["identity_key"]:
        raise IdentityResolutionProtocolError("transition identity_key mismatch")
    if previous["status"] == "resolved":
        if canonical_record(previous) != canonical_record(current):
            raise IdentityResolutionProtocolError("resolved observation is terminal and immutable")
        return
    if previous["status"] == "pending":
        if current["status"] not in {"forwarded_to_intake", "resolved"}:
            raise IdentityResolutionProtocolError("pending may transition only to forwarded_to_intake or resolved")
        return
    if previous["status"] == "forwarded_to_intake":
        if current["status"] != "resolved" or current.get("outcome") != "new_candidate":
            raise IdentityResolutionProtocolError("forwarded_to_intake may resolve only as new_candidate")
        return
    raise IdentityResolutionProtocolError("unsupported prior state")


def reduce_history(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Reduce already validated records to the current state per observation."""
    state: dict[str, dict[str, Any]] = {}
    for record in records:
        key = clean(record.get("observation_key"))
        if not HEX64_RE.fullmatch(key):
            raise IdentityResolutionProtocolError("history record has invalid observation_key")
        previous = state.get(key)
        validate_transition(previous, record)
        state[key] = record
    return state


def validate_against_history(history: list[dict[str, Any]], new_items: list[dict[str, Any]]) -> None:
    state = reduce_history(history)
    for item in new_items:
        validate_transition(state.get(item["observation_key"]), item)
        state[item["observation_key"]] = item


def render_comments(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    comments: list[dict[str, str]] = []
    for item in items:
        canonical = canonical_record(item)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        envelope = {"record_id": digest, "sha256": digest, "content": canonical}
        comments.append({
            "observation_key": item["observation_key"],
            "identity_key": item["identity_key"],
            "status": item["status"],
            "body": MARKER + "\n```json\n" + json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n```",
        })
    return comments


def parse_history(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(x, dict) for x in payload):
        raise IdentityResolutionProtocolError("history must be a JSON array of canonical records")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--history", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidate_ids = load_candidate_ids(args.root.resolve())
    items = validate(json.loads(args.input.read_text(encoding="utf-8")), candidate_ids)
    history = parse_history(args.history)
    validate_against_history(history, items)
    rendered = json.dumps({"protocol": PROTOCOL, "comments": render_comments(items)}, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, csv.Error, json.JSONDecodeError, IdentityResolutionProtocolError) as exc:
        raise SystemExit(f"[IDENTITY RESOLUTION V2 BLOCKED] {exc}") from exc
