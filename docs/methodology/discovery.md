# Discovery and citation-searching protocol

## Execution types

- **E0:** precision-first seed construction.
- **E1:** database/API or approved scholarly-search update.
- **E2:** backward citation searching.
- **E3:** forward citation searching.

A review cycle consists of one completed E1, E2 and E3 execution over the
eligible frontier. The Work automation is a surveillance intake channel, not a
replacement for this auditable cycle.

The complete coverage design, workstreams, benchmark calibration, provider
roles and first-expansion checklist are in the
[literature expansion strategy](expansion.md).

## Required execution record

Record the execution/cycle ID, date, component, operator or automation, source
and platform, exact strategy, limits/filters, coverage dates, result count,
unique count, raw snapshot/checksum when retained, request status/errors,
screening status and notes. Store every occurrence as a discovery event even
when the work is already known.

## Source-specific behaviour

- Use the syntax and pagination model of each provider; never send one generic
  Boolean string to every API.
- Distinguish zero hits, an inaccessible source, a parse failure and a rate limit.
- Preserve identifiers and provenance before deduplication.
- Never classify scope from title keywords alone.
- Never discard later discovery occurrences after a duplicate match.

## Candidate intake

Automated or manual searches create candidate IDs, never canonical `paper_id`s.
Deduplicate by normalised DOI, then stable source identifier, then normalised
title/year. Similar titles are only possible-duplicate flags. DOI/title conflicts
must be reviewed, not merged automatically.

The controlled Work flow is in [the automation runbook](../operations/automation.md).
Authorised providers are in [the source registry](../governance/sources.md).
