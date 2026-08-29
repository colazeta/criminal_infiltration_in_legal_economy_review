#!/usr/bin/env python3
"""Evaluate recorded execution metrics against the documented stop rule."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CONSECUTIVE_CYCLES = 3


def rate(value: str) -> float | None:
    value = (value or "").strip()
    if not value or value.upper() == "NA":
        return None
    return float(value)


def main() -> None:
    path = ROOT / "data/registry/execution_metrics.csv"
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    assessable = [
        row
        for row in rows
        if row.get("execution_id") != "E0"
        and rate(row.get("eligible_increment_rate", "")) is not None
        and rate(row.get("screening_yield", "")) is not None
    ]
    qualifying = []
    for row in assessable:
        no_new_codes = all(
            (row.get(field, "").strip() in {"0", "0.0"})
            for field in (
                "new_theme_codes",
                "new_sector_codes",
                "new_mechanism_codes",
                "new_method_codes",
            )
        )
        qualifying.append(
            rate(row["eligible_increment_rate"]) < 0.02
            and rate(row["screening_yield"]) < 0.02
            and no_new_codes
        )

    trailing = 0
    for value in reversed(qualifying):
        if not value:
            break
        trailing += 1
    if trailing >= REQUIRED_CONSECUTIVE_CYCLES:
        print(
            f"[REVIEW REQUIRED] Numeric stop conditions hold for {trailing} "
            "consecutive assessable cycles; retrieval failures and frontier "
            "coverage still require reviewer confirmation."
        )
    else:
        print(
            "[NOT SATURATED] "
            f"{len(assessable)} assessable cycle(s); {trailing} consecutive "
            f"cycle(s) meet the numeric rule, {REQUIRED_CONSECUTIVE_CYCLES} required."
        )


if __name__ == "__main__":
    main()
