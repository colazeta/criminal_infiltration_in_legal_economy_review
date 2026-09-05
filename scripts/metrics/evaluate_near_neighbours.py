#!/usr/bin/env python3
"""Measure retrieval pressure on conceptual near neighbours.

A near-neighbour hit is a query-calibration diagnostic. It is not a false
positive, an exclusion decision, or a precision estimate because each retrieved
work still requires the governed relational eligibility test.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.metrics.evaluate_discovery_benchmark import candidate_year, load_json, normalise_doi, normalise_title, result_rows


def records(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("unsupported near-neighbour schema")
    rows = payload.get("records")
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("near-neighbour records must be a non-empty array")
    return rows


def matched(record: dict[str, Any], results: list[dict[str, Any]]) -> bool:
    expected_doi = normalise_doi(record.get("doi"))
    expected_title = normalise_title(record.get("title"))
    expected_year = candidate_year(record.get("year"))
    for row in results:
        observed_doi = normalise_doi(row.get("doi") or row.get("DOI"))
        if expected_doi and observed_doi and expected_doi == observed_doi:
            return True
        observed_title = normalise_title(row.get("title") or row.get("display_name"))
        observed_year = candidate_year(row.get("year") or row.get("publication_year"))
        if expected_title and observed_title == expected_title:
            if expected_year is None or expected_year == observed_year:
                return True
    return False


def evaluate(near_neighbours: Any, results: Any) -> dict[str, Any]:
    neighbours = records(near_neighbours)
    rows = result_rows(results)
    hits = [record for record in neighbours if matched(record, rows)]
    by_phenomenon: dict[str, int] = {}
    for record in hits:
        phenomenon = str(record.get("phenomenon") or "unspecified")
        by_phenomenon[phenomenon] = by_phenomenon.get(phenomenon, 0) + 1
    return {
        "schema_version": 1,
        "near_neighbour_size": len(neighbours),
        "near_neighbour_hits": len(hits),
        "near_neighbour_hit_share": len(hits) / len(neighbours),
        "hit_ids": [record.get("benchmark_id") for record in hits],
        "hits_by_phenomenon": dict(sorted(by_phenomenon.items())),
        "interpretation": (
            "Conceptual-drift diagnostic only. A hit is not a false positive, exclusion decision, "
            "or precision estimate; inspect the relational infiltration evidence before screening."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--near-neighbours",
        type=Path,
        default=Path("docs/methodology/discovery-near-neighbours.json"),
    )
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(load_json(args.near_neighbours), load_json(args.results))
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
