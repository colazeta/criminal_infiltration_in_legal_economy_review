# Multi-source abstract discovery

Abstract retrieval is a separate mechanical aid to curator screening. It must not infer eligibility and it must not persist abstract text into the public corpus.

## Core rule

`Abstract absent` is not a valid early-stage outcome.

The curator may only conclude that an abstract was not found after the available provider registry and resolved-paper manifestations have been searched. When the automated web-search provider is not configured, the result is `needs_web_search`, not absence.

## Provider registry

The runtime abstract resolver uses the following layers:

1. OpenAlex;
2. Crossref;
3. Semantic Scholar Academic Graph;
4. DataCite metadata, including `descriptions` with `descriptionType=Abstract`;
5. Europe PMC core records when relevant;
6. Exa web search in `publication` mode when `EXA_API_KEY` is configured;
7. the already governed paper/repository/full-text URLs from `Retrieval coverage — mechanical`.

The provider registry is deliberately extensible. Adding another source must produce the same normalized result fields: provider, abstract, article URL, matched title/year/DOI, match type and match score.

## Web browsing handoff

A record that remains unresolved after the structured providers and resolved-paper layer is **not** labelled as having no abstract when Exa/web search is unavailable. The runtime returns `needs_web_search` and the curator UI shows `Ricerca web necessaria`.

That state is the explicit handoff for an assisted browsing pass using connected Exa and general web search. Search should use exact title first, DOI when available, author/year disambiguation, and should inspect publisher pages, institutional repositories, preprints, working-paper repositories and other credible manifestations.

If Exa is configured in the Worker and the web-search pass completes without an abstract, the state is `web_search_exhausted`. This still means `not found`, not `does not exist`.

## Match discipline

- DOI matches are preferred when exact.
- Title/year matches must clear provider-specific similarity thresholds.
- Exa/web results require a strong exact-title match before extracted text can be shown.
- Resolved URLs are candidate-bound and come only from the governed retrieval record; the browser cannot submit arbitrary fetch targets.
- Private/local literal-IP targets are rejected by the resolved-paper fetcher.

## Provenance

Runtime responses expose `providersTried`, `providerErrors`, `provider`, `matchType`, `matchScore` and `searchStatus`. The UI surfaces the source and provider trace so the curator can distinguish a verified abstract from an unfinished search.

## Credentials

- `OPENALEX_API_KEY`: optional, improves OpenAlex allowance.
- `SEMANTIC_SCHOLAR_API_KEY`: optional, recommended for sustained Semantic Scholar use.
- `EXA_API_KEY`: optional but required for automated Exa web search inside the Worker.

If `EXA_API_KEY` is absent, deployment remains valid and unresolved records are routed to `needs_web_search` rather than silently downgraded to abstract absence.
