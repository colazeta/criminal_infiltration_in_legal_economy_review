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

## Current automatic hierarchy

The selected-paper path is:

`resolved document → Jina Reader → Serper discovery → Jina Reader → Exa Search → Jina Reader → Tavily Basic → STOP`

The important distinction is between **discovery** and **reading**:

- Jina Reader reads a known public manifestation and detects an explicit abstract section;
- Serper performs one bounded SERP query and returns only candidate URLs;
- Exa performs Search API discovery only (`type=fast`, `category=research paper`, at most five results) and returns only candidate URLs;
- Jina Reader then reads a Serper/Exa-discovered public URL and validates its title before accepting an abstract;
- Tavily Basic remains the final content-bearing web-search fallback.

No Serper/Exa Contents, Deep Search, Agent, crawl, x402 or paid extraction capability is in the automatic path.

Firecrawl and Cloudflare Browser Run remain registered but `automatic_allowed=false` pending a separate hard free-plan boundary.

## Persistent project budgets

A provider free tier is not enough by itself. Credit-priced automatic providers also require a **persistent project-side budget** stored in the existing Cloudflare Durable Object namespace.

The current hard caps are deliberately below the verified free grants:

- **Serper:** at most 1,000 automatic project requests for this budget namespace, versus a verified 2,500-query signup free grant;
- **Exa Search:** at most 500 automatic project Search requests. At the verified $7 / 1,000 Search price, that is a maximum theoretical $3.50 of API credit, below the verified $20 initial Starter Free credit.

The budget is reserved **before** the external request. Once the project cap is exhausted, the provider request is not issued.

Automatic Serper/Exa execution additionally requires an explicit production attestation:

- `SERPER_DEDICATED_FREE_ACCOUNT=true` means the configured key belongs to the dedicated project free account and no purchased top-up is intended for project use;
- `EXA_DEDICATED_STARTER_ACCOUNT=true` means the configured key belongs to the dedicated Starter Free project account with no payment method intended for project use.

A key without that attestation remains `guarded` and cannot run automatically.

## Non-negotiable safeguards

1. Queue cards never consume web-browsing quota.
2. A web invocation requires an opened authenticated candidate and occurs after scholarly/resolved-document fallbacks.
3. No provider may silently fall through to a paid tier, paid balance, x402, auto-reload, Deep/Agent or advanced endpoint.
4. Provider failure, project-budget exhaustion or provider free-balance exhaustion produces a review state (`needs_web_search` / `web_search_exhausted`), not a paid retry.
5. Every invocation records provider, capability, quota unit, requests/free quota used and, where applicable, project-budget state.
6. Provider discovery metadata and runtime implementation must stay aligned through regression tests.
7. Adding or widening an automatic provider requires updating the provider registry, ontology module, zero-cost tests and operational documentation in the same reviewed change.
8. Persistent budget limits must never be increased merely because a provider account has paid balance.

## Why the project cap matters

Provider account state can change outside the repository. A project-owned persistent cap gives us a second boundary that does not depend on a vendor dashboard remaining unchanged. The dedicated-account guard then makes that cap meaningful by requiring the configured key to be associated with the intended free account.

This deliberately favours a missed automatic retrieval over monetary liability.
