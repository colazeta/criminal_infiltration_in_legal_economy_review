# Curator reading surface

The authenticated curator enriches candidate cards for review without changing the governed public corpus.

## Bibliographic view

A selected candidate presents the recorded title, authors, year, venue, DOI/source metadata and a direct article action. The direct action prefers a verified bibliographic landing page or DOI and otherwise falls back to a recorded HTTPS source link.

## Abstract enrichment

The abstract is retrieved only after curator authentication. The Worker queries OpenAlex and Crossref, preferring a DOI match and falling back to a strict title/year match. Weak matches are rejected rather than displayed.

Returned abstract text is ephemeral: it is held only in the browser session memory, is not added to `review_queue.csv`, is not included in public site data and is not treated as canonical metadata. The UI identifies the enrichment source and match basis. If no reliable abstract is available, the card says so explicitly.

OpenAlex may be used without a key for basic access. If an `OPENALEX_API_KEY` Worker variable is configured later, the same endpoint can use it without exposing the key to the browser.

## Security boundary

`/api/enrichment` is served only by the isolated curator Worker. Before contacting bibliographic providers, the Worker validates the existing curator bearer through the same `/api/session` authority used by the rest of the console. GitHub Pages keeps `apiBaseUrl` empty and therefore cannot query the enrichment endpoint.

Production deployment smoke tests verify that the reading asset is served and that an unauthenticated enrichment request is rejected with HTTP 401.
