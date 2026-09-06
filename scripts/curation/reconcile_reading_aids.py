#!/usr/bin/env python3
"""Keep reading aids exactly aligned with candidates still needing web abstract search.

Existing manually researched aids are preserved. Source-grounded overrides may be
prepared ahead of an intake. For a newly staged daily candidate without an
override, the governed intake relevance synopsis is used as an explicitly
non-author review synopsis. No eligibility or publication decision is inferred.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = ROOT / "data" / "curation" / "review_queue.csv"
ABSTRACT_PATH = ROOT / "data" / "curation" / "abstract_coverage.csv"
AIDS_PATH = ROOT / "data" / "curation" / "reading_aids.json"
OVERRIDES_PATH = ROOT / "config" / "curation" / "intake-reading-aid-overrides.json"


class ReadingAidError(ValueError):
    pass


def clean(value: object, limit: int = 2000) -> str:
    return " ".join(str(value or "").split())[:limit]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_json_records(path: Path, required: bool = True) -> list[dict[str, str]]:
    if not path.exists():
        if required:
            raise ReadingAidError(f"missing file: {path.relative_to(ROOT)}")
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != 1 or not isinstance(payload.get("records"), list):
        raise ReadingAidError(f"unsupported schema: {path.relative_to(ROOT)}")
    return [dict(record) for record in payload["records"]]


def index_unique(records: list[dict[str, str]], field: str, label: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for record in records:
        key = clean(record.get(field, ""), 100)
        if not key or key in result:
            raise ReadingAidError(f"{label} IDs are missing or duplicated")
        result[key] = record
    return result


def validate_aid(record: dict[str, str], candidate_id: str) -> dict[str, str]:
    kind = clean(record.get("kind", ""), 100)
    source_label = clean(record.get("sourceLabel", ""), 300)
    source_url = clean(record.get("sourceUrl", ""), 1000)
    synopsis = clean(record.get("synopsis", ""), 1500)
    note = clean(record.get("note", ""), 1000)
    checked_at = clean(record.get("checkedAt", ""), 20)
    if not all((kind, source_label, source_url, synopsis, note, checked_at)):
        raise ReadingAidError(f"reading aid {candidate_id} is incomplete")
    if not source_url.startswith("https://"):
        raise ReadingAidError(f"reading aid {candidate_id} requires an HTTPS source")
    return {
        "candidateId": candidate_id,
        "kind": kind,
        "sourceLabel": source_label,
        "sourceUrl": source_url,
        "synopsis": synopsis,
        "checkedAt": checked_at,
        "note": note,
    }


def first_https_source(value: str) -> str:
    for part in str(value or "").split(";"):
        url = part.strip()
        if url.startswith("https://"):
            return url
    return ""


def fallback_from_queue(row: dict[str, str], checked_at: str) -> dict[str, str]:
    candidate_id = row["candidate_id"]
    source_url = first_https_source(row.get("source_links", ""))
    synopsis = clean(row.get("intake_reason", ""), 1500)
    source_label = clean(row.get("source", ""), 300) or "Governed intake provenance"
    if row.get("origin") != "daily_surveillance" or not source_url or not synopsis:
        raise ReadingAidError(
            f"unresolved candidate {candidate_id} requires a researched reading aid; "
            "automatic fallback is allowed only for a source-grounded daily intake"
        )
    return {
        "candidateId": candidate_id,
        "kind": "review_synopsis",
        "sourceLabel": f"{source_label} intake evidence",
        "sourceUrl": source_url,
        "synopsis": synopsis,
        "checkedAt": checked_at,
        "note": (
            "Source-grounded intake synopsis used because the mechanical cascade did not expose "
            "a standalone abstract. Verify the linked scholarly source before screening; this is "
            "not an author abstract and cannot determine eligibility."
        ),
    }


def reconcile(checked_at: str) -> dict[str, int]:
    queue = index_unique(load_csv(QUEUE_PATH), "candidate_id", "queue")
    abstract_rows = index_unique(load_csv(ABSTRACT_PATH), "candidate_id", "abstract coverage")
    if set(queue) != set(abstract_rows):
        raise ReadingAidError("abstract coverage is not one-to-one with the queue")

    unresolved = {
        candidate_id
        for candidate_id, row in abstract_rows.items()
        if row.get("coverage_status") == "needs_web_search"
    }
    current = index_unique(load_json_records(AIDS_PATH), "candidateId", "reading aid")
    overrides = index_unique(
        load_json_records(OVERRIDES_PATH, required=False), "candidateId", "reading aid override"
    )

    output: list[dict[str, str]] = []
    preserved = added_override = added_fallback = removed = 0
    for candidate_id in sorted(unresolved):
        if candidate_id in current:
            output.append(validate_aid(current[candidate_id], candidate_id))
            preserved += 1
            continue
        if candidate_id in overrides:
            record = dict(overrides[candidate_id])
            record["checkedAt"] = checked_at
            output.append(validate_aid(record, candidate_id))
            added_override += 1
            continue
        output.append(validate_aid(fallback_from_queue(queue[candidate_id], checked_at), candidate_id))
        added_fallback += 1

    removed = len(set(current) - unresolved)
    payload = {
        "schemaVersion": 1,
        "purpose": (
            "Non-decisional curator reading aids for candidates whose mechanical abstract cascade "
            "did not expose a standalone abstract. These records store only short paraphrased "
            "synopses and source locators; they do not replace the source, screening, or a human decision."
        ),
        "records": output,
    }
    AIDS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "unresolved": len(unresolved),
        "preserved": preserved,
        "added_override": added_override,
        "added_fallback": added_fallback,
        "removed_stale": removed,
    }


def check() -> dict[str, int]:
    queue = index_unique(load_csv(QUEUE_PATH), "candidate_id", "queue")
    abstract_rows = index_unique(load_csv(ABSTRACT_PATH), "candidate_id", "abstract coverage")
    aids = index_unique(load_json_records(AIDS_PATH), "candidateId", "reading aid")
    if set(queue) != set(abstract_rows):
        raise ReadingAidError("abstract coverage is not one-to-one with the queue")
    unresolved = {
        candidate_id
        for candidate_id, row in abstract_rows.items()
        if row.get("coverage_status") == "needs_web_search"
    }
    if unresolved != set(aids):
        raise ReadingAidError("reading aids are not one-to-one with unresolved abstract coverage")
    for candidate_id, record in aids.items():
        validate_aid(record, candidate_id)
    return {"unresolved": len(unresolved), "reading_aids": len(aids)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(check(), sort_keys=True))
        return
    if not args.date:
        raise SystemExit("--date is required unless --check is used")
    print(json.dumps(reconcile(args.date), sort_keys=True))


if __name__ == "__main__":
    main()
