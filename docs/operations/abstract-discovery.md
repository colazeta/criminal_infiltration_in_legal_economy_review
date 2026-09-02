# Zero-cost multi-source abstract discovery

Abstract retrieval is a separate mechanical aid to curator screening. It must not infer eligibility and it must not persist abstract text into the public corpus.

## Core rule

`Abstract absent` is not a valid early-stage outcome, and automatic abstract discovery must not create monetary liability.

The resolver is a modular cascade. Every provider declares a stage, credential policy and billing policy. A paid or pay-as-you-go provider is not part of the production registry.

## Execution order

The order is deliberately cost- and quota-aware:

1. **Primary free bibliographic lookup** — OpenAlex and Crossref. OpenAlex is used without a billing key; exact DOI singleton lookups are free and anonymous search remains inside the provider's free allowance.
2. **Free scholarly/repository registry** — Semantic Scholar, DataCite, optional Unpaywall, CORE and Europe PMC. These calls are free or keyless/free-rate-limited. Optional credentials only improve a free allowance; they do not enable a paid provider.
3. **Governed resolved-paper layer** — publisher, repository and full-text URLs already present in `Retrieval coverage — mechanical` are inspected for abstract metadata or an abstract section.
4. **Free web fallback** — Tavily `basic` search, only when a selected paper is actually opened and only when a free key is configured. Background queue cards never consume Tavily credits.
5. **Assisted browsing handoff** — if the free web provider is unavailable, quota-exhausted or still inconclusive, the state is `needs_web_search`. It can then be researched with connected browsing tools during curator work without representing the abstract as absent.

## Zero-cost contract

The production path obeys all of the following constraints:

- Exa is not an automatic Worker dependency.
- OpenAlex is called without `OPENALEX_API_KEY` in the curator runtime.
- Semantic Scholar works keyless; `SEMANTIC_SCHOLAR_API_KEY`, if supplied, only improves the free rate limit.
- DataCite uses its public unauthenticated API.
- CORE works keyless at the public free rate; `CORE_API_KEY`, if supplied, only improves the free rate limit.
- Unpaywall is enabled only when `UNPAYWALL_EMAIL` is configured and remains a free API.
- Europe PMC uses the public REST API.
- Tavily is permitted only when `TAVILY_FREE_ONLY=true` and a free-plan `TAVILY_API_KEY` is configured.
- Tavily requests are hard-coded to `search_depth=basic`, `auto_parameters=false`, `include_answer=false` and one search request per opened unresolved paper. A response reporting more than one credit is rejected by `tavily_credit_guard`.
- If the Tavily free quota is unavailable or exhausted, the resolver stops. It never retries with advanced search, extract, crawl, research, pay-as-you-go or another paid provider.

The expected Tavily account configuration is the free Researcher plan with no credit card and a monthly limit set in the Tavily dashboard. Exhaustion should stop API calls until the free quota resets.

## Provider registry

The current zero-cost modules are:

| Provider | Stage | Runtime credential | Billing policy |
| --- | --- | --- | --- |
| OpenAlex | primary | none | anonymous free allowance / free DOI singleton |
| Crossref | primary | none | none |
| Semantic Scholar | scholarly | optional free key | none |
| DataCite | scholarly | none | none |
| Unpaywall | OA resolution | contact email | none |
| CORE | repository | optional free key | none |
| Europe PMC | scholarly | none | none |
| Tavily Basic | web | free-plan key | `free_hard_cap` |

The JavaScript registry exposes this metadata through `providerManifest`. Adding a new automatic provider requires declaring its billing policy and passing the zero-cost regression tests.

## Search states

- `found`: an abstract has been recovered with a verified match.
- `needs_resolved_document`: free scholarly APIs did not return an abstract; inspect already-resolved paper manifestations next.
- `needs_web_search`: the free automated pipeline cannot proceed or remains inconclusive; do not infer absence.
- `web_search_exhausted`: the configured free web search completed without a reliable abstract. This means **not found**, not **does not exist**.
- `unavailable`: a technical failure prevented completion.

## Match discipline

- DOI matches are preferred when exact.
- Title/year matches must clear provider-specific similarity thresholds.
- Free web results require a strong exact-title match and an explicit abstract section before extracted text can be shown.
- Resolved URLs are candidate-bound and come only from the governed retrieval record; the browser cannot submit arbitrary fetch targets.
- Private/local literal-IP targets are rejected by the resolved-paper fetcher.

## Provenance

Runtime responses expose `providersTried`, `providerErrors`, `provider`, `providerPlan`, `matchType`, `matchScore`, `searchStatus` and, for the web fallback, `freeCreditsUsed`. The UI surfaces provider provenance so the curator can distinguish a verified abstract from an unfinished search.

## Optional free credentials

- `SEMANTIC_SCHOLAR_API_KEY`: optional free key for a dedicated rate limit.
- `CORE_API_KEY`: optional free key for a higher CORE rate limit.
- `UNPAYWALL_EMAIL`: enables the free Unpaywall API.
- `TAVILY_API_KEY`: optional free-plan key; the Worker will only use it while `TAVILY_FREE_ONLY=true`.

None of these credentials is required for deployment. Absence of a credential disables only that optional enhancement and never triggers a paid fallback.
