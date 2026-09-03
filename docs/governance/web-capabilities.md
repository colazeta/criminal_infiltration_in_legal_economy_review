# Web capability governance

The project treats web browsing as a hierarchy of bounded capabilities, not as a flat list of search vendors.

The normative inventory is [`ontology/providers/web-capabilities.json`](../../ontology/providers/web-capabilities.json). The ontology extension is [`ontology/modules/web-retrieval.json`](../../ontology/modules/web-retrieval.json). Runtime execution is implemented by `curator-app/src/web-capability-resolver.js`.

## Decision rule

For each unresolved opened candidate, choose the **lowest-layer sufficient implemented capability** that is automatically eligible under the zero-spend policy.

A provider can be:

- **registered** — useful capability/free tier is documented;
- **implemented** — a tested adapter exists;
- **configured** — its free-only runtime guard and required credential/binding are present;
- **automaticEligible** — it is implemented, configured and explicitly allowed to run automatically.

Only the last state authorises a request.

## Current hierarchy

`resolved document → Jina Reader → SERP discovery → Tavily/semantic search → rendered browser → agentic research → assisted browsing handoff`

The current automatic subset is intentionally smaller:

`Jina Reader (guarded) → Tavily Basic (guarded) → STOP`

Serper, Exa, Firecrawl and Cloudflare Browser Run are registered to preserve the capability roadmap, but their automatic adapters are disabled until the project can prove zero-spend execution independently of account billing state.

## Non-negotiable safeguards

1. Queue cards never consume web-browsing quota.
2. A web invocation requires an opened authenticated candidate and occurs after scholarly/resolved-document fallbacks.
3. No provider may silently fall through to a paid tier, paid balance, x402, auto-reload or advanced endpoint.
4. Provider failure or quota exhaustion produces a review state (`needs_web_search` / `web_search_exhausted`), not a paid retry.
5. Every invocation records provider, capability, requests/credits used and errors in the runtime response.
6. Provider discovery metadata and runtime implementation must stay aligned through regression tests.
7. Adding an automatic provider requires updating the provider registry, ontology module, zero-cost tests and operational documentation in the same reviewed change.

## Why providers with free credit can remain disabled

A free allowance alone is not sufficient. If an account can later contain paid credit, auto-reload, or an unbounded billing route, the project cannot infer from the existence of a free tier that an automatic request is zero-cost. Such providers remain available for future integration but `automatic_allowed=false` until a hard stop exists.

This deliberately favours a missed automatic retrieval over monetary liability.
