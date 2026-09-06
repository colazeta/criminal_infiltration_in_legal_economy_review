# Verified abstract source bridge

The curator has two deliberately different evidence layers:

1. the bulk zero-cost abstract cascade, which attempts to detect abstract text mechanically;
2. targeted assisted retrieval, which can verify an exact publisher, repository or scholarly page even when the bulk cascade cannot extract the text.

A record marked `verified_abstract_source` in the effective reading-aid registry means that an exact source has been inspected and that the source exposes an abstract or equivalent substantive abstract field. This is stronger than `publisher_summary`, `full_text_intro` or `review_synopsis`.

`scripts/abstracts/promote_verified_sources.mjs` bridges that verified source state into `data/curation/abstract_coverage.csv` after the ordinary bulk backfill and its deterministic check have completed.

The bridge may change only `needs_web_search` to `available`. It records the verified source label and URL, uses `match_type=verified_abstract_source`, and does not persist abstract text. Reading-aid overrides take precedence over base aids, so a later targeted search can upgrade or downgrade the effective source classification without silently changing eligibility.

This bridge is non-decisional. It does not decide eligibility, publication, duplicate status, canonical metadata or whether a chapter belongs in the core review. A verified abstract source answers only the narrower retrieval question: a reliable abstract-bearing source for this exact work has been located.
