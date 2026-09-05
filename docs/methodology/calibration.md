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
2. run the retrieval benchmark evaluator;
3. run the near-neighbour evaluator on the same result set;
4. record benchmark misses, near-neighbour hits, provider indexing limits and any query revision in the cycle issue;
5. revise terminology when a known benchmark is missed for an explainable reason, but never inject benchmark titles as hidden search shortcuts;
6. send retrieved records through normal deduplication and human screening regardless of calibration membership.

Example:

```text
python scripts/metrics/evaluate_discovery_benchmark.py --results cycle-results.json
python scripts/metrics/evaluate_near_neighbours.py --results cycle-results.json
```

Neither evaluator changes the corpus, queue, eligibility state, canonical identity or publication state.
