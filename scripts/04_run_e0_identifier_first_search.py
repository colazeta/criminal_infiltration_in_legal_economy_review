#!/usr/bin/env python3
"""Disabled legacy E0 retrieval entry point.

The former implementation ignored source assignments, discarded available
abstracts and converted network failures into empty results. Re-running it would
create scientifically misleading candidate data. Source-specific, logged adapters
must replace it before any new production retrieval.
"""

raise SystemExit(
    "Disabled unsafe legacy retrieval. Implement the source-specific E1 adapters "
    "described in docs/NEXT_ACTION.md before running bibliographic discovery."
)
