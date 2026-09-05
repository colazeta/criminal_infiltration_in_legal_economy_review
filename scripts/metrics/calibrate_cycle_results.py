#!/usr/bin/env python3
"""Run both discovery-calibration instruments on one formal-cycle result set.

This preflight is diagnostic only. It cannot alter screening, canonical identity,
publication state or saturation metrics.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.metrics.evaluate_discovery_benchmark import evaluate as evaluate_benchmark
from scripts.metrics.evaluate_discovery_benchmark import load_json
from scripts.metrics.evaluate_near_neighbours import evaluate as evaluate_near_neighbours


def calibrate(
    results_payload: object,
    benchmark_payload: object,
    near_neighbour_payload: object,
    *,
    calibration_use: str = "formal_search",
) -> dict[str, object]:
    positive = evaluate_benchmark(benchmark_payload, results_payload, calibration_use)
    boundary = evaluate_near_neighbours(near_neighbour_payload, results_payload)
    return {
        "schema_version": 1,
        "calibration_use": calibration_use,
        "benchmark": positive,
        "near_neighbours": boundary,
        "review_required": {
            "benchmark_misses": positive["missed_ids"],
            "near_neighbour_hits": boundary["hit_ids"],
        },
        "interpretation": (
            "Formal-cycle search calibration only. Benchmark recovery is a sensitivity proxy and "
            "near-neighbour retrieval is a conceptual-drift diagnostic. Neither is an eligibility, "
            "precision, completeness or saturation decision."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=Path("docs/methodology/discovery-benchmark.json"),
    )
    parser.add_argument(
        "--near-neighbours",
        type=Path,
        default=Path("docs/methodology/discovery-near-neighbours.json"),
    )
    parser.add_argument("--calibration-use", default="formal_search")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--require-interpretable-benchmark",
        action="store_true",
        help="Fail if the selected positive benchmark is below its configured minimum size.",
    )
    args = parser.parse_args()

    report = calibrate(
        load_json(args.results),
        load_json(args.benchmark),
        load_json(args.near_neighbours),
        calibration_use=args.calibration_use,
    )
    benchmark = report["benchmark"]
    if args.require_interpretable_benchmark and not benchmark["interpretable"]:
        raise SystemExit(
            "[CALIBRATION BLOCKED] positive benchmark is below the configured minimum interpretable size"
        )

    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
