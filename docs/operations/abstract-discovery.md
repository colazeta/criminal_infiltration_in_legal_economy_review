# Zero-cost multi-source abstract discovery

Abstract retrieval is a separate mechanical aid to curator screening. It must not infer eligibility and it must not persist abstract text into the public corpus.

## Core rule

`Abstract absent` is not a valid early-stage outcome, and automatic abstract discovery must not create monetary liability.

The resolver is a modular capability cascade rather than a flat provider list. Every provider declares a capability layer, credential policy, free allowance, spending risk and automatic-use policy. A provider may be **registered and discoverable** without being eligible for automatic execution.

## Execution order

The order is deliberately cost-, capability- and quota-aware:

1. **Primary free bibliographic lookup** — OpenAlex and Crossref.
2. **Free scholarly/repository registry** — Semantic Scholar, DataCite, optional Unpaywall, CORE and Europe PMC.
3. **Governed resolved-paper layer** — publisher, repository and full-text locators already bound to the candidate are inspected directly.
4. **Free known-URL reader** — Jina Reader may read the candidate DOI landing path when `JINA_READER_FREE_ONLY=true`; this layer consumes no search credit and runs before a search API.
5. **Free web search** — Tavily `basic` search, only for the selected unresolved paper and only when a free-plan key is configured with `TAVILY_FREE_ONLY=true`.
6. **Registered future capability layers** — SERP discovery, richer search, rendered browsing and agentic research providers are visible in the governed registry but remain disabled until their adapters can prove zero-spend execution.
7. **Assisted browsing handoff** — unresolved cases become `needs_web_search`. The resolver stops rather than consuming an ungoverned paid balance.

Queue cards never invoke the web-capability resolver. Web reading/search begins only after the curator opens one candidate and cheaper scholarly/resolved-document layers have failed.

## Web capability registry

The normative provider inventory is `ontology/providers/web-capabilities.json`. The runtime projection is `curator-app/src/web-capability-resolver.js` and is regression-tested against the governed registry.

| Provider | Layer | Implemented | Automatic | Free allowance / guard |
| --- | ---: | --- | --- | --- |
| Jina Reader | 1 known-URL reader | yes | guarded yes | keyless rate-limited; `JINA_READER_FREE_ONLY=true` |
| Serper | 2 SERP discovery | no | no | 2,500 signup queries; adapter blocked pending free-balance isolation |
| Tavily Basic | 3 web search | yes | guarded yes | 1,000 credits/month; `TAVILY_FREE_ONLY=true`; Basic only |
| Exa | 3 semantic/deep search | no | no | free monthly credit exists, but paid/x402-capable balance is not automatically consumable |
| Firecrawl | 4 scrape/render/interact | no | no | free allowance exists, but adapter blocked until free-plan/keyless execution can be proven safely |
| Cloudflare Browser Run | 4 rendered browser | no | no | Workers Free allowance exists, but production plan/binding must be verified before automation |

`available` therefore does not mean `automatic`. A provider with a useful free tier can be retained in the hierarchy for future use while remaining technically unable to execute.

## Zero-cost contract

The production path obeys all of the following constraints:

- OpenAlex is called without `OPENALEX_API_KEY` in the curator runtime.
- Semantic Scholar works keyless; `SEMANTIC_SCHOLAR_API_KEY`, if supplied, only improves the free rate limit.
- DataCite uses its public unauthenticated API.
- CORE works keyless at the public free rate; `CORE_API_KEY`, if supplied, only improves the free rate limit.
- Unpaywall is enabled only when `UNPAYWALL_EMAIL` is configured and remains a free API.
- Europe PMC uses the public REST API.
- Jina Reader is permitted only while `JINA_READER_FREE_ONLY=true`. The automatic adapter reads only a DOI-derived public target; it does not accept an arbitrary browsing target from the browser UI.
- Tavily is permitted only when `TAVILY_FREE_ONLY=true` and a free-plan `TAVILY_API_KEY` is configured.
- Tavily requests are hard-coded to `search_depth=basic`, `auto_parameters=false`, `include_answer=false` and one search request per opened unresolved paper. A response reporting more than one credit is rejected by `tavily_credit_guard`.
- Serper, Exa, Firecrawl and Cloudflare Browser Run are registered but `automaticAllowed=false` until an implementation-specific hard stop is validated.
- Exhaustion or provider failure returns `needs_web_search` or `web_search_exhausted`; it never upgrades itself to a paid request.

## Capability and provenance model

`ontology/modules/web-retrieval.json` adds the semantic layer for:

- `WebRetrievalProvider`;
- `ProviderCapability`;
- `ProviderQuota`;
- `WebSearchInvocation`;
- `PageRetrievalInvocation`;
- `BrowserInvocation`;
- `AgenticResearchInvocation`.

Every runtime response can expose `providersTried`, `providerErrors`, `providerPlan`, `providerUsage`, `freeCreditsUsed` and `freeRequestsUsed`. This permits later analysis of which capability solved a candidate and how much free quota was consumed.

## Search states

- `found`: an abstract has been recovered with a verified match.
- `needs_resolved_document`: free scholarly APIs did not return an abstract; inspect already-resolved paper manifestations next.
- `needs_web_search`: the free automated pipeline cannot proceed or remains inconclusive; do not infer absence.
- `web_search_exhausted`: the configured free search layer completed without a reliable abstract. This means **not found**, not **does not exist**.
- `unavailable`: a technical failure prevented completion.

## Match discipline

- DOI matches are preferred when exact.
- Title/year matches must clear provider-specific similarity thresholds.
- Jina Reader may accept only the DOI-derived known target in the automatic abstract fallback and rejects a clearly mismatched returned page title.
- Free search results require a strong title match and an explicit abstract section before extracted text can be shown.
- Resolved URLs remain candidate-bound through the authenticated retrieval gate.
- Private/local literal-IP targets are rejected by the resolved-paper fetcher.

## Optional free credentials

- `SEMANTIC_SCHOLAR_API_KEY`: optional free key for a dedicated rate limit.
- `CORE_API_KEY`: optional free key for a higher CORE rate limit.
- `UNPAYWALL_EMAIL`: enables the free Unpaywall API.
- `JINA_API_KEY`: optional; the Reader adapter can operate keyless and never requires this credential.
- `TAVILY_API_KEY`: optional free-plan key; the Worker will only use it while `TAVILY_FREE_ONLY=true`.

None of these credentials is required for deployment. Absence of a credential disables only that optional enhancement and never triggers a paid fallback.
