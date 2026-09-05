#!/usr/bin/env python3
"""Evaluate search-result coverage against a non-decisional calibration set."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


def normalise_doi(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text)
    return text.rstrip(" .")


def normalise_title(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char)).lower()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def candidate_year(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    return year if 1800 <= year <= 2200 else None


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def result_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("results"), list):
        rows = payload["results"]
    else:
        raise ValueError("results must be a JSON array or an object containing a results array")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("every result must be an object")
    return rows


def benchmark_records(payload: Any, calibration_use: str) -> tuple[list[dict[str, Any]], int]:
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("unsupported benchmark schema")
    records = payload.get("records")
    minimum = payload.get("minimum_interpretable_size")
    if not isinstance(records, list) or not isinstance(minimum, int) or minimum < 1:
        raise ValueError("invalid benchmark")
    selected = [
        row
        for row in records
        if isinstance(row, dict)
        and calibration_use in row.get("calibration_uses", [])
    ]
    return selected, minimum


def matched(record: dict[str, Any], rows: list[dict[str, Any]]) -> bool:
    expected_doi = normalise_doi(record.get("doi"))
    expected_title = normalise_title(record.get("title"))
    expected_year = candidate_year(record.get("year"))
    for row in rows:
        observed_doi = normalise_doi(row.get("doi") or row.get("DOI"))
        if expected_doi and observed_doi and expected_doi == observed_doi:
            return True
        observed_title = normalise_title(row.get("title") or row.get("display_name"))
        observed_year = candidate_year(row.get("year") or row.get("publication_year"))
        if expected_title and observed_title == expected_title and expected_year == observed_year:
            return True
    return False


def evaluate(benchmark: Any, results: Any, calibration_use: str) -> dict[str, Any]:
    records, minimum = benchmark_records(benchmark, calibration_use)
    rows = result_rows(results)
    recovered = [record["benchmark_id"] for record in records if matched(record, rows)]
    missed = [record["benchmark_id"] for record in records if record["benchmark_id"] not in recovered]
    size = len(records)
    proxy_recall = len(recovered) / size if size else None
    interpretable = size >= minimum
    return {
        "schema_version": 1,
        "calibration_use": calibration_use,
        "benchmark_size": size,
        "minimum_interpretable_size": minimum,
        "recovered": len(recovered),
        "missed": len(missed),
        "proxy_recall": proxy_recall if interpretable else None,
        "raw_recovery_share": proxy_recall,
        "interpretable": interpretable,
        "recovered_ids": recovered,
        "missed_ids": missed,
        "interpretation": (
            "Calibration proxy only; it is not a formal saturation or completeness estimate."
            if interpretable
            else "Bootstrap calibration only; benchmark is below the minimum size for an interpretable recall proxy."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=Path("docs/methodology/discovery-benchmark.json"),
    )
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--calibration-use", default="formal_search")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = evaluate(load_json(args.benchmark), load_json(args.results), args.calibration_use)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
