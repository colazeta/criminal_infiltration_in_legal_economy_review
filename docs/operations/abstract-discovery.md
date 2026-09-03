# Zero-cost multi-source abstract discovery

Abstract retrieval is a separate mechanical aid to curator screening. It must not infer eligibility and it must not persist abstract text into the public corpus.

## Core rule

`Abstract absent` is not a valid early-stage outcome, and automatic abstract discovery must not create monetary liability.

The resolver is a modular capability cascade rather than a flat provider list. Every provider declares a capability layer, credential policy, free allowance, spending risk and automatic-use policy.

## Execution order

The order is deliberately cost-, capability- and quota-aware:

1. **Primary free bibliographic lookup** — OpenAlex and Crossref.
2. **Free scholarly/repository registry** — Semantic Scholar, DataCite, optional Unpaywall, CORE and Europe PMC.
3. **Governed resolved-paper layer** — publisher, repository and full-text locators already bound to the candidate are inspected directly.
4. **Free known-URL reader** — Jina Reader reads the DOI-derived target when `JINA_READER_FREE_ONLY=true`.
5. **SERP discovery** — Serper may make one bounded search request for the opened candidate, but only with a dedicated-free-account attestation and a successful reservation from the persistent 1,000-request project budget. A discovered public URL is handed back to Jina Reader for content reading.
6. **Semantic research-paper discovery** — Exa Search may make one `type=fast`, research-paper-category request with at most five results, but only with a dedicated Starter Free attestation and a successful reservation from the persistent 500-request project budget. No Contents, Deep Search or Agent capability is requested. A discovered public URL is handed to Jina Reader.
7. **Final free content search** — Tavily Basic runs only for the selected unresolved paper when a free-plan key is configured with `TAVILY_FREE_ONLY=true`.
8. **Registered future capability layers** — Firecrawl and Cloudflare Browser Run remain non-automatic until a separate free-plan boundary is proven.
9. **Assisted browsing handoff** — unresolved cases become `needs_web_search`. The resolver stops rather than consuming an ungoverned paid balance.

Queue cards never invoke the web-capability resolver. Web reading/search begins only after the curator opens one candidate and cheaper scholarly/resolved-document layers have failed.

## Web capability registry

The normative provider inventory is `ontology/providers/web-capabilities.json`. The runtime projection is `curator-app/src/web-capability-resolver.js` and is regression-tested against the governed registry.

| Provider | Layer | Implemented | Automatic | Free allowance / hard guard |
| --- | ---: | --- | --- | --- |
| Jina Reader | 1 known-URL reader | yes | guarded yes | keyless rate-limited; `JINA_READER_FREE_ONLY=true` |
| Serper | 2 SERP discovery | yes | guarded yes | 2,500 signup queries; dedicated-free-account attestation + persistent 1,000-request project cap |
| Exa Search | 3 semantic paper discovery | yes | guarded yes | $20 initial Starter Free credit; Search-only adapter + dedicated Starter attestation + persistent 500-request project cap |
| Tavily Basic | 3 content search | yes | guarded yes | 1,000 credits/month; `TAVILY_FREE_ONLY=true`; Basic only |
| Firecrawl | 4 scrape/render/interact | no | no | registered only pending a hard free-plan proof |
| Cloudflare Browser Run | 4 rendered browser | no | no | registered only pending production-plan/binding verification |

`automatic_allowed=true` is not sufficient by itself. A request is issued only when every runtime guard, credential requirement and applicable project-budget reservation succeeds.

## Zero-cost contract

The production path obeys all of the following constraints:

- OpenAlex is called without `OPENALEX_API_KEY` in the curator runtime.
- Semantic Scholar works keyless; `SEMANTIC_SCHOLAR_API_KEY`, if supplied, only improves the free rate limit.
- DataCite uses its public unauthenticated API.
- CORE works keyless at the public free rate; `CORE_API_KEY`, if supplied, only improves the free rate limit.
- Unpaywall is enabled only when `UNPAYWALL_EMAIL` is configured and remains a free API.
- Europe PMC uses the public REST API.
- Jina Reader is permitted only while `JINA_READER_FREE_ONLY=true`; discovered targets must pass the public-HTTPS target filter and title-match validation.
- Serper requires `SERPER_FREE_ONLY=true`, `SERPER_DEDICATED_FREE_ACCOUNT=true`, an API key and a successful persistent budget reservation. Its adapter performs only one bounded `/search` request and returns URLs for Jina reading.
- Exa requires `EXA_FREE_ONLY=true`, `EXA_DEDICATED_STARTER_ACCOUNT=true`, an API key and a successful persistent budget reservation. Its adapter uses only `/search`, `type=fast`, category `research paper`, maximum five results. It does not request Contents, Deep Search, Agent, output schema, livecrawl or x402.
- The Exa response is rejected if its reported request cost exceeds the one-request guard used by the project.
- Tavily is permitted only when `TAVILY_FREE_ONLY=true` and a free-plan `TAVILY_API_KEY` is configured. Requests remain hard-coded to Basic and one credit maximum.
- Firecrawl and Cloudflare Browser Run remain technically non-automatic.
- Exhaustion or provider failure returns `needs_web_search` or `web_search_exhausted`; it never upgrades itself to a paid request.

## Persistent project budgets

The Durable Object coordinator stores cumulative provider usage independently of a browser session.

- Serper stops permanently for this budget namespace after 1,000 reserved automatic calls.
- Exa Search stops permanently after 500 reserved automatic calls.

The budget reservation happens before the external provider call. Provider dashboard changes, purchased balance or future account upgrades do not raise these limits.

## Capability and provenance model

`ontology/modules/web-retrieval.json` adds the semantic layer for:

- `WebRetrievalProvider`;
- `ProviderCapability`;
- `ProviderQuota`;
- `ProviderProjectBudget`;
- `WebSearchInvocation`;
- `PageRetrievalInvocation`;
- `BrowserInvocation`;
- `AgenticResearchInvocation`.

Every runtime response can expose `providersTried`, `providerErrors`, `providerPlan`, `providerUsage`, `freeCreditsUsed` and `freeRequestsUsed`. Provider usage includes the quota unit and project-budget reservation when applicable.

## Search states

- `found`: an abstract has been recovered with a verified match.
- `needs_resolved_document`: free scholarly APIs did not return an abstract; inspect already-resolved paper manifestations next.
- `needs_web_search`: the free automated pipeline cannot proceed or remains inconclusive; do not infer absence.
- `web_search_exhausted`: the configured free search layers completed without a reliable abstract. This means **not found**, not **does not exist**.
- `unavailable`: a technical failure prevented completion.

## Match discipline

- DOI matches are preferred when exact.
- Title/year matches must clear provider-specific similarity thresholds.
- Jina Reader rejects a clearly mismatched page title.
- Serper/Exa discovery results require an exact DOI signal or a sufficiently strong title match before their URL is read.
- A Serper/Exa-discovered page must itself expose a compatible title before its abstract is accepted.
- Resolved and discovered URLs are restricted to public HTTPS targets; private/local literal-IP targets are rejected.
- Free search failure never proves that an abstract does not exist.

## Optional free credentials and attestations

- `SEMANTIC_SCHOLAR_API_KEY`: optional free key for a dedicated rate limit.
- `CORE_API_KEY`: optional free key for a higher CORE rate limit.
- `UNPAYWALL_EMAIL`: enables the free Unpaywall API.
- `JINA_API_KEY`: optional; the Reader adapter can operate keyless.
- `SERPER_API_KEY`: optional; remains unusable automatically unless the dedicated free-account Environment variable is true.
- `EXA_API_KEY`: optional; remains unusable automatically unless the dedicated Starter Free Environment variable is true.
- `TAVILY_API_KEY`: optional free-plan key; the Worker uses it only while `TAVILY_FREE_ONLY=true`.

None of these credentials is required for deployment. Absence of a credential or attestation disables only that provider and never triggers a paid fallback.
