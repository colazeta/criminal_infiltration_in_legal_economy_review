# Discovery calibration

Phase A of the expansion protocol uses two deliberately separate calibration instruments.

## Retrieval benchmark

`discovery-benchmark.json` contains works already present in governed repository evidence and is used to test whether formal-search query families recover expected literature. `evaluate_discovery_benchmark.py` reports benchmark recovery. The number is a **sensitivity/calibration proxy**, not an estimate of the total recall of the literature and not evidence of saturation.

The configured formal-search set currently reaches the minimum calibration size of 20 records. That threshold makes the proxy usable for comparing query families; it does not make the underlying set a statistically representative sample of all relevant literature.

## Near-neighbour benchmark

`discovery-near-neighbours.json` contains adjacent phenomena that can resemble infiltration in search results: money laundering, procurement/corruption risk, passive investment and asset conversion, corporate governance/crime, facilitation, and external crime effects on firms.

Membership is not an exclusion decision. Each record carries a `guard_question` asking whether the missing relational element is actually present in the full work. `evaluate_near_neighbours.py` reports how many of these boundary records a query retrieves. A high hit share is a prompt to inspect conceptual drift or query breadth, not a false-positive rate.

## Use in formal cycles

For each principal query family:

1. save or convert the returned result metadata to a JSON array containing at least DOI or title/year where available;
2. run the combined calibration preflight on that exact result set;
3. record benchmark misses, near-neighbour hits, provider indexing limits and any query revision in the cycle issue;
4. revise terminology when a known benchmark is missed for an explainable reason, but never inject benchmark titles as hidden search shortcuts;
5. send retrieved records through normal deduplication and human screening regardless of calibration membership.

Run repository-internal calibration tools as Python modules from the repository root so package imports resolve identically in local runs and CI.

The formal-cycle default is:

```text
python -m scripts.metrics.calibrate_cycle_results \
  --results cycle-results.json \
  --require-interpretable-benchmark \
  --output cycle-calibration.json
```

The combined output contains both the positive benchmark recovery report and the near-neighbour drift report, plus explicit lists of benchmark misses and boundary hits that require methodological review. It is intended to be attached or transcribed into the formal cycle audit record.

The lower-level evaluators remain available for debugging a single instrument:

```text
python -m scripts.metrics.evaluate_discovery_benchmark --results cycle-results.json
python -m scripts.metrics.evaluate_near_neighbours --results cycle-results.json
```

None of these tools changes the corpus, queue, eligibility state, canonical identity, publication state or formal saturation metrics. Calibration output is methodological evidence about the search strategy, not a scientific decision about any retrieved work.
