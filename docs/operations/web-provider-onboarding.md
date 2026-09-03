# Web provider onboarding — Serper and Exa

This runbook activates the bounded discovery adapters without weakening the project's zero-spend contract.

## Preconditions

The runtime code and persistent budgets are already deployed independently of credentials.

- Serper project lifetime cap: **1,000 successful reservation attempts**, below the verified 2,500-query signup grant.
- Exa Search project lifetime cap: **500 Search-only calls**. At the verified Search price of $7/1,000 requests this represents a maximum theoretical $3.50, below the verified $20 initial Starter Free credit.
- Budget is reserved before the provider request.
- Queue browsing never invokes these providers.
- A credential by itself does not enable a provider.

## 1. Create a dedicated Serper free account

1. Open `https://serper.dev/` and choose the 2,500-free-query signup.
2. Use an account dedicated to this review.
3. Do **not** purchase/top up credits and do not add a payment route for this project account.
4. Copy the API key from the Serper dashboard.

In the GitHub Environment **`curator-production`** set:

- Environment secret `SERPER_API_KEY` = the Serper key.
- Environment variable `SERPER_DEDICATED_FREE_ACCOUNT` = `true`.

The second value is an explicit curator attestation that the supplied key belongs to the dedicated free/no-top-up account. If it is absent or not exactly `true`, the Worker treats Serper as guarded even when a key exists.

## 2. Create a dedicated Exa Starter Free account

1. Open `https://auth.exa.ai/` (or use the Starter "Start building for free" link from `https://exa.ai/pricing?tab=api`).
2. Keep the account on **Starter Free**. The verified plan offers $20 signup credit plus $10/month and does not require a payment method.
3. Do **not** upgrade to Developer/PAYGO, add a payment method, enable x402, or use a shared key that can draw from paid balance.
4. Create/copy an API key from the Exa dashboard.

In the GitHub Environment **`curator-production`** set:

- Environment secret `EXA_API_KEY` = the Exa key.
- Environment variable `EXA_DEDICATED_STARTER_ACCOUNT` = `true`.

The Exa automatic adapter is restricted to `/search`, `type=fast`, category `research paper`, and at most five results. Contents, Deep Search, Agent, livecrawl and x402 are outside the adapter.

## 3. Deploy

Run **Deploy curator Worker** manually or merge/push a change covered by that workflow.

Expected deployment summary when correctly configured:

- `Serper discovery enabled under the persistent 1,000-request project cap and dedicated-free-account guard.`
- `Exa Search enabled under the persistent 500-request Search-only project cap and dedicated Starter Free guard.`

If a key is present but the relevant attestation is not `true`, deployment succeeds but the provider remains unable to run.

## 4. Verify without spending quota

Sign in to the secure curator and request:

`GET /api/web-provider-status`

The endpoint is authenticated and performs **no provider search**. It returns, per provider:

- `mode`: `ready`, `guarded`, or `registered_only`;
- `automaticEligible`;
- `blockingReasons`;
- project budget `used`, `limit`, and `remaining` where applicable.

For initial activation the expected values are:

- Jina Reader: `ready`;
- Serper: `ready`, budget `0/1000` before its first invocation;
- Exa Search: `ready`, budget `0/500` before its first invocation;
- Tavily: `ready` only if its optional free key is separately configured.

## 5. First live validation

Open **one** unresolved candidate in the authenticated curator. Do not bulk-open candidates.

The expected order is:

`Jina DOI reader → Serper discovery → Jina discovered page → Exa Search discovery → Jina discovered page → Tavily Basic → STOP`

Only a provider actually reached by the cascade consumes its project budget. A successful earlier layer prevents later calls.

After the test, call `/api/web-provider-status` again and confirm the counters increased only for providers that were actually invoked.

## Fail-closed conditions

Do not continue automatic use if any of these becomes false:

- the account is still dedicated to this project;
- the account still has no paid/top-up route;
- the Serper free grant remains sufficient for the remaining project cap;
- Exa pricing/free-credit terms remain sufficient for the remaining Search-only project cap.

If provider economics change, set the corresponding Environment attestation to `false` first. This disables automatic use without deleting the key or changing code.
