#!/usr/bin/env python3
"""Overlay curator-assisted abstract availability onto the mechanical coverage ledger.

The evidence file stores only provenance and source URLs, never abstract text.
"""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COVERAGE = ROOT / "data" / "curation" / "abstract_coverage.csv"
EVIDENCE = ROOT / "data" / "curation" / "abstract_assisted_evidence.csv"


def rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def main() -> None:
    coverage = rows(COVERAGE)
    evidence = rows(EVIDENCE)
    if not evidence:
        print("No assisted abstract evidence to apply.")
        return

    by_candidate = {row["candidate_id"]: row for row in evidence}
    updated = 0
    for row in coverage:
        assisted = by_candidate.get(row.get("candidate_id", ""))
        if not assisted:
            continue
        if assisted.get("title", "") != row.get("title", ""):
            raise SystemExit(f"Assisted evidence title mismatch for {row.get('candidate_id')}")
        if assisted.get("coverage_status") != "available":
            raise SystemExit(f"Unsupported assisted coverage status for {row.get('candidate_id')}")
        if not assisted.get("abstract_source") or not assisted.get("article_url"):
            raise SystemExit(f"Incomplete assisted evidence for {row.get('candidate_id')}")
        row.update(
            coverage_status="available",
            abstract_source=assisted["abstract_source"],
            article_url=assisted["article_url"],
            providers_tried="assisted free web research",
            match_type=assisted.get("match_type") or "assisted_web",
            match_score=assisted.get("match_score") or "1",
            provider_errors="",
            checked_at=assisted.get("checked_at") or row.get("checked_at", ""),
            notes=(
                "Abstract availability confirmed by assisted free web research; "
                "only provenance and source URL are persisted, never abstract text."
            ),
        )
        updated += 1

    missing = sorted(set(by_candidate) - {row.get("candidate_id", "") for row in coverage})
    if missing:
        raise SystemExit(f"Assisted evidence references candidates outside the queue: {', '.join(missing)}")

    if not coverage:
        raise SystemExit("Abstract coverage ledger is missing")
    fieldnames = list(coverage[0].keys())
    if "abstract" in fieldnames or "abstract_text" in fieldnames:
        raise SystemExit("Abstract text must not be persisted")
    with COVERAGE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(coverage)
    print(f"Applied assisted abstract evidence to {updated} candidate(s).")


if __name__ == "__main__":
    main()
