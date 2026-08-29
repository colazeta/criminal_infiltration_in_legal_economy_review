#!/usr/bin/env python3
"""Detect canonical DOI and normalised-title/year collisions without mutation."""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def normalise_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def main() -> None:
    path = ROOT / "data/registry/papers.csv"
    with path.open(newline="", encoding="utf-8-sig") as handle:
        papers = list(csv.DictReader(handle))

    indices: dict[str, dict[str, list[str]]] = {
        "DOI": defaultdict(list),
        "title/year": defaultdict(list),
    }
    for row in papers:
        paper_id = row.get("paper_id", "")
        doi = row.get("doi", "").strip().lower()
        if doi:
            indices["DOI"][doi].append(paper_id)
        title_year = f"{normalise_title(row.get('title', ''))}|{row.get('year', '').strip()}"
        indices["title/year"][title_year].append(paper_id)

    collisions = []
    for label, index in indices.items():
        for key, paper_ids in index.items():
            if len(paper_ids) > 1:
                collisions.append(f"{label} {key!r}: {', '.join(paper_ids)}")
    if collisions:
        for collision in collisions:
            print(f"[FAIL] {collision}")
        raise SystemExit(1)
    print(f"[OK] No canonical collisions across {len(papers)} work(s).")


if __name__ == "__main__":
    main()
