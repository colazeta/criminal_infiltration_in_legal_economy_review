#!/usr/bin/env python3
"""Bridge curator-verified full-text reading aids into retrieval coverage.

This is a mechanical synchronisation layer. It does not infer open-access rights,
eligibility, canonical identity, or scientific conclusions. A reading aid is
eligible only when the curator override explicitly records `full_text_intro`, a
HTTPS final-source locator, and `Evidence basis: full_text` in its note.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
COVERAGE_PATH = ROOT / "data" / "curation" / "retrieval_coverage.csv"
OVERRIDES_PATH = ROOT / "data" / "curation" / "reading_aid_overrides.json"
SOURCE_LABEL = "Curator verified full text"
MATCH_LABEL = "reading_aid_override:full_text_intro"
NOTE = (
    "Curator-verified full-text locator synchronised from "
    "reading_aid_overrides.json; retrieval only, with no eligibility or "
    "canonicalisation decision."
)


class LocatorSyncError(ValueError):
    """Raised when the curated locator bridge cannot be applied safely."""


def safe_https(value: object) -> str:
    candidate = str(value or "").strip()
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return ""
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        return ""
    return candidate


def valid_date(value: object) -> str:
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise LocatorSyncError(f"invalid checkedAt date: {text!r}") from exc


def split_semicolon(value: object) -> list[str]:
    return [part.strip() for part in str(value or "").split(";") if part.strip()]


def append_unique(value: object, addition: str) -> str:
    parts = split_semicolon(value)
    addition_parts = split_semicolon(addition)
    if not addition_parts:
        return "; ".join(parts)
    width = len(addition_parts)
    if any(parts[index : index + width] == addition_parts for index in range(len(parts) - width + 1)):
        return "; ".join(parts)
    parts.extend(addition_parts)
    return "; ".join(parts)


def eligible_overrides(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != 1 or not isinstance(payload.get("records"), list):
        raise LocatorSyncError("reading aid overrides do not match schemaVersion 1")

    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for record in payload["records"]:
        if not isinstance(record, dict) or record.get("kind") != "full_text_intro":
            continue
        note = str(record.get("note") or "")
        if "Evidence basis: full_text" not in note:
            continue
        candidate_id = str(record.get("candidateId") or "").strip()
        source_url = safe_https(record.get("sourceUrl"))
        if not candidate_id or not source_url:
            raise LocatorSyncError("eligible full_text_intro override lacks candidateId or HTTPS sourceUrl")
        if candidate_id in seen:
            raise LocatorSyncError(f"duplicate eligible override for {candidate_id}")
        seen.add(candidate_id)
        result.append(
            {
                "candidate_id": candidate_id,
                "source_url": source_url,
                "checked_at": valid_date(record.get("checkedAt")),
            }
        )
    return result


def read_coverage(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    if not fieldnames or "candidate_id" not in fieldnames:
        raise LocatorSyncError("retrieval coverage is missing its governed header")
    ids = [row.get("candidate_id", "") for row in rows]
    if "" in ids or len(ids) != len(set(ids)):
        raise LocatorSyncError("retrieval coverage candidate IDs are invalid")
    return fieldnames, rows


def apply(coverage_path: Path, overrides_path: Path, *, check: bool = False) -> dict[str, int]:
    fieldnames, rows = read_coverage(coverage_path)
    by_id = {row["candidate_id"]: row for row in rows}
    curated = eligible_overrides(overrides_path)
    changed = 0

    for item in curated:
        candidate_id = item["candidate_id"]
        source_url = item["source_url"]
        row = by_id.get(candidate_id)
        if row is None:
            raise LocatorSyncError(f"{candidate_id}: override candidate is absent from retrieval coverage")

        if check:
            if row.get("resolution_status") != "full_text" or not safe_https(row.get("full_text_url")):
                raise LocatorSyncError(f"{candidate_id}: verified full-text locator is not represented as full_text")
            if source_url not in split_semicolon(row.get("source_urls")):
                raise LocatorSyncError(f"{candidate_id}: verified full-text locator is absent from source_urls")
            if SOURCE_LABEL not in split_semicolon(row.get("resolution_sources")):
                raise LocatorSyncError(f"{candidate_id}: verified locator provenance is absent")
            if MATCH_LABEL not in split_semicolon(row.get("match_method")):
                raise LocatorSyncError(f"{candidate_id}: verified locator match provenance is absent")
            continue

        before = dict(row)
        if row.get("resolution_status") != "full_text" or not safe_https(row.get("full_text_url")):
            row["resolution_status"] = "full_text"
            row["best_url"] = source_url
            row["best_url_kind"] = "full_text"
            row["full_text_url"] = source_url
        row["source_urls"] = append_unique(row.get("source_urls"), source_url)
        row["resolution_sources"] = append_unique(row.get("resolution_sources"), SOURCE_LABEL)
        row["match_method"] = append_unique(row.get("match_method"), MATCH_LABEL)
        row["match_confidence"] = "high"
        row["checked_at"] = max(str(row.get("checked_at") or ""), item["checked_at"])
        row["notes"] = append_unique(row.get("notes"), NOTE)
        if row != before:
            changed += 1

    if not check and changed:
        with coverage_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    return {"eligible_overrides": len(curated), "changed": changed}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage", type=Path, default=COVERAGE_PATH)
    parser.add_argument("--overrides", type=Path, default=OVERRIDES_PATH)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = apply(args.coverage, args.overrides, check=args.check)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
