#!/usr/bin/env python3
"""Reconcile audited E0 ``import_now`` records with canonical registries.

This command is intentionally check-only. It never promotes records. A missing
canonical import must be prepared as a reviewed registry patch that adds the
work, its discovery event and its current screening decision together.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def doi(value: str) -> str:
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value or "", flags=re.I).lower()


def main() -> None:
    audited = rows(ROOT / "data/raw/e0_seed_promotion_staging_audited.csv")
    papers = rows(ROOT / "data/registry/papers.csv")
    events = rows(ROOT / "data/registry/discovery_events.csv")
    decisions = rows(ROOT / "data/registry/screening_decisions.csv")

    ready = [row for row in audited if row.get("pre_import_decision") == "import_now"]
    paper_by_doi = {doi(row.get("doi", "")): row for row in papers if row.get("doi")}
    event_papers = {row.get("paper_id") for row in events}
    current_decision_papers = {
        row.get("paper_id")
        for row in decisions
        if row.get("is_current", "").lower() == "true"
    }

    problems: list[str] = []
    for row in ready:
        canonical = paper_by_doi.get(doi(row.get("doi", "")))
        if not canonical:
            problems.append(f"{row['seed_id']}: missing canonical paper")
            continue
        paper_id = canonical["paper_id"]
        if paper_id not in event_papers:
            problems.append(f"{row['seed_id']}: {paper_id} has no discovery event")
        if paper_id not in current_decision_papers:
            problems.append(f"{row['seed_id']}: {paper_id} has no current decision")

    if problems:
        for problem in problems:
            print(f"[FAIL] {problem}")
        raise SystemExit(1)
    print(f"[OK] {len(ready)} audited import_now record(s) are canonical and traceable.")


if __name__ == "__main__":
    main()
